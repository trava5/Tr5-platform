# IMPLEMENTATION_CONTRACT_0004

Status: Accepted

> Status: Implemented — see Completion Notes and per-section annotations
> below.

---

# Title

Implement the `profiles/` loader for `projects/voice_agent/` (Phase 3 —
new work, not a transfer)

---

# Purpose

Give `projects/voice_agent/` a way to load a named profile — a system
prompt plus a selected subset of the tools already registered in
`actions/tool_catalog.py` — as a self-contained, validated unit that a
future live agent runtime (Phase 4) can consume directly.

Unlike Contracts 0002 and 0003, this is not a transfer. `jarvis_cesky`'s own
`profiles/` directory (reviewed at the pinned commit
`5601ad6c6f4ca55673bef358380ad8cb2f31be3e`) is documentation only — a
`README.md` describing the intended shape, and one example profile
(`000_base/`) containing static `README.md`, `prompt.txt`, `actions.json`,
`features.json`, but no code that reads any of it. `jarvis_cesky` itself
still runs on `core/prompt.txt` and the full tool catalog directly. This
Contract builds the loader for the first time, using the documented intent
as its design basis (per P13 — a genuine, if unimplemented, proven-in-
discussion pattern), not inventing a new shape from scratch.

---

# Intent

- Build only what today's understanding needs: a loader for exactly one
  profile shape, matching what `voice_agent` already has (the 5-tool
  catalog from Phase 2). No multi-profile switching logic, no runtime
  integration — those wait for a second real profile and for Phase 4,
  respectively (P2, P9).
- The loader validates rather than trusts: every tool name a profile
  declares SHALL be checked against `actions/tool_catalog.py`'s actual
  keys, failing clearly and specifically if a profile references a tool
  that does not exist. This is the same posture as backend/config's
  existing `runtime_unavailable`-style explicit status reporting — fail
  informatively, not silently.

---

# Current State

- `projects/voice_agent/` has `backend/` (Contract 0002), `actions/` and
  `features/002_telegram_bridge/` (Contract 0003). No `profiles/` directory
  exists yet.
- `actions/tool_catalog.py`'s `TOOL_CATALOG` currently has exactly five
  keys: `get_weather`, `get_calendar_events`, `add_calendar_event`,
  `delete_calendar_event`, `open_app`.
- No live agent runtime exists yet (`backend/services/agent_runtime.py`
  reports `runtime_unavailable`) — nothing currently calls a profile loader,
  and this Contract does not change that.

---

# Inputs

- `jarvis_cesky`'s `profiles/README.md` and `profiles/000_base/README.md`,
  at the pinned commit, as design reference only — their prose describes
  intended shape and rules; their content is adapted, not copied verbatim,
  since the underlying catalog and available tools differ from the source
  project.
- `projects/voice_agent/actions/tool_catalog.py` (already present).

---

# Outputs

- `projects/voice_agent/profiles/README.md` — adapted from the source's
  documented rules (profile directory shape, copy-only-when-stable rule),
  updated to reference `voice_agent`'s actual catalog rather than
  `jarvis_cesky`'s.
