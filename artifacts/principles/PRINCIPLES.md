# Tr5 Principles

Status: Living Document — Draft v0.1 (pending review against actual repository state)

---

## Purpose

This document collects the operating principles of the Tr5 Platform.

Unlike `FOUNDATIONAL-WORLDVIEW.md`, which is stable and changes rarely, this
document is expected to grow and be revised as the platform accumulates
experience.

A principle exists here because it was *discovered through practice*, not
because it was assumed in advance.

---

## Revision Process

Every principle SHALL be reviewed after each pass through the Implementation
Pipeline in which it was relevant.

A review answers one question:

> Did this principle serve the decision well, or does it need to be revised?

Each principle carries a `Status` field:

- **Active** — currently guiding decisions, no revision needed yet.
- **Under Review** — a recent case raised doubt; being reconsidered.
- **Revised** — superseded by a newer formulation (link to replacement).
- **Deprecated** — no longer applies; kept for historical record.

Principles are never silently deleted. Deprecated principles remain in this
document with a reason, so future contributors understand *why* something
that once made sense no longer does.

---

## Principles

### P1 — Architecture defines direction. Implementation reflects current understanding.
Status: Active

Architecture may anticipate the future. Implementation SHALL NOT. Every
implementation reflects only what is known and needed today.

### P2 — Implement today's understanding, not tomorrow's assumptions.
Status: Active

If a capability is not required by the current Implementation Contract, it is
not built — even if it seems obviously useful later.

### P3 — Discovery observes reality. It never creates it.
Status: Active

Any tool or process whose purpose is to describe the current state of the
system (e.g. the Discovery Engine) SHALL NOT prescribe or generate structure.
It only reports what already exists.

### P4 — Current State contains facts, never interpretations.
Status: Active

Discovery output is objective: names, paths, types. No reasoning, no
evaluation, no quality judgment belongs in a Current State document.

### P5 — Discovery precedes reasoning.
Status: Active

Before any decision is made about what should change, the current state must
be established through discovery — not assumed from memory or intention.

### P6 — Every implementation begins with an explicit architectural intent.
Status: Active

No code is written without a preceding Implementation Contract that states
*why* it is needed, not only *what* it is.

### P7 — Human-readable intent and machine-readable execution are separate representations of the same decision.
Status: Active

The Implementation Contract (`.md`) and the future Implementation Package
(`.json`) express one decision for two different audiences: humans and
agents. They must never diverge in meaning.

### P8 — One decision may have multiple representations, but only one intent.
Status: Active

If a Contract and its Package (or its implementation) disagree, the
disagreement itself is a defect to resolve — not a matter of preference.

### P9 — Validate architecture before scaling implementation.
Status: Active

A new pattern, tool, or structural decision is proven on the smallest
possible case (e.g. Discovery Engine v1.0) before it is generalized.

### P10 — Implementation Contracts are Artifacts.
Status: Active

Contracts have identity, a current state, and a lifecycle, like any other
Artifact. They live under `artifacts/`, not under `tools/` or elsewhere.

### P11 — An Implementation Agent implements; it does not architect.
Status: Active

An agent executing a Contract does not introduce abstractions, features, or
simplifications beyond what the Contract specifies. If a gap requires an
architectural decision, the agent reports it instead of deciding.

### P12 — Process weight must match decision weight.
Status: Active

The full pipeline exists to protect structural, hard-to-reverse decisions.
Small, reversible changes take the light path. A process that taxes every
step will eventually be abandoned — and an abandoned process protects
nothing.

### P13 — Standards are extracted from working systems, not invented in advance.
Status: Active

A convention earns its place in the platform by proving itself inside a real
project first. The constitutional layer stays minimal until reality demands
more.

### P14 — Discovery reflects platform content, not incidental local tooling.
Status: Active

