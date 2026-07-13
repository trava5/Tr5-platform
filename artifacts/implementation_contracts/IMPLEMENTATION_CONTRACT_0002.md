# IMPLEMENTATION_CONTRACT_0002

Status: Accepted

---

# Title

Scaffold `projects/voice_agent/` and transfer the `backend/` service from
`jarvis_cesky` (Phase 1 of the voice agent transfer)

---

# Purpose

Establish the first application under the Tr5 Platform: the voice agent.

This Contract covers only Phase 1 of a multi-phase transfer from the
existing external project `jarvis_cesky`
(https://github.com/trava5/jarvis_cesky, source commit
`5601ad6c6f4ca55673bef358380ad8cb2f31be3e`): moving its already-isolated
`backend/` service into Tr5, unmodified in behavior, restructured only where
Tr5 naming/document conventions require it.

`backend/` was chosen to go first because it has zero dependencies outside
itself (verified: no imports of `main.py`, `app_config.py`, or any
desktop-only module) and is architecturally the piece every future Tr5
application will eventually talk to as a shared runtime — matching
`jarvis_cesky`'s own ADR-016 direction.

---

# Intent

- Validate that Tr5's platform conventions (naming, `projects/` structure,
  README standard) work for a real, non-trivial Python application — not
  only for the Discovery Engine toy case (per P9).
- Prove the transfer pipeline itself (Contract → Agent → Review) on a
  bounded, low-risk slice before attempting harder phases.
- Produce a working, standalone FastAPI service inside Tr5 that can be run
  and smoke-tested independently of `jarvis_cesky`.

This is explicitly a **transfer**, not a **rewrite**. Behavior of the copied
code SHALL NOT change. Restructuring is limited to what Tr5 conventions
require (paths, README, requirements scoping). Phase 4 (later) is where a
from-scratch redesign happens — not here.

---

# Current State

- Tr5-platform contains only the foundational documents and the Discovery
  Engine; no `projects/` directory exists yet.
- `jarvis_cesky` (external, read-only reference for this Contract) contains
  a working `backend/` package (2586 lines across `app.py`, `api.py`,
  `config.py`, `database.py`, `storage.py`, `client.py`,
  `realtime_client.py`, `services/`, `db/`) implementing a FastAPI service
  with conversation storage, memory storage, and realtime WebSocket events,
  backed by PostgreSQL with an in-memory fallback.
- `jarvis_cesky` itself has known, unrelated in-flight work (`MIG-006`,
  `MIG-007`) affecting `main.py` and realtime audio — this Contract does not
  touch or depend on that work.
- `jarvis_cesky` also has known committed sensitive/incidental content
  (Telegram voice recordings, `.idea/`, log files) — entirely outside
  `backend/` and explicitly excluded from this transfer regardless of their
  status in the source repository.

---

# Inputs

- `jarvis_cesky` repository, `backend/` directory only, at commit
  `5601ad6c6f4ca55673bef358380ad8cb2f31be3e`.

---

# Outputs

- `projects/voice_agent/backend/` — the transferred service code.
- `projects/voice_agent/README.md` — per DOCUMENT_STANDARD §4.
- `projects/voice_agent/requirements.txt` — scoped to what `backend/`
  actually imports.
- `projects/voice_agent/.env.example` — scoped to backend-relevant settings
  only.

---

# Functional Requirements

The implementation SHALL:

- Create `projects/voice_agent/`.
- Copy the full `backend/` package tree from the source commit into
  `projects/voice_agent/backend/`, preserving internal module structure and
  behavior exactly.
- Include `client.py` and `realtime_client.py` — confirmed dependency-free
  of any desktop-only module, and useful as reference clients for future
  Tr5 applications connecting to this service.
- Create `projects/voice_agent/requirements.txt` containing only packages
  the transferred code actually imports (expected: `fastapi`, `uvicorn`,
  `websockets`, `sqlalchemy`, `asyncpg`, `requests`; verify against actual
  imports rather than copying `jarvis_cesky`'s full `requirements.txt`,
  which includes desktop-only dependencies such as `pyaudio` and
  `google-genai`).
- Create `projects/voice_agent/.env.example` containing only the variables
  `backend/config.py` actually reads (database connection, backend host/
  port/app-name settings). Do not carry over Telegram, ElevenLabs, or
  Gemini variables — those belong to later phases.
- Create `projects/voice_agent/README.md` following the DOCUMENT_STANDARD
  §4 template (Purpose, Current capabilities, Current limitations, Planned
  evolution). "Current limitations" SHALL state plainly that this service
  currently has no connected live agent runtime (`runtime_unavailable` is
  the expected status until Phase 4).
- Verify the transferred service starts successfully (`uvicorn` boots
  without error) and `GET /api/v1/status` responds, using an isolated
  virtual environment and the new `requirements.txt`.
- Keep environment variable names unchanged from the source (e.g.
  `JARVIS_BACKEND_APP_NAME`, `DATABASE_URL`) — renaming is explicitly out
  of scope for this Contract.

---

# Out of Scope

Version 1.0 of this transfer SHALL NOT:

- Transfer `actions/`, `features/`, `profiles/`, `memory/`, `main.py`, or
  `core/prompt.txt` (later phases).
- Rename environment variables or change configuration semantics.
- Add, remove, or modify any endpoint, model, or behavior.
- Modify the `jarvis_cesky` repository in any way.
- Carry over `.idea/`, log files, or any content from
  `features/002_telegram_bridge/konverzace/` (none of these live in
  `backend/`, but this is stated explicitly to remove any ambiguity).
- Define how other future Tr5 projects will connect to this service — that
  is deferred to the platform-level review after all transfer phases
  complete, per the agreed plan.
- Implement the `profiles/` loader (Phase 3) or rewrite the live agent
  runtime (Phase 4).

---

# Acceptance Criteria

The implementation is accepted when:

- `projects/voice_agent/backend/` exists and is module-for-module
  equivalent to the source at the referenced commit (no missing, no added
  files beyond what this Contract specifies).
- The service starts cleanly via `uvicorn` in a fresh virtual environment
  built only from the new `requirements.txt`.
- `GET /api/v1/status` returns a response.
- No file naming or directory naming violates the Tr5 naming convention
  (`lowercase_with_underscores` for directories and Python files, no
  diacritics).
- `README.md` and `.env.example` exist and match the scope defined above.
- No excluded content (per Out of Scope) is present anywhere under
  `projects/voice_agent/`.
- The Contract is annotated in place per DOCUMENT_STANDARD §3.1.

---

# Future Evolution

- Phase 2: transfer `actions/` and `features/`, wired into this backend.
- Phase 3: implement the `profiles/` loader as new work (not a transfer —
  `jarvis_cesky`'s own `profiles/` is currently only a documentation
  template, per its ADR-014).
- Phase 4: design and implement the live agent runtime (replacing
  `main.py`'s role) from current understanding, once `jarvis_cesky`'s own
  `MIG-006`/`MIG-007` has stabilized enough to inform — but not be
  copied into — the design.
- Platform-level review after all phases: extract proven patterns into
  PRINCIPLES.md / DOCUMENT_STANDARD.md, and define the standard for how any
  Tr5 application connects to the voice agent (including the decision
  record structure for "is this app voice-enabled").

---

# Completion Notes

(To be completed after implementation.)

---

# Lessons Learned

(To be completed after implementation.)
