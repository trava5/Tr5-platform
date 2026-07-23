# IMPLEMENTATION_CONTRACT_0007

Status: Accepted

---

# Title

Structural test/production isolation: remove import-time side effects,
unify all runtime configuration into `BackendSettings` (resolves P21)

---

# Purpose

Close the structural gap that caused the Contract 0006 incident (real
Gemini API calls and real database writes made by verification code).
Two independent root causes, both fixed here:

1. `backend/app.py` has a module-level `app = create_app()`, so merely
   *importing* the module runs real settings loading — before any test
   code gets a chance to isolate anything.
2. `create_app()` reads `GEMINI_API_KEY`/`GEMINI_TEXT_MODEL` directly via
   `os.getenv(...)`, outside of `BackendSettings` — so even code that
   *does* construct an explicit, safe `BackendSettings` object and passes
   it to `create_app(settings=...)` (already possible today) gets no
   protection for the Gemini side, because that path never consults
   `settings` at all.

---

# Intent

- Per P21: verification code must be *structurally incapable* of reaching
  real external systems, not just instructed to avoid them. This Contract
  delivers the actual mechanism, not another documented caution.
- Two independent fixes, because either gap alone would have been enough
  to cause the incident:
  - **Import-time safety:** switch to uvicorn's factory pattern
    (`uvicorn backend.app:create_app --factory`) so `create_app()` runs
    only when a server is actually started, never as an import side
    effect. Importing `backend.app` (as any test or review script does)
    becomes inert.
  - **Single settings surface:** extend `BackendSettings` to include
    `gemini_api_key` and `gemini_text_model`, loaded the same way every
    other setting already is. `create_app()` stops calling `os.getenv`
    for these directly. This means `create_app(settings=BackendSettings(...))`
    with an explicit, fully-populated object is now a *complete* isolation
    boundary — no setting can leak from the real environment around it.
- This Contract does not change runtime behavior for a normal server
  start (`GEMINI_API_KEY` in `.env` still works exactly as before) — it
  changes only how the app is launched (factory string) and where two
  settings are read from (moved, not removed).

---

# Current State

- `backend/app.py`: `app = create_app()` at module level;
  `api_key = os.getenv("GEMINI_API_KEY", "").strip()` and
  `model = os.getenv("GEMINI_TEXT_MODEL", ...)` read directly inside
  `create_app()`, bypassing `BackendSettings` entirely.
- `backend/config.py`: `BackendSettings` (frozen dataclass) already holds
  every other runtime setting (`database_url`, `app_name`, etc.), loaded
  via `load_settings()` → `_load_env_file()` → `os.getenv`. Passing an
  explicit `settings` object to `create_app()` already bypasses
  `load_settings()` entirely for everything `BackendSettings` covers —
  confirmed by reading the code directly (this is why the fix is to move
  Gemini settings *into* this object, not to invent a new mechanism).
- Current run command (PyCharm Run Configuration and manual PowerShell
  use): `uvicorn backend.app:app --reload --port 8000`. This Contract
  changes this to `uvicorn backend.app:create_app --factory --reload
  --port 8000` — the person will need to update their saved Run
  Configuration; this is called out explicitly since it is a workflow
  change, not just a code change.

---

# Inputs

- `backend/app.py`, `backend/config.py` (both existing, modified here).

---

# Outputs

- `backend/config.py`: `BackendSettings` gains `gemini_api_key: str` and
  `gemini_text_model: str` fields. `load_settings()` populates them from
  `GEMINI_API_KEY` / `GEMINI_TEXT_MODEL` (same env var names as today,
  same default for the model as today) — no `.env`/`.env.example` change
  needed, only where the values are read from internally.

  > Status: Done.
