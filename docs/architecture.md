# Divum Chat — System Architecture
### Slack-alternative for ~250 employees | Cost-minimal today, scale-ready tomorrow

---

## 0. Design Philosophy

The core principle: **every subsystem that might outgrow "cheap and local" is built behind an interface from day one.** Nothing about the code changes when you scale — only a config value and which class gets injected.

| Subsystem | Day-1 implementation | Swap-in later | Trigger to swap |
|---|---|---|---|
| File storage | Local Linux filesystem | S3 / MinIO / GCS / Azure Blob | Multi-server deploy, >~500GB, need CDN |
| WebSocket fan-out | In-process (single instance) | Redis Pub/Sub → Kafka/NATS | 2+ backend replicas |
| Task queue | Celery + Redis broker | Celery + RabbitMQ/SQS | Queue depth/throughput issues |
| Search | Postgres FTS | Elasticsearch/OpenSearch/Typesense | Relevance quality complaints, >5M messages |
| Cache/presence | Redis (single node) | Redis Cluster/Sentinel | HA requirement |
| Push notifications | FCM direct call | FCM via queue + retry | Notification volume/reliability issues |

This table is the spec. Below is how each row is implemented.

---

## 1. High-Level Architecture

```
                              ┌─────────────────────┐
                              │   Mobile App (RN)    │
                              │  TypeScript + Expo    │
                              └──────────┬───────────┘
                                         │ HTTPS / WSS
                                         ▼
                              ┌─────────────────────┐
                              │   Nginx (reverse     │
                              │   proxy + TLS term)   │
                              └──────────┬───────────┘
                                         │
                  ┌──────────────────────┼──────────────────────┐
                  ▼                      ▼                      ▼
        ┌──────────────────┐  ┌──────────────────┐   ┌──────────────────┐
        │  FastAPI REST API │  │ FastAPI WS Gateway│   │  Static/Uploads   │
        │  (stateless)      │  │ (connection mgr)  │   │  server (nginx)   │
        └─────────┬─────────┘  └─────────┬─────────┘   └─────────┬─────────┘
                  │                      │                       │
                  │        ┌─────────────┴─────────────┐        │
                  │        │   Redis (pub/sub + cache   │        │
                  │        │   + presence + rate-limit) │        │
                  │        └─────────────┬─────────────┘        │
                  │                      │                       │
        ┌─────────┴──────────────────────┴───────────┐          │
        ▼                                              ▼          ▼
┌───────────────┐                          ┌───────────────┐  ┌──────────────────┐
│  PostgreSQL   │                          │ Celery Workers │  │ StorageBackend    │
│  (primary DB  │                          │ (async: encrypt,│  │ interface         │
│  + FTS)       │                          │ thumbnail, push)│  │ → LocalFS (today) │
└───────────────┘                          └───────────────┘  │ → S3Backend (later)│
                                                                 └──────────────────┘
```

**Why this shape:** REST and WebSocket are split into two logical services from day one (even if deployed as one process initially). This is the single highest-leverage decision for future scaling — it means you can scale WS connection capacity independently of API throughput later without restructuring anything.

---

## 2. The Storage Abstraction (the part that makes "no S3 today, S3-ready tomorrow" real)

Define a `StorageBackend` interface. Every file operation in the app goes through it — nothing ever calls `open()` or a filesystem path directly outside this module.

```python
# storage/base.py
from abc import ABC, abstractmethod
from typing import BinaryIO

class StorageBackend(ABC):
    @abstractmethod
    async def save(self, key: str, data: BinaryIO, content_type: str) -> str:
        """Returns a storage URI, e.g. 'local://uploads/abc.enc' or 's3://bucket/abc.enc'"""

    @abstractmethod
    async def load(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str | None:
        """Local backend returns None (use API proxy download); S3 backend returns a real presigned URL."""
```