Extracted from the first Discovery Engine run (Contract 0001): a literal
filesystem scan surfaces VCS internals, virtual environments, and IDE state
— none of which represent the platform itself, and which can drown out the
signal entirely (in practice, one such directory outnumbered every real
artifact combined). Discovery output SHALL exclude this kind of incidental
content.

The first implementation (v1.0) did this via a hardcoded exclusion list,
flagged as provisional. A second real case (Contract 0002's testing
produced gitignored `__pycache__/` that still showed up in
`TR5_CURRENT_STATE.md`) confirmed the concern per P13. Resolved in
Discovery Engine v1.1 (Contract 0001, Revision 1.2): exclusion is now
`.gitignore`-aware; only `.git` remains hardcoded as a permanent baseline.

---

### P15 — Verify byte-identity after any transfer, don't trust the copy mechanism.
Status: Active

Extracted from Contract 0002: `git archive | tar -x` silently normalized
line endings on Windows even from a clean, correctly-pinned working tree.
A plain file copy plus an explicit `diff` check against the source is safer
for "transfer, unmodified" Contracts than any tool assumed to be
transparent. Applies to every future transfer phase (voice agent Phases
2–4 and any later project onboarding).

Confirmed a second time in Contract 0003 with no new exceptions — this is
now the standard transfer method, not a per-Contract decision.

---

### P16 — A named risk applies to its pattern, not to its filename.
Status: Active

Extracted from Contract 0003: the Contract explicitly named
`calendar.py`'s path-resolution risk (`BASE_DIR` computed from file
nesting depth) but not `bridge.py`'s, even though both share the identical
pattern. The Implementation Agent verified both anyway and stated why. This
was correct, and is the expected behavior, not scope creep: per P11 an
agent does not invent new requirements, but recognizing that a stated risk
is a property of a code pattern — and applies wherever that pattern
recurs — is implementation, not architecture. A Contract cannot always
enumerate every file a given risk touches; it states the risk, and
verifying its actual extent is part of doing the work.

---

### P17 — Click is the universal interface. Voice is an opt-in layer above it.
Status: Active

Every application on the platform SHALL have a "click" interface — this is
the mandatory, universal control surface. Voice is a second, optional layer
above select applications/functions, not a parallel universal interface.
`platform_shell` (see Backlog) is the single control surface every project
connects to; it is designed around click as the primary case, with voice
support added where it makes sense, not derived from voice_agent's needs.

Every project's backend SHALL follow the same shared template/conventions
(per DOCUMENT_STANDARD), so `platform_shell` can talk to any of them
uniformly. Each project's frontend surface may differ in specifics (what
can be clicked, what it does), but the shape of the connection — how
`platform_shell` discovers and talks to a project — should not.

Practical consequence for `platform_shell`'s eventual design: `voice_agent`
is used as one real test case to validate the connection standard against
(per P13 — extract from a working system), not as the template the
standard is copied from. Building `voice_agent` first does not mean voice
comes first architecturally.

---

### P18 — Not every entity is a platform Artifact. Some are implementation detail inside one.
Status: Active

