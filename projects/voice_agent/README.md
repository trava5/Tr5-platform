# Voice Agent

## Purpose

Server backend for the JARVIS voice agent: a standalone FastAPI service
providing conversation storage, memory storage, and realtime WebSocket
events, backed by PostgreSQL with an in-memory fallback. Transferred from
the external `jarvis_cesky` project as Phase 1 of a multi-phase migration
(see `IMPLEMENTATION_CONTRACT_0002`).

## Current capabilities (v0.1)

- `GET /api/v1/health` and `GET /api/v1/status` report backend and
  PostgreSQL configuration health.
- `WS /api/v1/realtime` streams runtime-state, message, and (reserved)
  audio events.
- `POST /api/v1/messages` accepts the stable agent message contract.
- `GET /api/v1/conversations` and `GET /api/v1/conversations/{id}` expose
  stored conversation sessions.
- Short-term memory (`/api/v1/memory/short-term`) and long-term decision
  (`/api/v1/memory/decisions`) storage, plus a one-time SQLite import
  endpoint (`/api/v1/memory/import/sqlite`).
- Runs standalone via `uvicorn`, without any database configured (in-memory
  fallback), or against PostgreSQL when `DATABASE_URL` is set.
- Includes `backend/client.py` and `backend/realtime_client.py` as
  reference HTTP/WebSocket clients for other Tr5 applications.
- `actions/` provides a catalog-driven tool mechanism (`tool_catalog.py`,
  `action_loader.py`) with three numbered, independently importable
  actions: weather (`001_weather`), Google Calendar
  read/create/delete (`002_calendar`), and opening Windows applications
  (`003_open_app`).
- `features/002_telegram_bridge/` provides a Telegram Bot API bridge
  (long polling, text and voice messages, chat allowlisting) that talks to
  this backend's `/api/v1/messages` endpoint via `backend_client.py`.

## Current limitations

- No connected live agent runtime: `POST /api/v1/messages` responds with
  `runtime_unavailable` until Phase 4 implements the live runtime.
  `tool_catalog.py` exists and is importable, and its three actions run
  independently, but nothing calls them yet — no agent dispatches tool
  calls into `actions/` until Phase 4.
- Only the numbered, cataloged `actions/` are present. The ten flat,
  uncataloged legacy action modules and `features/001_elevenlabs_voice/`
  are not transferred — both are still coupled to the source project's
  `main.py`/`app_config.py` and are deferred to Phase 4, where they will be
  re-evaluated rather than transferred as-is.
- No `profiles/` or `memory/` (desktop) layers — those are later transfer
  phases.
- Environment variable names are unchanged from the source project and are
  not yet renamed to a Tr5-wide convention.

## Planned evolution

- Phase 3: implement the `profiles/` loader as new work.
- Phase 4: design and implement the live agent runtime.
- Platform-level review: define how any Tr5 application connects to the
  voice agent.