```python
# storage/local.py
class LocalFileSystemBackend(StorageBackend):
    def __init__(self, base_path: str = "/srv/company-chat"):
        self.base_path = Path(base_path)

    async def save(self, key, data, content_type):
        path = self.base_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = encrypt_bytes(data.read())          # Fernet/AES-GCM, key from env/KMS
        path.write_bytes(encrypted)
        return f"local://{key}"

    async def get_presigned_url(self, key, expires_in=3600):
        return None  # no direct URL possible; client hits /files/{id}/download instead
```

```python
# storage/s3_ready.py  (stub — implement when you actually need it)
class S3Backend(StorageBackend):
    """Drop-in replacement. Same interface, zero call-site changes required.
    Works with AWS S3, MinIO, Backblaze B2, Cloudflare R2, or any S3-compatible API —
    which is itself an option if 'not paid AWS' matters more than 'not S3-compatible'."""
    ...
```

```python
# storage/factory.py
def get_storage_backend() -> StorageBackend:
    backend = settings.STORAGE_BACKEND  # env var: "local" | "s3"
    return {"local": LocalFileSystemBackend, "s3": S3Backend}[backend]()
```

All upload/download endpoints, thumbnail generation, and avatar handling call `storage.save()` / `storage.load()` — never a path directly. **This one abstraction is what turns "migrate off local disk" from a rewrite into a one-line env var change plus a data migration script.**

Encryption stays backend-agnostic too: encrypt/decrypt happens in the service layer *before* handing bytes to whichever `StorageBackend` is active, so switching backends never touches your security model.

---

## 3. WebSocket Architecture (built for horizontal scale from day 1, even while running 1 replica)

The naive mistake at this stage: hold WebSocket connections in a plain in-memory dict and call it done. It works with 1 replica — and becomes silently broken the moment you run 2 for a zero-downtime deploy (user A's message never reaches user B if they're on different instances). Building the pub/sub layer now costs almost nothing and avoids a painful retrofit.

```
Client A ──WS──▶ Instance 1 ──publish──▶ Redis Pub/Sub ──▶ Instance 2 ──WS──▶ Client B
```

```python
# ws/manager.py
class ConnectionManager:
    def __init__(self):
        self.local_connections: dict[str, set[WebSocket]] = {}  # user_id -> sockets on THIS instance
        self.redis = redis.from_url(settings.REDIS_URL)

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self.local_connections.setdefault(user_id, set()).add(ws)
        await self._start_listener_if_needed()

    async def broadcast_to_channel(self, channel_id: str, event: dict):
        # publish once — every instance (including this one) receives it via subscription
        await self.redis.publish(f"channel:{channel_id}", json.dumps(event))

    async def _redis_listener(self):
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("channel:*", "user:*")
        async for message in pubsub.listen():
            await self._deliver_to_local_sockets(message)
```

At 250 users on 1 replica, Redis pub/sub adds a few ms of latency for nothing in return *today* — but it means adding replica #2 later is a deploy config change, not an architecture change.

**WebSocket events:**

| Event | Direction | Payload |
|---|---|---|
| `message.new` | server→client | message object |
| `message.edited` / `message.deleted` | server→client | message id, patch |
| `typing.start` / `typing.stop` | client→server→broadcast | channel_id, user_id |
| `presence.update` | server→client | user_id, status, last_seen |
| `read_receipt.update` | client→server→broadcast | message_id, user_id, timestamp |
| `notification.new` | server→client | notification object |

---

## 4. Backend Module Structure

```
app/
├── main.py                      # FastAPI app, startup/shutdown hooks
├── core/
│   ├── config.py                 # Pydantic settings (env-driven, incl. STORAGE_BACKEND)
│   ├── security.py               # JWT issue/verify, password hashing (argon2)
│   └── rate_limit.py              # slowapi / custom Redis-based limiter
├── db/
│   ├── base.py                    # SQLAlchemy async engine/session
│   └── models/                    # one file per aggregate: user.py, channel.py, message.py...
├── storage/
│   ├── base.py                    # StorageBackend ABC
│   ├── local.py
│   ├── s3_ready.py                # stub, implement on demand
│   └── factory.py
├── modules/
│   ├── auth/          (router, service, schemas)
│   ├── users/
│   ├── channels/
│   ├── messages/
│   ├── files/
│   ├── search/
│   ├── notifications/
│   └── admin/
├── ws/
│   ├── manager.py
│   └── router.py
├── workers/
│   ├── celery_app.py
│   ├── tasks_files.py             # encrypt, thumbnail, virus-scan-stub
│   └── tasks_notifications.py     # FCM push, digest emails
└── tests/
```

