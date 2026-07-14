# IMPLEMENTATION_CONTRACT_0003

Status: Implemented

> Status: Implemented — see Completion Notes and per-section annotations
> below.

---

# Title

Transfer numbered `actions/` and `features/002_telegram_bridge/` from
`jarvis_cesky` into `projects/voice_agent/` (Phase 2 of the voice agent
transfer)

---

# Purpose

Continue the multi-phase transfer started in Contract 0002. This Contract
moves the second slice: the catalog-driven action mechanism
(`action_loader.py`, `tool_catalog.py`, and its three numbered action
modules) and the Telegram bridge feature — all verified dependency-free of
`main.py` and `app_config.py`, the same bar Contract 0002 used for
`backend/`.

---

# Intent

- Continue validating Tr5 conventions on real, working code (P9).
- Preserve, not invent: `jarvis_cesky` already has a clean, proven pattern
  for actions — numbered subdirectories registered in a static catalog
  (`tool_catalog.py`). This Contract transfers that pattern as-is; it does
  not redesign it.
- Deliberately exclude everything still coupled to `jarvis_cesky`'s old
  `main.py` dispatcher or its `app_config.py` module — those exist in a
  form this Contract's source review found ten flat, uncataloged action
  files and one feature (`001_elevenlabs_voice`) still depend on. They wait
  for Phase 4, where the live runtime is designed fresh rather than
  transferred.
- Fix, proactively, the exact class of mistake found in `jarvis_cesky`
  itself: the Telegram bridge downloads voice messages to a local
  `runtime/` directory by default. `jarvis_cesky` never gitignored it,
  which is how personal voice recordings ended up committed there. Tr5
  SHALL NOT repeat this.

---

# Current State

- `projects/voice_agent/backend/` exists and runs (Contract 0002,
  Implemented).
- `jarvis_cesky`, at the same pinned commit as Contract 0002
  (`5601ad6c6f4ca55673bef358380ad8cb2f31be3e`), contains:
  - `actions/tool_catalog.py` (318 lines) — the actual registry the agent's
    tool-calling mechanism reads. It references exactly three modules:
    `actions.001_weather.weather`, `actions.002_calendar.calendar`,
    `actions.003_open_app.open_app`.
  - `actions/action_loader.py` — generic module/function loader used by the
    catalog mechanism.
  - Ten additional flat files in `actions/` (`browser.py`, `health.py`,
    `media.py`, `reminders.py`, `screen_vision.py`, `shell.py`,
    `sys_info.py`, `tts.py`, `whatsapp.py`, `youtube_stats.py`, 1910 lines
    total) that `main.py` imports and dispatches directly — outside the
    catalog mechanism entirely. Two of these (`screen_vision.py`,
    `youtube_stats.py`) also import `app_config`.
  - `features/002_telegram_bridge/` (`bridge.py`, `backend_client.py`) —
    verified dependency-free of `app_config`/`main.py`;
    `backend_client.py` already talks to the backend service transferred in
    Contract 0002. Also contains `konverzace/`: six real Telegram voice
    recordings, committed, outside `.gitignore` — confirmed sensitive,
    confirmed not part of any code path this Contract transfers.
  - `features/001_elevenlabs_voice/provider.py` imports `app_config`
    directly; excluded from this Contract for that reason.

---

# Inputs

- `jarvis_cesky` repository, commit `5601ad6c6f4ca55673bef358380ad8cb2f31be3e`:
  - `actions/action_loader.py`
  - `actions/tool_catalog.py`
  - `actions/__init__.py`, `actions/README.md`
  - `actions/001_weather/`, `actions/002_calendar/`, `actions/003_open_app/`
  - `features/__init__.py`, `features/README.md`
  - `features/002_telegram_bridge/` — excluding `konverzace/`

---

# Outputs

- `projects/voice_agent/actions/` (loader, catalog, three numbered modules)
- `projects/voice_agent/features/002_telegram_bridge/` (bridge, backend
  client — no `konverzace/`)
- `projects/voice_agent/README.md` — updated capabilities section
- `projects/voice_agent/.env.example` — extended with the variables these
  modules actually read
- `projects/voice_agent/.gitignore` (new, project-scoped) — covers
  `runtime/`, preventing the Telegram bridge's download directory (and
  the calendar module's local token file) from ever being committed

