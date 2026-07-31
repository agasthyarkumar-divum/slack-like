# Getting Started

First-time setup and day-to-day commands for running Divum Chat locally. All
commands below assume repo root unless stated otherwise. `make help` lists
every shortcut described here.

## Prerequisites

- Docker + Docker Compose (backend: postgres, redis, api, worker)
- Node.js 20+ and npm (mobile: Expo)
- Python 3.12+ (only needed if you run the API on the host instead of Docker)

## First-time setup

```bash
git clone <repo> && cd divum-chat   # or wherever this repo lives
make up                              # copies .env.example -> .env, builds + starts the backend
make mobile                          # installs mobile deps, starts the Expo dev server
```

That's it for a first run. Everything below is reference for what those do and
what to run day-to-day.

## The one rule that avoids most local-dev pain

**Pick ONE way to run the API at a time: Docker, or the host.** Both bind to
`localhost:8000`. Running `docker-compose up` and `uvicorn app.main:app` at
the same time on the same machine gets you `[Errno 98] Address already in
use` — the second one loses, and it's not always obvious which one is
"running" anymore. `make backend-dev` (host mode) automatically stops the
Docker `api` container first so this can't happen; if you start uvicorn by
hand instead, stop the container yourself first (`docker-compose stop api`).

## Backend

**Everything in Docker (default, recommended):**

```bash
make up          # build + start postgres, redis, api, worker
make logs         # tail API logs
make ps            # check container status
make down           # stop everything (data/volumes persist)
```

API: `http://localhost:8000` — docs at `/docs` (Swagger) and `/redoc`, health
check at `/health`.

**API on the host instead** (e.g. to attach a debugger — db/redis still run
in Docker):

```bash
make backend-dev
```

This creates `backend/.venv`, installs `requirements.txt`, makes sure
`db`/`redis` containers are up, stops the Docker `api` container if it's
running, and starts `uvicorn --reload` on the host.

**Migrations** (Alembic, async — needs `db` running, either via Docker or host):

```bash
make migration m="add users table"   # autogenerate a new migration
make migrate                          # apply pending migrations
```

**Config**: app name, version, and all secrets (DB URL, JWT key, storage
backend, FCM key) live in one place — [`backend/app/core/config.py`](../backend/app/core/config.py),
populated from environment variables. Root `.env` feeds the Docker stack;
`backend/.env` feeds host-mode `uvicorn`. Neither is committed — copy from
the matching `.env.example`.

## Mobile

Mobile commands must run **from `mobile/`** (or via the `make mobile*`
targets, which `cd` there for you) — `npm run dev` / bare `expo` from the
repo root or from `backend/` will fail with "missing script" or "command not
found".

```bash
make mobile          # npm install + expo start (interactive: scan QR, or press i/a/w)
make mobile-web        # same, opens straight into the web preview
make mobile-android      # target an Android emulator/device
make mobile-ios            # target an iOS simulator/device (macOS only)
make typecheck                # tsc --noEmit
```

If Expo says "Port 8081 is being used by another process," something (often
a previous Expo run that didn't shut down cleanly, or a background session
started by an assistant) is still holding it. Free it with:

```bash
make clean-ports
```

Then re-run `make mobile`. Prefer this over `kill -9`-ing PIDs by hand — it
only touches the Metro/Expo port range (8081/8082/19000-19002), never
Docker's ports.

## Common mistakes (from experience)

- **Pasting a multi-line block that starts with `cd backend`** while your
  shell is already inside `backend/` (or `mobile/`) silently `cd`s nowhere
  (the `cd` fails, the rest of the block runs in the *current* directory
  instead) — e.g. a stray `backend/.venv` inside `mobile/` if that happens
  from `mobile/`. Check `pwd` before pasting multi-line setup blocks, or use
  the `make` targets instead, which always `cd` to the right place internally.
- **Two things bound to :8000** — see "the one rule" above.
- **Stray Expo/Metro processes on :8081** from a previous session — `make clean-ports`.