Each `modules/*` follows router → service → repository, so business logic never directly touches the DB session or the storage backend — always through an injected service. This is what keeps the S3/search swaps to *one file changed*, not a grep-and-replace across the codebase.

---

## 5. Database Schema (PostgreSQL, normalized, FTS-ready)

```sql
-- Core identity
CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id UUID REFERENCES departments(id),
    name VARCHAR(100) NOT NULL
);

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,       -- 'admin','member','guest'
    permissions JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    avatar_uri TEXT,                          -- storage:// URI, backend-agnostic
    department_id UUID REFERENCES departments(id),
    team_id UUID REFERENCES teams(id),
    role_id UUID REFERENCES roles(id),
    status VARCHAR(20) DEFAULT 'offline',     -- online/away/offline
    last_seen TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    search_vector TSVECTOR                    -- generated column, see index below
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    device_info JSONB,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Channels & membership
CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL,                -- 'public','private','dm','group'
    topic TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    search_vector TSVECTOR
);

CREATE TABLE channel_members (
    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ DEFAULT now(),
    role VARCHAR(20) DEFAULT 'member',        -- 'owner','admin','member'
    muted BOOLEAN DEFAULT false,
    PRIMARY KEY (channel_id, user_id)
);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES users(id),
    content TEXT,
    reply_to_id UUID REFERENCES messages(id),
    forwarded_from_id UUID REFERENCES messages(id),
    is_pinned BOOLEAN DEFAULT false,
    is_edited BOOLEAN DEFAULT false,
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    edited_at TIMESTAMPTZ,
    search_vector TSVECTOR
);

CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    storage_uri TEXT NOT NULL,                -- 'local://...' or 's3://...' — backend-agnostic
    thumbnail_uri TEXT,
    file_name VARCHAR(255),
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    is_encrypted BOOLEAN DEFAULT true,
    is_compressed BOOLEAN DEFAULT false,
    checksum VARCHAR(64),                     -- sha256, for integrity verification
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE reactions (
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    emoji VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (message_id, user_id, emoji)
);

CREATE TABLE message_reads (
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    read_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (message_id, user_id)
);

-- Notifications & audit
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,                -- 'mention','dm','reaction'
    payload JSONB NOT NULL,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id UUID,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
) PARTITION BY RANGE (created_at);           -- partition by month from day 1

-- Indexes
CREATE INDEX idx_messages_channel_created ON messages(channel_id, created_at DESC);
CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_channel_members_user ON channel_members(user_id);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id) WHERE is_read = false;
CREATE INDEX idx_messages_search ON messages USING GIN(search_vector);
CREATE INDEX idx_users_search ON users USING GIN(search_vector);
CREATE INDEX idx_channels_search ON channels USING GIN(search_vector);

-- FTS trigger example (messages)
CREATE FUNCTION messages_search_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', coalesce(NEW.content, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_messages_search BEFORE INSERT OR UPDATE
    ON messages FOR EACH ROW EXECUTE FUNCTION messages_search_trigger();
```

**Two decisions worth calling out:**
- `audit_logs` is **partitioned by month from day 1** — this is the table most likely to silently bloat and slow down unpartitioned. Cheap to set up now, painful to retrofit on a live table.
- `attachments.storage_uri` stores a backend-agnostic URI (`local://` / `s3://`) rather than a raw path — so a future migration script can rewrite rows without any app-code changes.

---

## 6. API Design (REST, representative endpoints)