`FOUNDATIONAL_WORLDVIEW.md` states every entity is represented as an
Artifact in its current State. This does not mean every function, module,
or agentic action gets its own platform-level lifecycle (Contract, README,
Architecture/Implementation Review). A platform Artifact is something with
its own identity, lifecycle, and review history at the platform level —
a Contract, a foundational document, a project (`voice_agent`,
`platform_shell`, ...). An individual action like `get_weather` or
`add_calendar_event` is an implementation detail inside the Artifact that
Contract 0003 created (`voice_agent`'s `actions/`) — it doesn't need its
own Artifact status. Treating every internal detail as a full Artifact
would violate P12 (process weight matches decision weight) by ceremony
alone.

---

### P19 — Dependency verification must include deferred imports, not just module-level ones.
Status: Active

Extracted from a live test after Contract 0005: `calendar.py`'s Google
Calendar API imports (`googleapiclient`, `google.oauth2.credentials`, etc.)
are deferred inside a function body, not declared at module top level.
Contract 0003's dependency check searched only top-level `import`/`from`
lines (`grep "^from \|^import "`), missed these, and shipped a
`requirements.txt` that let the module *import successfully* while still
failing at actual call time with a real user waiting on a real answer —
worse than an import-time failure, because it surfaces late, inside a
production-shaped code path, not during setup.

Live end-to-end testing (a human sending real messages against a real
model, not just structural verification) found this in minutes; static
review of the code had not. Neither replaces the other: structural review
catches shape/contract violations early and cheaply, live testing catches
what only shows up when real inputs meet real code paths. Both remain
part of the process — this is not a reason to make live testing mandatory
for every Contract (P12), but a documented reminder that "no top-level
import found" is not the same claim as "no dependency exists."

---

### P20 — An uncommitted local fix is invisible to the next review cycle and can be silently overwritten.
Status: Active

Extracted from a real incident: Contract 0003's Google Calendar dependency
fix (Revision 1.1) was applied locally by the person (confirmed by their
own successful `pip install` log) but never committed. A later, unrelated
fix (Contract 0005 Revision 1.3, `tzdata`) was built by the Architect from
a fresh clone of the repository — which, lacking the uncommitted local
change, produced a `requirements.txt` missing the Calendar packages. The
person then applied that zip on top of their working copy, silently
reverting their own local fix.

The Architect's review process always works from a fresh clone (deliberate
— it is the only way to review what is actually true, not what is assumed
true). This is correct and SHALL NOT change. The consequence is that any
local change not yet committed effectively does not exist from the
Architect's point of view, and a subsequent delivered fix can overwrite it
without either party noticing until a symptom reappears. Mitigation:
commit and push immediately after applying any delivered fix, before
starting the next piece of work — already the standing instruction after
every review, but this incident is the concrete reason it matters, not
just process hygiene for its own sake.

---

### P21 — Verification code must be structurally incapable of touching real external systems, not just instructed to avoid them.
Status: Active

Extracted from a serious incident in Contract 0006: automated verification
of Acceptance Criteria made two real Gemini API calls and wrote real rows
into the person's real home Postgres database — a production system, not
a test fixture. Root cause was not carelessness but a genuine structural
trap: `os.environ.pop("GEMINI_API_KEY")` does not simulate "unset" against
this codebase's `_load_env_file()` (which only skips keys already present,
so popping one makes it reload from the real `.env`), and
`backend/app.py`'s module-level `app = create_app()` (required for
uvicorn's `module:app` import string) runs real settings loading as a side
effect of merely *importing* the module — before any test-local isolation
code gets a chance to run.

The Implementation Agent handled the aftermath well: immediate disclosure,
explicit permission requested before deleting anything, precise
content-matched deletion, verified before/after. That response is the
standard to hold — but the goal is for this situation not to recur, not
just to be handled gracefully when it does.

