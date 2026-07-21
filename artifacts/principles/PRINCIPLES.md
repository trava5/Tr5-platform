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
