# IMPLEMENTATION_CONTRACT_0002

Status: Accepted

> Status: Implemented — see Completion Notes and per-section annotations
> below.

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

> Status: Done — all four outputs created as specified.

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

> Status: Done — copied `backend/` from `jarvis-windows` (local clone of
> `jarvis_cesky`), whose HEAD at transfer time was exactly commit
> `5601ad6c6f4ca55673bef358380ad8cb2f31be3e` with a clean working tree, so
> the copy is byte-for-byte identical to the source commit (verified with
> `diff -rq`, excluding `__pycache__`). `client.py` and `realtime_client.py`
> included per requirement. `requirements.txt` built from actual imports:
> `fastapi, uvicorn, pydantic, websockets, sqlalchemy, asyncpg, requests`.
> `pydantic` was added beyond the Contract's "expected" list because
> `schemas.py` imports it directly (`from pydantic import BaseModel,
> Field`) — a deviation from the illustrative list, not from the
> instruction, which was to verify against actual imports. `asyncpg` is not
> imported by name in Python but is required as the async driver behind
> `postgresql+asyncpg://` URLs in `backend/db/session.py`, consistent with
> the Contract's own expected list. `.env.example` contains exactly the
> nine variables read by `backend/config.py`
> (`JARVIS_BACKEND_APP_NAME/HOST/PORT/RELOAD`, `DATABASE_URL/NAME/USER/
> PASS/SCHEMA`); variables read only by `client.py`/`realtime_client.py`
> (e.g. `JARVIS_BACKEND_BASE_URL`, `JARVIS_BACKEND_REALTIME_ENABLED`) were
> deliberately excluded per the Contract's explicit scoping to what
> `config.py` reads. Verified boot: fresh venv from the new
> `requirements.txt`, `uvicorn backend.app:app`, `GET /api/v1/status` and
> `GET /api/v1/health` both returned HTTP 200 with the in-memory fallback
> active (no `DATABASE_URL` set).

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

> Status: Done — none of these were touched. `jarvis-windows` (the source
> clone) was not modified.

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

> Status: Done — all Acceptance Criteria verified:
> `projects/voice_agent/backend/` is byte-for-byte equivalent to the source
> commit (`diff -rq`, no missing/added files); the service booted cleanly
> via `uvicorn` in a fresh venv built only from the new `requirements.txt`;
> `GET /api/v1/status` returned HTTP 200; all directory/file names are
> `lowercase_with_underscores` with no diacritics; `README.md` and
> `.env.example` exist and match the defined scope; no excluded content
> (Telegram recordings, `.idea/`, logs, `actions/`, `features/`, `profiles/`,
> `memory/`, `main.py`, `core/prompt.txt`) is present anywhere under
> `projects/voice_agent/`; this annotation itself satisfies the last
> criterion.

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

Implemented as specified. The source `jarvis_cesky` repository was accessed
via a pre-existing local clone at `PycharmProjects/jarvis-windows` rather
than a fresh GitHub clone; its `origin` remote confirmed it is that
repository, and its HEAD matched the Contract's pinned commit exactly with
a clean working tree, so no fetch was needed. `backend/` was copied with a
direct file copy (not `git archive` + `tar`, which was tried first and
introduced CRLF line-ending changes on Windows) and verified byte-identical
with `diff -rq`. `requirements.txt` was derived by grepping all `import`/
`from` statements across the package; this added one package
(`pydantic`) beyond the Contract's illustrative "expected" list, which is a
result of following the Contract's own instruction to verify against
actual imports rather than a deviation from it. `.env.example` was scoped
strictly to `backend/config.py`'s own reads, per the Contract's explicit
wording, even though `client.py`/`realtime_client.py` (also transferred)
read several additional variables — those are reference-client concerns,
not this backend service's, and are out of scope here. Verification used a
disposable venv and a non-default port, both removed after the boot/status
check; no database was configured, so the service ran on the in-memory
fallback, which is the expected standalone behavior per `storage.py`.

---

# Lessons Learned

- `git archive | tar -x` is not a safe way to transfer files byte-for-byte
  on Windows/Git Bash — it can silently normalize line endings even when
  the source working tree does not. A plain file copy from a clean,
  correctly-pinned working tree is simpler and safer for "transfer,
  unmodified" Contracts like this one.
- A Contract's illustrative list of expected dependencies (here,
  `requirements.txt`) should still be verified against actual imports
  rather than trusted as exhaustive — this Contract already anticipated
  that by saying "verify... rather than copying", and that instruction
  caught one real gap (`pydantic`).