```
Auth
  POST   /auth/register
  POST   /auth/login                 → access + refresh JWT
  POST   /auth/refresh
  POST   /auth/logout
  POST   /auth/password-reset/request
  POST   /auth/password-reset/confirm

Users
  GET    /users/me
  PATCH  /users/me
  GET    /users/{id}
  GET    /users?department=&team=&search=

Channels
  POST   /channels
  GET    /channels                    (mine)
  GET    /channels/{id}
  PATCH  /channels/{id}
  POST   /channels/{id}/members
  DELETE /channels/{id}/members/{user_id}

Messages
  GET    /channels/{id}/messages?cursor=&limit=
  POST   /channels/{id}/messages
  PATCH  /messages/{id}
  DELETE /messages/{id}
  POST   /messages/{id}/reactions
  POST   /messages/{id}/pin
  POST   /messages/{id}/forward

Files
  POST   /files/upload                (multipart; async encrypt+thumbnail via Celery)
  GET    /files/{id}/download          (streams decrypted; or 302 to presigned URL if S3 backend)
  GET    /files/{id}/thumbnail

Search
  GET    /search?q=&type=messages|users|channels|files

Notifications
  GET    /notifications
  POST   /notifications/{id}/read
  POST   /notifications/read-all

Admin
  GET    /admin/users
  PATCH  /admin/users/{id}/role
  GET    /admin/audit-logs
  GET    /admin/stats
```

All list endpoints use cursor-based pagination (not offset) — matters once channels have tens of thousands of messages; costs nothing to do correctly from the start.

---

## 7. Authentication Flow

```
1. POST /auth/login (email, password)
   → verify argon2 hash → issue access JWT (15 min) + refresh JWT (30 days)
   → refresh token hash stored in `sessions` table (enables revocation)

2. Every request: Authorization: Bearer <access_token>
   → verified statelessly (no DB hit) via signature + expiry

3. On 401 (expired access token):
   POST /auth/refresh (refresh_token)
   → check `sessions` table: not revoked, not expired
   → issue new access token (rotate refresh token too — detect reuse = compromise)

4. Logout / admin-forced-logout:
   → mark session row revoked_at = now()
   → refresh silently fails going forward; access token dies naturally within 15 min
```

Short access-token TTL (15 min) is what makes JWT revocation-friendly without needing a blocklist check on every single request.

---

## 8. File Upload/Download Flow

```
Upload:
  Client → POST /files/upload (multipart)
    → API validates size/mime, writes to temp, returns 202 + file_id immediately
    → Celery task: compress (if beneficial, e.g. non-media) → encrypt (AES-256-GCM)
                   → storage.save() → generate thumbnail (Pillow, if image/video)
                   → update `attachments` row → emit ws event "file.ready"

Download:
  Client → GET /files/{id}/download
    → check channel membership / permission
    → storage.load() → decrypt in-memory → stream to client
    → (S3 backend later: skip decrypt-and-stream, return get_presigned_url() as a 302 instead)
```

Doing encryption/thumbnailing **async via Celery** rather than inline in the request is what keeps upload latency low even for large videos — this matters more than almost anything else in the files pipeline.

---

## 9. Notification Flow

```
Message sent → mentions parsed → for each mentioned/DM'd user:
    1. Insert `notifications` row
    2. If user has active WS connection → push via ws/manager (instant)
    3. If user offline/backgrounded → Celery task → FCM push
    4. In-app badge count = COUNT(*) WHERE user_id=? AND is_read=false
```

---

## 10. Suggested Open-Source Libraries

| Purpose | Library |
|---|---|
| Auth scaffolding | `fastapi-users` |
| ORM / migrations | `SQLAlchemy 2.0` (async) + `Alembic` |
| Password hashing | `argon2-cffi` (preferred over bcrypt) |
| JWT | `python-jose` or `pyjwt` |
| Rate limiting | `slowapi` |
| Background jobs | `Celery` + `redis` broker |
| Image processing | `Pillow` |
| Video thumbnail | `ffmpeg-python` (shells out to ffmpeg) |
| Compression | `zstandard` |
| Encryption | `cryptography` (Fernet or AES-GCM) |
| Push notifications | `firebase-admin` |
| RN chat UI | `react-native-gifted-chat` |
| RN forms | `react-hook-form` |
| RN navigation | `@react-navigation/native` |
| HTTP client | `axios` (with interceptor for token refresh) |
| RN WebSocket | native `WebSocket` + reconnect logic (`react-use-websocket` pattern, or roll your own with backoff) |