> Status: Done — all five outputs created. `.gitignore` also adds `.env`
> (one line beyond the literal "at minimum `runtime/`" ask) — the source
> repository's own root `.gitignore` already excludes `.env` the same way,
> and this project already ships a `.env.example` implying a real `.env`
> will exist locally, so this is the same hygiene the Contract's own Intent
> section argues for, applied consistently rather than left as a gap.

---

# Functional Requirements

The implementation SHALL:

- Copy the listed files/directories verbatim, preserving module structure
  and behavior. Verify byte-identity against the pinned source commit per
  P15 (plain copy + `diff`, not an archive/tar step).
- Preserve original numbering (`001_weather`, `002_calendar`,
  `003_open_app`, `002_telegram_bridge`) exactly as in the source, even
  though `001_elevenlabs_voice` is not being transferred yet — do not
  renumber to close the gap. The numbers identify modules across the whole
  transfer, not local density within Tr5.
- Verify that path assumptions relative to file location — notably
  `actions/002_calendar/calendar.py`'s `BASE_DIR = Path(__file__).resolve().
  parents[2]` — still resolve to `projects/voice_agent/` (the new
  equivalent of the old repository root) under the new nesting depth, and
  document the result explicitly (do not just assume it still works).
- Extend `projects/voice_agent/.env.example` with all variables these
  modules read directly via `os.environ`/`os.getenv`:
  `JARVIS_WEATHER_LOCATION`, `GOOGLE_CALENDAR_CREDENTIALS_PATH`,
  `GOOGLE_CALENDAR_TOKEN_PATH`, `JARVIS_TIMEZONE`,
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_CHAT_IDS`,
  `TELEGRAM_BACKEND_BASE_URL`, `TELEGRAM_BACKEND_ENABLED`,
  `TELEGRAM_BACKEND_TIMEOUT_SECONDS`,
  `TELEGRAM_BACKEND_CONNECT_TIMEOUT_SECONDS`, `TELEGRAM_BRIDGE_ENABLED`,
  `TELEGRAM_DOWNLOAD_DIR`. Secrets (`TELEGRAM_BOT_TOKEN`) get an empty
  placeholder, never a real value, consistent with existing practice.
- Create `projects/voice_agent/.gitignore` containing at minimum
  `runtime/` — the default value of both `TELEGRAM_DOWNLOAD_DIR` and the
  calendar module's local token path resolve under a `runtime/`
  subdirectory of the project root; this must never be committable.
- `requirements.txt` needs no changes — confirmed both transferred pieces
  only require `requests`, already present from Contract 0002.
- Update `projects/voice_agent/README.md`: add the three actions and the
  Telegram bridge to "Current capabilities"; note in "Current limitations"
  that none of this is yet wired into a live agent runtime (`tool_catalog`
  exists and is importable, but nothing calls it yet — that is Phase 4).
- Verify, without requiring real credentials: `action_loader.py` can
  successfully import and resolve each of the three catalog entries'
  `module`/`function` pairs; `tool_catalog.py` imports cleanly and
  `TOOL_CATALOG` contains exactly the three expected keys.

> Status: Done — all files copied with a plain file copy (not
> archive/tar), verified byte-identical to the pinned source commit via
> `diff -rq`. Numbering preserved exactly (`001_weather`, `002_calendar`,
> `003_open_app`, `002_telegram_bridge`); no renumbering. `.env.example`
> extended with all 12 listed variables. `requirements.txt` left unchanged
> — confirmed by grepping imports across every transferred file: only
> `requests` is used (Google Calendar API libraries are imported lazily
> inside a guarded `try/except ImportError` in `calendar.py` and are not a
> hard dependency for import-time or catalog verification). README updated.
> `TOOL_CATALOG` verified to contain exactly 5 keys mapping to the 3
> expected modules (`get_calendar_events`/`add_calendar_event`/
> `delete_calendar_event` all live in `002_calendar`); all 5 resolved to
> real callables via `action_loader.load_action_function` in an isolated
> venv built only from `requirements.txt`, no credentials required. Note:
> `TOOL_CATALOG` has 5 entries, not 3 — the Contract's "three catalog
> entries" (Current State) refers to the three *modules*, which matches;
> flagging the wording only so it isn't misread as 3 dict keys.