- `projects/voice_agent/profiles/000_base/`:
  - `README.md` — purpose of the base profile
  - `prompt.txt` — a general-purpose system prompt (Czech, matching the
    platform's established language for user-facing content)
  - `actions.json` — `{"enabled_tools": [...]}` listing all five currently
    catalog tool names (the base profile is the general/default assistant;
    all currently available tools are appropriate for it — this is a
    stated assumption for Architecture Review, not a silent choice)
  - `features.json` — `{"enabled_features": []}`. Neither
    `002_telegram_bridge` nor any ElevenLabs-dependent feature is enabled
    by default; turning them on is a separate, explicit decision, not a
    side effect of this Contract.
- `projects/voice_agent/profiles/profile_loader.py` (new code):
  - `load_profile(name: str, profiles_root: Path, tool_catalog: dict) ->
    Profile` — reads the four files, parses the two JSON files, validates
    every `enabled_tools` entry exists as a `tool_catalog` key (raise a
    clear, specific exception listing exactly which names are unknown if
    not), and returns a small structured result (prompt text, resolved
    tool specs — not just names — and the raw enabled-features list).
  - `list_available_profiles(profiles_root: Path) -> list[str]` — names of
    subdirectories under `profiles_root` that contain the required four
    files.
  - No dependency on `backend/`, `actions/action_loader.py`'s dynamic
    import machinery, or anything live — this loader only reads and
    validates static profile definitions and cross-references the already-
    imported `tool_catalog` dict passed in by the caller.

> Status: Done — all outputs created. One addition beyond the literal list:
> `profiles/__init__.py` (a one-line docstring, matching `actions/__init__.py`
> and `features/__init__.py`), needed for `profiles/profile_loader.py` to be
> importable as part of this project's existing package layout — every
> other top-level code directory here (`backend/`, `actions/`, `features/`)
> already has one. `prompt.txt` is adapted from `jarvis_cesky`'s
> `core/prompt.txt` (the assistant's actual working prompt, consulted for
> tone/persona continuity per P13) rather than from `profiles/000_base/
> prompt.txt` (which is only a one-line placeholder in the source) — tool-
> specific rules for tools this profile's catalog does not contain
> (memory, WhatsApp, reminders, YouTube stats, screen analysis) were
> dropped rather than carried over.

---

# Functional Requirements

The implementation SHALL:

- Create the file structure listed under Outputs.
- Implement `profile_loader.py` exactly as scoped above: pure
  read-validate-return, no side effects, no network or live agent calls.
- Raise a specific, descriptive exception (not a bare `KeyError` or
  silent skip) when `actions.json` references a tool name absent from
  `tool_catalog`.
- Raise a specific, descriptive exception when a named profile directory
  is missing any of the four required files.
- Include a `README.md` update for `projects/voice_agent/` noting the new
  capability and, explicitly, that nothing yet calls `profile_loader.py` —
  it is available and verified in isolation, not wired into a runtime.

> Status: Done — `profile_loader.py` is pure read-validate-return: no
> network calls, no writes, no dependency on `backend/` or
> `action_loader.py`. `ProfileFilesMissingError` (missing-file case) and
> `UnknownToolError` (unknown-tool case) are both distinct, named
> exception classes (subclasses of a common `ProfileError`) carrying the
> specific missing filenames / unknown tool names as attributes and in
> the message — neither is a bare `KeyError` or silent skip.
> `projects/voice_agent/README.md`'s "Current capabilities" and "Current
> limitations" sections were both updated, the latter explicitly stating
> `profile_loader.py` is not wired into any runtime yet.

---

# Out of Scope

This Contract SHALL NOT:

- Wire `profile_loader.py` into `backend/services/agent_runtime.py` or any
  live runtime (Phase 4).
- Create any profile beyond `000_base`.
- Enable `002_telegram_bridge` or any ElevenLabs-dependent feature by
  default.
- Validate `enabled_features` entries against any features registry — no
  such registry exists yet; the loader returns the declared list as-is and
  Phase 4 decides what to do with it.
- Modify `actions/tool_catalog.py` or any transferred code from Contracts
  0002/0003.

> Status: Done — none of these were touched: no wiring into
> `agent_runtime.py` (confirmed unchanged), only `000_base` exists under
> `profiles/`, `002_telegram_bridge` and `001_elevenlabs_voice` are not in
> `000_base/features.json`, `enabled_features` is returned as-is with no
> registry check, and `actions/tool_catalog.py` plus everything from
> Contracts 0002/0003 is untouched (verified: only files under `profiles/`
> and the `README.md` edit already annotated above were added or changed;
> no other file in `projects/voice_agent/` was modified).

---

# Acceptance Criteria

The implementation is accepted when:

- `load_profile("000_base", ...)` succeeds against the real
  `actions.tool_catalog.TOOL_CATALOG` and returns all five tools resolved
  (not just their names).
- Calling `load_profile` with a deliberately broken `actions.json` (an
  unknown tool name) raises a specific, catchable exception identifying
  the unknown name(s) — verified with an actual test call, not just code
  inspection.
- Calling `load_profile` on a profile directory missing `prompt.txt`
  raises a specific, catchable exception — likewise verified by an actual
  test call.
- `list_available_profiles` returns exactly `["000_base"]` against the
  delivered directory.
- No file naming or directory naming violates the Tr5 naming convention.
- The Contract is annotated per DOCUMENT_STANDARD §3.1.

> Status: Done — all Acceptance Criteria verified with actual test calls
> (script written, run, then deleted; not left in the tree):
> `load_profile("000_base", ...)` against the real
> `actions.tool_catalog.TOOL_CATALOG` returned all 5 tools fully resolved
> (asserted each equals, but is not the same object as, the catalog entry —
> confirming the `deepcopy`). A profile with `actions.json` referencing
> `"totally_made_up_tool"` raised `UnknownToolError` naming exactly that
> tool. A profile directory missing `prompt.txt` raised
> `ProfileFilesMissingError` naming exactly that file.
> `list_available_profiles(profiles_root)` against the real delivered
> `profiles/` returned exactly `["000_base"]`. All directory/file names
> are `lowercase_with_underscores` (`profiles/`, `profile_loader.py`,
> `000_base/`) with no diacritics in names (prose content is Czech with
> full diacritics, matching the source project's own code-level Czech
> text, e.g. `tool_catalog.py`'s descriptions — the naming-convention rule
> applies to names, not document/string content). This annotation itself
> satisfies the last criterion.

---

# Architecture Review

### Round 1 — 2026-07-14 — Verdict: Accepted
Reviewer: Architect

Checked against P2/P9: scope is deliberately limited to one profile and
zero runtime wiring, matching the smallest real need rather than building
ahead of it. Checked against P13: the design follows `jarvis_cesky`'s own
documented (if never implemented) intent for `profiles/`, rather than
inventing an unrelated shape — the source's prose is a legitimate design
input even though its code never existed. The explicit "all five tools in
the base profile" and "no features enabled by default" choices are called
out as stated assumptions specifically so this review step is the place
they get confirmed or corrected, not left as a silent implementation
detail. No conflict found with `FOUNDATIONAL_WORLDVIEW.md` or
`PRINCIPLES.md`. Accepted as drafted.

---

# Future Evolution

- A second, genuinely specialized profile (e.g. once `hockey_stats` or
  `home_assistant` exists and the platform-level review defines how they
  connect) would be the real trigger to revisit whether the loader needs
  more than single-profile validation.
- Phase 4: the live agent runtime consumes `profile_loader.py`'s output to
  actually configure a running session.
- `platform_shell` (discussed, not yet scheduled — see PRINCIPLES.md
  Backlog): once it exists, profile selection likely becomes a
  shell-level, not voice_agent-level, concern — revisit then rather than
  guessing now.

---

# Completion Notes

Implemented as specified. Unlike Contracts 0002/0003, this was new code
rather than a transfer, so there was no source commit to `diff` against —
verification instead meant writing a throwaway script that actually called
`load_profile`/`list_available_profiles` against both the real delivered
profile and two deliberately broken temporary ones (built under
`tempfile.TemporaryDirectory`, never inside `projects/voice_agent/`), then
deleting the script once all four assertions passed. `prompt.txt`'s content
is the one place this Contract required an actual creative decision rather
than a mechanical copy or a pure validation routine: `jarvis_cesky`'s
`profiles/000_base/prompt.txt` is a one-line placeholder with no usable
prompt text, so `core/prompt.txt` (the source project's real, currently-
running system prompt) was used as the tone/persona reference instead —
disclosed explicitly in the Outputs annotation above rather than treated
as a silent substitution, since the Contract's Inputs section named only
the `profiles/README.md` files. Tool-specific rules in that source prompt
referencing tools outside this profile's 5-tool catalog (memory, WhatsApp,
reminders, YouTube, screen analysis) were dropped rather than carried over,
since a prompt instructing the model to use nonexistent tools would be
actively wrong, not just extra.