This time the damage was a handful of junk conversation rows and two
inexpensive API calls. The same class of gap could, in a future Contract,
trigger a real side-effecting tool (e.g. `add_calendar_event` against the
person's actual calendar) during "verification." Acceptance Criteria that
say "verify without a real API key" or "no real database" describe an
*intent*; they are not a *mechanism*. Future Contracts touching anything
that can reach a real external system SHALL specify the actual isolation
mechanism (e.g. dependency injection of fakes with no environment-variable
path to real credentials at all, subprocess isolation with a
deliberately-empty environment, or an explicit `TESTING`-gated code path
that a real deployment can never accidentally take) — not simply instruct
"don't use the real one."

Open follow-up, not yet resolved: `backend/app.py`'s module-level
`create_app()` side effect on import is itself worth revisiting — a
future Contract should consider whether the app factory can be made safe
to import without side effects, independent of whatever test discipline
individual Contracts practice.

---

## Roles

| Role | Responsibility |
|---|---|
| Architect | Discovers, discusses, decides, writes Contracts |
| Implementation Agent | Implements exactly what a Contract specifies; reports gaps instead of resolving them |
| Architecture Reviewer | Verifies implementation against Contract and Worldview before acceptance |

---

## Accepted Pipeline

Two speeds, chosen by the weight of the decision:

**Structural decisions** (new tools, new directory shapes, new standards,
anything hard to reverse):

```
Discussion
    ↓
Accepted Decisions
    ↓
Implementation Contract (.md)
    ↓
Architecture Review ✅
    ↓
Implementation Agent
    ↓
Repository
    ↓
Discovery Engine
    ↓
TR5_CURRENT_STATE.md
```

**Small, reversible changes** (fixes, typos, additive tweaks within an
existing Contract's scope):

```
Change
    ↓
Repository
    ↓
noted at the next Architecture Review / Discovery pass
```

Note: the Implementation Package (`.json`) step was removed from the default
pipeline. A Markdown Contract is already machine-readable for current agents
(e.g. Claude Code). The Package returns only if a future agent actually
requires it (see Backlog).

---

## Open Questions (Backlog)

These are known unresolved decisions. They are intentionally left open until
a real case forces the decision — per P2.

- **[Priority — safety-relevant] Test/production isolation mechanism
  (P21).** `backend/app.py`'s module-level `app = create_app()` triggers
  real settings loading on import, which contributed to a real incident
  (Contract 0006) where verification code reached the person's real
  Gemini API and real Postgres database. Needs a real structural fix
  (dependency injection, subprocess isolation, or a `TESTING`-gated path),
  not just documented caution. Should be addressed before Phase 4c
  (Telegram bridge — a channel with its own real external side effects)
  if not sooner, given it directly affects verification safety for every
  subsequent Contract.
- **`projects/platform_shell/` (future direction, discussed not yet
  scheduled).** Tr5 needs a universal entry point for the whole platform —
  see P17 for the accepted design stance (click is the mandatory, primary
  interface; voice is an opt-in layer above select functions, not a
  parallel universal one). This is a separate project, not part of
  `voice_agent` — `voice_agent` is a capability provider, `platform_shell`
  is the control surface. Every project's backend follows the same shared
  template so `platform_shell` can connect uniformly; frontend specifics
  differ per project. Not scheduled yet — Phase 4 of the voice agent
  transfer finishes first, so this work doesn't interrupt an in-flight
  task. Explicit risk to guard against when this is scheduled: do not
  design the connection standard by copying `voice_agent`'s shape —
  `voice_agent` is one validating test case (per P13), and being built
  first must not make it the template. Expect substantial discussion when
  this starts. This is also where the deferred "does this app get
  voice/click control, and where is that decision recorded" question gets
  resolved for real.
- **`jarvis_cesky` governance migration.** This external project already runs
  its own working ADR/AGENTS.md system (17 accepted ADRs, proven in
  practice) — a parallel, more mature analog of Tr5's Contract/CLAUDE.md
  system. Decision: migrate it to Tr5's system gradually, once its current
  migration (`MIG-006`/`MIG-007`, backend/realtime work) reaches a stable
  point. Do not force this now — it would compete with in-flight work. When
  resumed: (a) extract proven patterns from its ADRs into PRINCIPLES.md
  first per P13 (e.g. actions/features/profiles separation, numbered
  subdirectories, shared-backend-multi-client architecture), (b) only then
  introduce Tr5 Contracts for new work in that repo, (c) never rewrite its
  existing ADR history — it is append-only, same principle as our own.
  Known, still-open security items in that repo (independent of governance
  question, can be fixed anytime): committed Telegram voice recordings
  (`.oga` files) in `features/002_telegram_bridge/konverzace/`, missing
  `.idea/` and `*.log` entries in `.gitignore`.
- Format and scope of the future `implementation_packages/` (`.json`)
  representation.
- Whether Contracts eventually need a richer lifecycle folder structure
  (`draft/`, `accepted/`, `implemented/`) — deferred until Current State
  shows a real need.