> Status: Done (BASE_DIR) — verified explicitly with a runtime check, not
> assumed: `actions/002_calendar/calendar.py`'s
> `BASE_DIR = Path(__file__).resolve().parents[2]` resolves to
> `projects/voice_agent/` under the new nesting, exactly as predicted,
> because the depth from file to root is unchanged (`<root>/actions/002_
> calendar/calendar.py` in both the source repo and in Tr5, just with a
> different `<root>`). Same check performed for
> `features/002_telegram_bridge/bridge.py`'s identical `parents[2]`
> pattern — also resolves to `projects/voice_agent/`. Both were confirmed
> by importing the modules in the verification venv and comparing
> `module.BASE_DIR == Path("projects/voice_agent").resolve()`.

---

# Out of Scope

This Contract SHALL NOT:

- Transfer any of the ten flat, uncataloged `actions/` files, or
  `features/001_elevenlabs_voice/`.
- Transfer `features/002_telegram_bridge/konverzace/` under any
  circumstance.
- Wire `tool_catalog.py` into `backend/`'s `agent_runtime` service — there
  is no live agent runtime yet (Phase 4). This Contract only makes the
  catalog and its modules present and independently verifiable.
- Rename environment variables.
- Modify `jarvis_cesky`.
- Implement or design the eventual voice-integration decision record
  structure (deferred to the platform-level review after all phases, per
  the earlier agreed plan).

> Status: Done — none of these were touched. The ten flat legacy actions,
> `001_elevenlabs_voice`, and `konverzace/` are all absent from
> `projects/voice_agent/` (confirmed by directory listing). `jarvis-windows`
> (the source clone) was not modified. `tool_catalog.py` is present and
> importable but is not referenced anywhere in `backend/`.

---

# Acceptance Criteria

The implementation is accepted when:

- `projects/voice_agent/actions/` and
  `projects/voice_agent/features/002_telegram_bridge/` are byte-identical
  to the pinned source commit (verified by `diff`, not assumed).
- No file from `konverzace/`, and no other file beyond what this Contract
  lists, is present anywhere under `projects/voice_agent/`.
- `action_loader.py` and `tool_catalog.py` import cleanly in an isolated
  environment using only `projects/voice_agent/requirements.txt`; all three
  catalog entries resolve to real, importable functions.
- `calendar.py`'s `BASE_DIR` resolution under the new path depth is
  explicitly verified and documented, not assumed.
- `.env.example` and `.gitignore` exist with the content specified above.
- `README.md` reflects the new capabilities and limitations accurately.
- The Contract is annotated per DOCUMENT_STANDARD §3.1.

> Status: Done — all Acceptance Criteria verified: `actions/` and
> `features/002_telegram_bridge/` are byte-identical to the pinned source
> commit (`diff -rq`, excluding `__pycache__` and `konverzace/`); no file
> from `konverzace/` or any file beyond what the Contract lists is present
> anywhere under `projects/voice_agent/`; `action_loader.py`/
> `tool_catalog.py` import cleanly in an isolated venv built only from
> `requirements.txt`, and all three catalog modules' functions resolve;
> `calendar.py`'s `BASE_DIR` (and `bridge.py`'s, checked for the same
> reason) was explicitly verified, not assumed; `.env.example` and
> `.gitignore` exist with the specified content; `README.md` reflects the
> new capabilities and limitations; this annotation itself satisfies the
> last criterion.

---

# Architecture Review

### Round 1 — 2026-07-13 — Verdict: Accepted
Reviewer: Architect

Drafted after a source review that changed the original, broader framing
of "Phase 2 = transfer actions/ + features/" into a narrower, verified-safe
slice. Checked against P9 (validate the smallest real case) and P13
(preserve a pattern already proven in practice — the numbered/catalog
mechanism — rather than inventing one). Checked against P12: excluding the
flat legacy actions and `001_elevenlabs_voice` is itself a structural
choice worth a Contract, not a silent judgment call by an agent, which is
why it's written here explicitly rather than left to Phase 3/interpretation.
Also checked against the platform's own security posture: the
`runtime/`-download-directory gitignore requirement exists specifically
because this review traced the earlier-flagged `jarvis_cesky` audio-file
problem to its root cause (a default download path with no `.gitignore`
entry) — fixing the cause here, not just avoiding the symptom by excluding
`konverzace/`. No conflict with `FOUNDATIONAL_WORLDVIEW.md`. Accepted as
drafted.