---

## 11. Deployment / Folder Structure

```
/srv/company-chat/
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── backend/
│   ├── Dockerfile
│   └── app/                    (structure from §4)
├── uploads/                    # LocalFileSystemBackend root — separate volume, encrypted at rest
├── backups/                    # borg/restic snapshots, cron'd nightly
└── .env                        # STORAGE_BACKEND=local, DB creds, JWT secret, FCM key, etc.
```

```yaml
# docker-compose.yml (shape)
services:
  api:       # FastAPI REST + WS (can split into 2 services later without code changes)
  worker:    # Celery worker
  db:        # postgres:16
  redis:     # redis:7
  nginx:     # reverse proxy + TLS
```

**Non-negotiable from day 1, cost-free:** automated nightly encrypted backup of both the Postgres volume and the `uploads/` directory to a second disk or off-box target (even a cheap secondary VM or a family/dept NAS). With no S3, your entire file corpus lives on one box's disk — backups aren't a roadmap item, they're launch-blocking.

---

## 12. UI/UX Screen Summary

| Screen | Key elements |
|---|---|
| **Login** | Email/password, "forgot password", clean centered card, dark-mode aware |
| **Home** | Left rail: channel list, DMs, search bar. Sidebar collapsible on mobile |
| **Channel List** | Sections: Channels / DMs / Groups, unread badges, presence dots |
| **Chat** | Message list (virtualized), composer with attach/emoji, typing indicator strip, reply/pin/forward via long-press or hover menu |
| **Profile** | Avatar, department/team, status setter, edit fields |
| **Search** | Tabs: Messages / Users / Channels / Files, debounced query |
| **Notifications** | List grouped by day, mark-all-read, tap-to-jump |
| **Settings** | Dark mode toggle, notification prefs, privacy, account |
| **Admin Dashboard** | User table (role/dept/team filters), audit log viewer, usage stats |

Navigation: bottom tabs on mobile (Home / Search / Notifications / Profile), stack navigation within each tab (React Navigation).

---

## 13. Development Roadmap

**Phase 1 (Weeks 1–4): Foundation**
Auth, users, departments/teams/roles, DB schema + migrations, storage abstraction (local only), basic REST CRUD for channels/messages.

**Phase 2 (Weeks 5–8): Realtime**
WebSocket gateway + Redis pub/sub manager, typing/presence/read-receipts, message edit/delete/reactions, RN chat UI wired to WS.

**Phase 3 (Weeks 9–11): Files & Search**
Upload/download pipeline (Celery: encrypt/compress/thumbnail), Postgres FTS across messages/users/channels/files, file previews in RN.

**Phase 4 (Weeks 12–14): Notifications & Admin**
FCM integration, in-app notification center, admin dashboard, audit log viewer, RBAC enforcement pass.

**Phase 5 (Weeks 15–16): Hardening & Launch**
Rate limiting, backup automation + restore drill, load test WS at 250 concurrent, security review, dark mode + settings polish.

---

## 14. Future Scalability Path (when, not if)

| Trigger | Action | Effort given the abstractions above |
|---|---|---|
| 2+ backend replicas needed | WS already uses Redis pub/sub — just deploy more replicas behind nginx `least_conn` | Zero code change |
| Storage >500GB or need CDN | Swap `STORAGE_BACKEND=local` → `s3`, run migration script to copy `uploads/` → bucket | Implement `S3Backend` class (~1 day), one env var |
| Search quality complaints / >5M messages | Add Typesense/OpenSearch, dual-write from `messages` insert, swap `/search` service impl | Isolated to `modules/search/service.py` |
| Redis becomes a bottleneck/SPOF | Redis Sentinel or managed Redis | Infra-only change |
| Need multi-region / DR | Postgres streaming replication + object storage (now on S3) replicates natively | Straightforward once on S3 |

This is the payoff of the abstraction-first approach: none of these are re-architecture projects. They're each isolated, bounded pieces of work because the interface boundary was drawn correctly on day one.
