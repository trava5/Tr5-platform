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
  in, text out, one profile, including real tool execution) via plain
  `generate_content` with function calling
  (`backend/services/gemini_chat_handler.py`) — not the Live API, which is
  reserved for Phase 4b's real-time voice use case. Without
  `GEMINI_API_KEY`, the endpoint still responds with `runtime_unavailable`,
  unchanged from before. Multi-turn continuity is backed by short-term
  memory (`MemoryRepository`): recent turns for the same conversation are
  loaded before each Gemini call and the new exchange is saved after,
  durable across restarts once `DATABASE_URL` points at PostgreSQL.
- `WS /api/v1/live/audio` opens a real-time, bidirectional Gemini Live API
  audio session (`backend/services/gemini_live_audio_handler.py`) when
  `GEMINI_API_KEY` is set: raw PCM audio in (16-bit, 16kHz mono) is
  forwarded straight into the Live session; audio out (24kHz), input/output
  transcripts, and tool execution (reusing the same
  `backend/services/gemini_common.py` tool-execution logic as
  `gemini_chat_handler.py`, not a second implementation) stream back over
  the WebSocket. The backend holds the Live session (Variant A) — a client
  only streams audio in/out, never talking to Gemini directly. Without
  `GEMINI_API_KEY`, the connection is accepted then cleanly closed with a
  `runtime_unavailable` reason, not a bare drop.
- `client/live_audio_client.py` is a standalone console client (Phase 4b-2):
  captures microphone audio (16-bit PCM, mono, 16kHz, 1024-frame chunks via
  `pyaudio`) and streams it to `/api/v1/live/audio`, plays back the 24kHz
  audio response, and prints transcripts to the console. Resolves the
  backend URL using the same `JARVIS_BACKEND_BASE_URL`/`_HOST`/`_PORT`
  convention as `realtime_client.py`. Run with
  `python -m client.live_audio_client`. No GUI, no activation gating —
  streams continuously until Ctrl+C.
- `GET /api/v1/conversations` and `GET /api/v1/conversations/{id}` expose
  stored conversation sessions.
- Short-term memory (`/api/v1/memory/short-term`) and long-term decision
  (`/api/v1/memory/decisions`) storage, plus a one-time SQLite import
  endpoint (`/api/v1/memory/import/sqlite`).
- Runs standalone via `uvicorn backend.app:create_app --factory` (or
  `python -m backend`), without any database configured (in-memory
  fallback), or against PostgreSQL when `DATABASE_URL` is set.
  `backend/app.py` has no module-level app instance and no direct
  `os.getenv` calls — `create_app()` only runs when a server is actually
  started (or explicitly called), never as an import side effect, and
  every setting (including `GEMINI_API_KEY`/`GEMINI_TEXT_MODEL`) is read
  through `BackendSettings`.
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

- No long-term decisions (confirmed, durable facts) yet — only recent-turn
  short-term memory is wired in (and only for the text endpoint, not live
  audio); `long_term_decisions` needs a confirmation UX that does not exist
  yet. Only one profile (`000_base`).
- Live audio (`/api/v1/live/audio`) has no memory/continuity across
  sessions. `client/live_audio_client.py` is a plain console script only —
  no GUI, no `platform_shell` integration, no wake-word/push-to-talk
  activation; real voice comprehension end-to-end requires the person's
  own microphone, speakers, and real `GEMINI_API_KEY`, and is their
  verification step, not this repository's automated one. `pyaudio` has no
  prebuilt wheel for every Python version/platform (notably, none yet for
  Python 3.14 on Windows as of this writing — it falls back to a source
  build requiring Microsoft C++ Build Tools); install a Python version with
  a prebuilt `pyaudio` wheel, or install the Build Tools, if `pip install`
  fails to build it.
- Only the numbered, cataloged `actions/` are present. The ten flat,
  uncataloged legacy action modules and `features/001_elevenlabs_voice/`
  are not transferred — both are still coupled to the source project's
  `main.py`/`app_config.py` and are deferred to Phase 4, where they will be
  re-evaluated rather than transferred as-is.
- No `memory/` (desktop) layer — that is a later transfer phase.
- Environment variable names are unchanged from the source project and are
  not yet renamed to a Tr5-wide convention.

## Planned evolution

- `long_term_decisions` + confirmation UX, once a real need for durable
  cross-session facts (not just recent-turn continuity) is identified.
- Phase 4b-1-bis: memory/continuity for live audio sessions, likely reusing
  `MemoryRepository` the same way Contract 0006 did for text.
- Phase 4c: enable and verify `features/002_telegram_bridge` end-to-end.
- Platform-level review: define how any Tr5 application connects to the
  voice agent.
