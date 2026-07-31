# Divum Chat

Internal team chat for ~250 employees — channels, DMs, files, and search, built
cost-minimal today and scale-ready tomorrow. See [docs/architecture.md](docs/architecture.md)
for the full system design and [docs/websocket-events.md](docs/websocket-events.md)
for the realtime wire protocol.

```
divum-chat/
├── backend/     FastAPI + PostgreSQL + Redis + Celery
├── mobile/      Expo Router app (TypeScript)
├── docs/        architecture.md, websocket-events.md, getting-started.md
├── Makefile     shortcuts for everything below
└── docker-compose.yml
```

## Quickstart

```bash
make up          # backend: build + start postgres, redis, api, worker (Docker)
make mobile        # mobile: install deps + start the Expo dev server
```

API at `http://localhost:8000` (`/docs` for Swagger, `/redoc` for ReDoc, `/health`
for a liveness check). `make help` lists every target with its description.

## Makefile commands

| Command | What it does |
|---|---|
| `make up` / `make down` / `make logs` / `make ps` | Backend via Docker — build+start, stop, tail API logs, container status |
| `make backend-dev` | API on the host with `--reload`; auto-stops the Docker `api` container first so the port-8000 collision you hit can't happen again |
| `make migrate` / `make migration m="..."` | Alembic — apply migrations / autogenerate a new one |
| `make mobile` / `make mobile-web` / `make mobile-android` / `make mobile-ios` | Start the Expo dev server (default / web / Android / iOS) — always `cd`s into `mobile/` for you, so wrong-directory mistakes can't happen via `make` |
| `make test` | Run the backend test suite against a real Postgres (`company_chat_test`, auto-created on the `db` container) |
| `make clean-ports` | Kills anything stray on Expo's ports (8081/8082/19000-19002) without touching Docker's ports |

Full walkthrough, troubleshooting, and the ground rules that keep backend/mobile
from fighting over ports: **[docs/getting-started.md](docs/getting-started.md)**.

Config — app name, version, and all secrets (DB, JWT, storage, FCM) — lives in
one place: [`backend/app/core/config.py`](backend/app/core/config.py), populated
from environment variables / `.env`. Nothing else in the backend hardcodes these
values.

## Status

Following the phased build order in the project brief — see commit history and
`docs/architecture.md` §13 for the roadmap. Currently: auth (Phase 3) — register,
login, refresh (with rotation + reuse detection), logout, `GET /users/me`, and
the mobile login screen wired end-to-end.