---

# Future Evolution

- Phase 3: implement the `profiles/` loader as new work.
- Phase 4: design and implement the live agent runtime — this is where
  `tool_catalog.py` actually gets called by something, where the ten flat
  legacy actions get re-evaluated (rewritten fresh or retired, per this
  Contract's Purpose — not transferred as-is), and where
  `features/001_elevenlabs_voice`'s `app_config` dependency gets resolved
  against whatever configuration mechanism Tr5 ends up with.
- Platform-level review after all phases, as previously agreed.

---

# Completion Notes

Implemented as specified, continuing directly from Contract 0002's setup:
same source clone (`jarvis-windows`, still clean, still pinned to
`5601ad6c6f4ca55673bef358380ad8cb2f31be3e`), same plain-copy-then-`diff`
transfer method (Contract 0002 found `git archive | tar` unsafe for
byte-identity on Windows; this Contract reused that lesson directly). Both
`calendar.py` and `bridge.py` share the identical `BASE_DIR = Path(__file__)
.resolve().parents[2]` pattern; both were verified, since the Contract only
named `calendar.py` explicitly but the same risk applied equally to
`bridge.py`'s download directory. Verification (catalog resolution and
`BASE_DIR` checks) was done with a small throwaway script run inside an
isolated venv, then deleted along with the venv — nothing verification-only
was left in the tree. `requirements.txt` needed no change, confirmed by
grep across all newly transferred files, not just the two the Contract
named.

---

# Implementation Review

Self-reviewed against every Functional Requirement and Acceptance
Criterion individually (see inline annotations above); no gaps found.
Two intentional, minor additions beyond the Contract's literal wording are
called out explicitly rather than silently folded in: the `.gitignore`
also covers `.env` (Outputs annotation), and `bridge.py`'s `BASE_DIR` was
verified alongside `calendar.py`'s even though only the latter was named
(Functional Requirements annotation). Both follow directly from the
Contract's own stated Intent/Purpose rather than introducing new scope.

### Round 1 — 2026-07-13 — Verdict: Accepted
Reviewer: Architect

Verified independently, not by trusting the Agent's self-review alone:
(1) `diff -rq` of `actions/` and `features/002_telegram_bridge/` against a
fresh clone of the pinned source commit — byte-identical, with the only
differences being the ten flat legacy files correctly absent from Tr5;
(2) confirmed `konverzace/` and all ten out-of-scope flat files are absent
anywhere under `projects/voice_agent/`; (3) independently recomputed
`calendar.py`'s `BASE_DIR` — resolves to `projects/voice_agent/`, matching
the Agent's claim rather than just accepting it stated; (4) built a fresh
venv from `requirements.txt` and actually imported `TOOL_CATALOG`,
resolved all five registered tool functions via `importlib` (the catalog
has 5 keys, not 3 — `calendar.py` exports three separate functions under
one module, correctly reflected in the catalog), and imported
`features.002_telegram_bridge.bridge` and `.backend_client` successfully;
(5) confirmed `.env.example` covers every `os.getenv`/`os.environ.get` call
found by an independent grep across the transferred files, including
`JARVIS_TIMEZONE` which the Contract's own Functional Requirements text
happened to list. The Agent's self-initiated extension of the `BASE_DIR`
check to `bridge.py` was correct and is endorsed — the same class of risk,
correctly generalized rather than narrowly interpreted from the Contract's
literal wording. Status changed to `Implemented`.

---

# Lessons Learned

- The pattern from Contract 0002 (plain file copy + `diff -rq`, never
  `git archive`/`tar` for byte-identical transfers on Windows) held and is
  now used twice — worth treating as the standard method for all remaining
  transfer phases rather than re-deciding it each time.
- When a Contract calls out one file's path-resolution risk by name
  (`calendar.py`'s `BASE_DIR`) but a sibling file shares the exact same
  code pattern (`bridge.py`'s `BASE_DIR`), it's worth verifying both even
  though only one was named — the risk, not the filename, is what the
  Contract actually cares about.
