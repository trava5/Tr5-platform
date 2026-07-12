# Tr5 Document Standard

Status: Accepted v1.0

---

## Purpose

This document defines how Artifacts are structured, named, and written across
the Tr5 Platform, so that any contributor — human or agent — produces output
that looks and behaves consistently, regardless of which project it belongs
to.

This standard applies to the platform itself and to every project built on
top of it.

---

## 1. Directory Structure

Every Tr5-based repository SHALL follow this top-level shape:

```
<project>/
│
├── README.md
│
├── artifacts/
│   ├── foundation/
│   │   ├── FOUNDATIONAL_WORLDVIEW.md
│   │   └── DOCUMENT_STANDARD.md
│   │
│   ├── implementation_contracts/
│   │   └── IMPLEMENTATION_CONTRACT_XXXX.md
│   │
│   └── principles/
│       └── PRINCIPLES.md
│
├── tools/
│   └── <tool_name>/
│       ├── README.md
│       └── <source_files>
│
└── src/
```

Rules:

- `artifacts/` holds everything with identity, a current state, and a
  lifecycle (Worldview, Principles, Contracts, and future Packages/Decisions).
- `tools/` holds software that operates *on* artifacts (e.g. Discovery
  Engine). Tools are not themselves artifacts in the philosophical sense —
  they are implementations produced by Contracts.
- `src/` is reserved for actual application code (e.g. the voice agent, video
  analysis, Home Assistant integration) — kept separate from platform
  tooling.
- New top-level directories are only added when the Discovery Engine's
  Current State shows a real, existing need for one — never speculatively
  (per P2, P3).

---

## 2. Naming Conventions (Accepted)

- **Directories:** `lowercase_with_underscores` (e.g. `implementation_contracts/`,
  `discovery_engine/`).
- **Document files** (`.md` artifacts such as Worldview, Principles,
  Contracts, standards): `UPPERCASE_WITH_UNDERSCORES.md` (e.g.
  `FOUNDATIONAL_WORLDVIEW.md`, `IMPLEMENTATION_CONTRACT_0001.md`,
  `DOCUMENT_STANDARD.md`).
- **Source code and other files** (Python, config, tool READMEs' filenames):
  `lowercase_with_underscores` (e.g. `generate_current_state.py`).
- **Diacritics:** never used, in any file, directory, or identifier name —
  ASCII only, regardless of the language used in discussion.
- **Contract numbering:** four-digit zero-padded sequence
  (`0001`, `0002`, ...), never reused.

This resolves the naming inconsistency previously flagged as an open
question.

---

## 3. Implementation Contract Template

Every Contract SHALL follow this structure (established by Contract #0001):

```markdown
# IMPLEMENTATION_CONTRACT_XXXX

Status: Draft | Accepted | Implemented | Rejected

## Title
## Purpose          (Why — architectural intent, for humans)
## Intent
## Current State    (what exists today, per Discovery Engine)
## Inputs
## Outputs
## Functional Requirements   (SHALL)
## Out of Scope               (SHALL NOT)
## Acceptance Criteria
## Future Evolution           (explicitly excluded, not forgotten)
## Completion Notes            (filled after implementation)
## Lessons Learned             (filled after implementation)
```

A Contract separates two concerns, always:

- **Why** — belongs to humans, is the architectural justification.
- **What** — belongs to implementation, is the precise, testable
  specification.

---

## 4. README Standard for Tools / Artifacts

Every significant Artifact or tool SHALL have its own `README.md` containing:

```markdown
# <Name>

## Purpose
## Current capabilities (vX.Y)
## Current limitations
## Planned evolution
```

The README should change rarely — it describes responsibility, not
implementation detail. When capabilities grow, the "Current capabilities"
list grows; the Purpose section should stay stable.

---

## 5. Agent Behavior (summary)

Full instruction lives in each Contract handoff, but the standing rule for
any Implementation Agent (Claude Code, Codex, or other) is:

- Implement exactly what the active Contract specifies.
- Do not introduce architecture, abstractions, or features beyond it.
- If something required isn't covered by the Contract, stop and report —
  do not assume.
- Output must follow the directory structure and naming patterns in this
  document, so all projects under Tr5 remain structurally consistent.

(A dedicated `AGENT-GUIDE.md` with fuller, project-agnostic instructions is a
natural next document — proposed once the repo is connected and current
state is confirmed.)

---

## Open Questions (Backlog)

- Whether `src/` needs its own sub-standard once the first real project
  (voice agent) begins.
- Format of `implementation_packages/*.json` once that stage of the pipeline
  is implemented.