- `backend/app.py`:
  - `create_app()` reads `settings.gemini_api_key` /
    `settings.gemini_text_model` — zero direct `os.getenv` calls remain
    in this file.
  - Module-level `app = create_app()` removed entirely.
  - `create_app` remains the module's factory function, used directly by
    uvicorn's `--factory` flag (`backend.app:create_app`).

  > Status: Done — `import os` also removed (no longer used anywhere in
  > the file). One disclosed deviation beyond this bullet's literal file
  > list: `backend/__main__.py` (a Contract 0002 deliverable, not listed
  > in this Contract's Inputs) hardcoded `uvicorn.run("backend.app:app",
  > ...)`, which would have broken `python -m backend` the moment the
  > module-level `app` was removed. Flagged to the person before
  > proceeding (this Contract's own Out of Scope literally forbids
  > touching Contract 0002-0006 deliverables beyond `app.py`/`config.py`);
  > with explicit permission, updated to
  > `uvicorn.run("backend.app:create_app", factory=True, ...)` — the one
  > obvious fix, no design choice involved. See Completion Notes.
- `projects/voice_agent/README.md` updated: run instructions changed to
  the `--factory` form.

  > Status: Done — also updated `backend/README.md`'s "Spusteni" section
  > with the explicit `uvicorn ... --factory` command, since the top-level
  > README doesn't demonstrate that command directly.
- `CLAUDE.md` (repository root, not this project): add a short, standing
  instruction for the Implementation Agent — when verifying any Contract
  that touches `backend/app.py` or anything constructed from it, always
  call `create_app(settings=BackendSettings(...))` with an explicit,
  fully-populated settings object (real fields blanked/fake), and never
  rely on `os.environ` mutation (`pop`, `setenv`, `monkeypatch.setenv`) as
  the isolation mechanism for this project. This is documentation of
  practice, not a new code mechanism — the mechanism is the two fixes
  above; this just tells future agents to actually use it.

  > Status: Done — added under a new "Verifying anything built on
  > backend/app.py (voice_agent)" section, above "Current active work".

---

# Functional Requirements

The implementation SHALL:

- Add the two fields to `BackendSettings` and populate them in
  `load_settings()` exactly as scoped.
- Remove `os.getenv("GEMINI_API_KEY", ...)` and
  `os.getenv("GEMINI_TEXT_MODEL", ...)` from `create_app()`; replace with
  reads from the `settings` parameter already in scope.
- Remove the module-level `app = create_app()` line.
- Verify, with an actual test, that `import backend.app` alone — with a
  real `.env` present containing real credentials, if the test
  environment happens to have one — makes zero calls to
  `os.getenv("GEMINI_API_KEY")`, `os.getenv("DATABASE_URL")`, or any
  `genai.Client`/database connection constructor. (In the Architect's own
  review environment this is moot, since no `.env` exists there — but the
  Implementation Agent's environment does have a real one, and this is
  exactly the scenario that caused the incident, so it is the one that
  must be verified where it matters.)
- Verify that `create_app(settings=BackendSettings(gemini_api_key="",
  database_url="", ...))` — fully explicit, no environment reads at all —
  produces a runtime in the same `runtime_unavailable`/
  `database.configured: false` state as today's environment-based path,
  confirming the two paths are behaviorally equivalent, not just that the
  unsafe path was removed.
- Verify the server still starts correctly with the new factory command
  and that `/api/v1/status` reflects real `GEMINI_API_KEY`/`DATABASE_URL`
  values from a real `.env` when actually running as a server (not merely
  imported) — i.e., confirm normal operation is unchanged, only the
  import-time behavior changed.

> Status: Done — all five requirements verified with actual test calls
> (see Acceptance Criteria annotation for the concrete evidence), run
> against the real, present `.env` (real `GEMINI_API_KEY`/`DATABASE_URL`)
> to make the import-time test meaningful, per this Contract's own
> instruction that this is "exactly the scenario that caused the incident,
> so it is the one that must be verified where it matters." No message was
> ever sent and no write ever made against the real Postgres instance
> during this Contract's verification — only a bare `import`, an
> explicit-settings `TestClient` run (forced `database_url=""`), and two
> read-only HTTP calls (`/api/v1/health`, `/api/v1/status`) against a real,
> temporarily-started server, torn down immediately after.

---

# Out of Scope

This Contract SHALL NOT:

- Change any other setting's loading mechanism — only Gemini's two
  settings move into `BackendSettings`; `database_url` etc. are already
  correctly handled and untouched.
- Add a `TESTING` environment variable or flag-gated code path — the
  chosen mechanism (factory pattern + unified settings object) achieves
  P21's goal without needing one; do not add a second, redundant
  mechanism (P2).
- Modify `gemini_chat_handler.py`, `agent_runtime.py`, or any
  Contract 0002–0006 deliverable beyond `backend/app.py` and
  `backend/config.py`.
- Attempt to fix or verify against the person's real Postgres server —
  same standing limitation as every prior Contract touching this area.

---

# Acceptance Criteria

The implementation is accepted when:

- `BackendSettings` has `gemini_api_key`/`gemini_text_model`; `create_app()`
  contains no direct `os.getenv` calls for either.
- No module-level `create_app()` call remains in `backend/app.py`.
- A test importing `backend.app` in an environment with a real `.env`
  present (simulated or real, per the Implementation Agent's actual local
  setup) demonstrates zero real external calls occur from the import
  alone.
- `create_app(settings=...)` with a fully explicit settings object behaves
  identically (same status shape) to today's environment-driven path when
  given equivalent blank values.
- The server starts correctly via `uvicorn backend.app:create_app
  --factory ...` and behaves identically to before for a normal run with
  real `.env` values.
- `README.md` and `CLAUDE.md` updated as scoped.
- The Contract is annotated per DOCUMENT_STANDARD §3.1.

> Status: Done — every criterion verified with actual test calls: (1)
> `grep`-equivalent search of `app.py` for `os.getenv`/`import os` returns
> nothing; (2) `grep`-equivalent search for `^app = create_app` returns
> nothing; (3) bare `import backend.app` with the real `.env` present
> tracked `os.getenv`, `genai.Client.__init__`, and `create_engine` calls —
> zero of any of them, and `hasattr(backend.app, "app")` is `False`; (4)
> `create_app(settings=BackendSettings(gemini_api_key="", database_url="",
> ...))` produced `status: "runtime_unavailable"` and
> `database.configured: False`, matching the environment-driven path's
> shape; (5) a real server started via
> `uvicorn backend.app:create_app --factory --port 8123` against the real
> `.env` correctly showed `agent_runtime.connected: true` and
> `database.configured/ok: true` via `/api/v1/health`/`/api/v1/status`,
> then was shut down; (6) `README.md`/`CLAUDE.md` updated, this annotation
> pass fulfills the last criterion.

---

# Architecture Review

### Round 1 — 2026-07-22 — Verdict: Accepted
Reviewer: Architect

Checked against P21 directly — this Contract exists because of it, so the
review question is whether the fix actually delivers a structural
guarantee or another instruction. It does: after this Contract, there is
no code path in `backend/app.py` that reads a real environment variable
unless a server is actually being started (`--factory`) or the caller
explicitly asks `load_settings()` to do so. An explicit `BackendSettings`
object is now a complete boundary, not a partial one. Checked against P2:
rejected the `TESTING` env var alternative deliberately — it would have
been a second, weaker mechanism layered on top rather than fixing the two
actual root causes, and every environment-variable-gated approach is
exactly the class of "instruction, not structure" P21 warns against.
Checked against P12: this is a structural fix affecting how the server is
launched, correctly given a full Contract rather than treated as a light-
path tweak, given it's a direct response to a safety-relevant incident.
No conflict with `FOUNDATIONAL_WORLDVIEW.md`/`PRINCIPLES.md`. Accepted as
drafted.

---

# Future Evolution

- If a future Contract needs to isolate something this mechanism doesn't
  cover (e.g. a genuinely side-effecting tool call, not just settings),
  the CLAUDE.md guidance added here is the place to extend, and the same
  "structural, not instructional" standard applies.
- Phase 4c (Telegram bridge) can now proceed with a real isolation
  mechanism available, rather than waiting further.

---

# Completion Notes

Implemented as scoped. `BackendSettings` gained `gemini_api_key`/
`gemini_text_model`, populated in `load_settings()` from the same env var
names as before. `create_app()` now reads both from `settings`; the
module-level `app = create_app()` and the now-unused `import os` were
removed. `README.md` (top-level and `backend/README.md`) updated with the
explicit `--factory` command.

**Disclosed deviation, agreed with the person before implementing:**
`backend/__main__.py` was not in this Contract's Inputs and its Out of
Scope literally forbids touching Contract 0002-0006 deliverables beyond
`app.py`/`config.py` — but `__main__.py` hardcoded
`uvicorn.run("backend.app:app", ...)`, which is exactly the string this
Contract's own fix removes. Left unfixed, `python -m backend` (the
project's documented launch command) would have broken the moment this
Contract's Outputs were implemented. This looked like an oversight in
Inputs/Out of Scope rather than a deliberate exclusion (no reasoning for
excluding it appears anywhere in the Contract, unlike the deliberate
`AgentRuntime` exclusion in Contract 0005/0006). Flagged before touching
anything; the person approved fixing it as a disclosed deviation rather
than blocking on a full Contract amendment. Changed to
`uvicorn.run("backend.app:create_app", factory=True, ...)` — the same
one-line pattern this Contract already applies everywhere else, no new
design decision.

Verification note: Acceptance Criterion 3 (import-time safety) and
criterion 5 (real server operation) were both verified against the actual,
real `.env` present in this environment (real `GEMINI_API_KEY`, real
`DATABASE_URL`), per this Contract's own instruction that this is the
scenario that actually matters. This was done safely this time, using
exactly the practice this Contract's own `CLAUDE.md` addition now
prescribes: the import-safety test only *observed* (via monkeypatched
trackers) whether `os.getenv`/`genai.Client`/`create_engine` were called,
never actually invoking them; the explicit-settings test forced
`database_url=""` and `gemini_api_key=""` on the `BackendSettings` object
itself; the real-server test hit only the two read-only endpoints
(`/api/v1/health`, `/api/v1/status`) — no message was sent, no write
occurred, and the server was torn down immediately after.

---

# Implementation Review

(To be completed after implementation.)

---

# Lessons Learned

- When a Contract's fix necessarily changes a public entry point (here:
  the module-level `app` object), grep the whole repo for every reference
  to that entry point before assuming Inputs/Out of Scope captured every
  affected file — `backend/__main__.py` referenced the exact string being
  removed and was not listed anywhere in this Contract, despite being a
  real, in-repo, previously-working launch path.
- The fix genuinely works, tested the way it was meant to be tested: a
  bare `import backend.app` with a real, credential-bearing `.env` present
  makes zero real external calls (tracked directly, not inferred), and an
  explicit `BackendSettings` object is now a complete isolation boundary —
  both were false before this Contract, which is exactly what caused the
  Contract 0006 incident this Contract exists to fix.