---

# Implementation Review

Self-reviewed against every Functional Requirement and Acceptance
Criterion (see inline annotations above); no gaps found. Two disclosed,
minor additions beyond the Contract's literal text: `profiles/__init__.py`
(mechanical — required for the package to be importable, matching every
sibling directory's existing convention) and using `core/prompt.txt`
rather than an Input-listed file as the prompt's tone reference (a
creative-content decision the Contract required someone to make, since its
only listed reference for prompt content was a non-functional placeholder).
Both are called out explicitly rather than folded in silently, consistent
with how Contracts 0002 and 0003 handled their own minor disclosed
deviations.

---

# Lessons Learned

- For a "new code, not a transfer" Contract, verification can't lean on
  `diff` against a pinned source commit the way 0002/0003 did — a small,
  throwaway, assertion-based script exercising the real success path plus
  every named failure path (built and torn down in the same run) is the
  equivalent rigor for validation logic.
- When a Contract's only listed design-reference Input turns out to be a
  non-functional placeholder (here, `profiles/000_base/prompt.txt`), it's
  worth explicitly checking whether a *related* file elsewhere in the same
  source project (here, `core/prompt.txt`) is actually the load-bearing
  version of that content, and disclosing the substitution rather than
  either inventing from nothing or silently treating the placeholder as
  sufficient.
