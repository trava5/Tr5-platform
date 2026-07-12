# Tr5 Principles

Status: Living Document — v1.0 (Accepted)

---

## Purpose

This document collects the operating principles of the Tr5 Platform.

Unlike `FOUNDATIONAL_WORLDVIEW.md`, which is stable and changes rarely, this
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

- Format and scope of the future `implementation_packages/` (`.json`)
  representation.
- Whether Contracts eventually need a richer lifecycle folder structure
  (`draft/`, `accepted/`, `implemented/`) — deferred until Current State
  shows a real need.
