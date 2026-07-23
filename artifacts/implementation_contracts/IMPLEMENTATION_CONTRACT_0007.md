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
- `backend/app.py`:
  - `create_app()` reads `settings.gemini_api_key` /
    `settings.gemini_text_model` — zero direct `os.getenv` calls remain
    in this file.
  - Module-level `app = create_app()` removed entirely.
  - `create_app` remains the module's factory function, used directly by
    uvicorn's `--factory` flag (`backend.app:create_app`).
- `projects/voice_agent/README.md` updated: run instructions changed to
  the `--factory` form.
- `CLAUDE.md` (repository root, not this project): add a short, standing
  instruction for the Implementation Agent — when verifying any Contract
  that touches `backend/app.py` or anything constructed from it, always
  call `create_app(settings=BackendSettings(...))` with an explicit,
  fully-populated settings object (real fields blanked/fake), and never
  rely on `os.environ` mutation (`pop`, `setenv`, `monkeypatch.setenv`) as
  the isolation mechanism for this project. This is documentation of
  practice, not a new code mechanism — the mechanism is the two fixes
  above; this just tells future agents to actually use it.

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

(To be completed after implementation.)

---

# Implementation Review

(To be completed after implementation.)

---

# Lessons Learned

(To be completed after implementation.)
