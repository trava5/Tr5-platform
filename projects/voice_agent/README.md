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
- `POST /api/v1/messages` accepts the stable agent message contract. When
  `GEMINI_API_KEY` is set, it produces real Gemini-backed responses (text
  in, text out, one profile, single-turn, including real tool execution)
  via plain `generate_content` with function calling
  (`backend/services/gemini_chat_handler.py`) — not the Live API, which is
  reserved for Phase 4b's real-time voice use case. Without
  `GEMINI_API_KEY`, the endpoint still responds with `runtime_unavailable`,
  unchanged from before.
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
- `profiles/` provides a static profile loader (`profile_loader.py`) with
  `load_profile()` and `list_available_profiles()`. One profile,
  `000_base`, is delivered: a general-purpose assistant prompt with all
  five current `actions/tool_catalog.py` tools enabled and no features
  enabled by default. The loader validates every profile's declared tools
  against the real tool catalog and raises a specific exception on an
  unknown tool name or a missing profile file.

## Current limitations

- No memory across messages, no audio, no multi-turn conversational
  continuity, and only one profile (`000_base`). Each message opens a
  fresh `generate_content` call; nothing is persisted or remembered
  between messages. Real-time voice (Gemini Live API) is Phase 4b's
  concern, not implemented here.
- Only the numbered, cataloged `actions/` are present. The ten flat,
  uncataloged legacy action modules and `features/001_elevenlabs_voice/`
  are not transferred — both are still coupled to the source project's
  `main.py`/`app_config.py` and are deferred to Phase 4, where they will be
  re-evaluated rather than transferred as-is.
- No `memory/` (desktop) layer — that is a later transfer phase.
- Environment variable names are unchanged from the source project and are
  not yet renamed to a Tr5-wide convention.

## Planned evolution

- Phase 4a-bis: wire memory persistence into `gemini_chat_handler.py`.
- Phase 4b: Gemini Live API for real-time voice input/output, alongside
  (not replacing) `gemini_chat_handler.py`.
- Phase 4c: enable and verify `features/002_telegram_bridge` end-to-end.
- Platform-level review: define how any Tr5 application connects to the
  voice agent.
