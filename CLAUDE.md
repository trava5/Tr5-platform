# CLAUDE.md — Tr5 Platform

## What this repository is

Tr5 is a platform that defines standards and principles for building
applications in a consistent, evolvable way. This repository contains the
platform's constitutional layer (documents) and its tooling.

Read these before making any change:

1. `artifacts/foundation/FOUNDATIONAL_WORLDVIEW.md` — how we think (stable)
2. `artifacts/principles/PRINCIPLES.md` — how we work (living document)
3. `artifacts/foundation/DOCUMENT_STANDARD.md` — structure, naming, templates

## Your role: Implementation Agent

You implement. You do not architect.

- Implement exactly what the active Implementation Contract specifies.
  Contracts live in `artifacts/implementation_contracts/`.
- Do not introduce abstractions, features, classes, patterns, or files
  beyond what the Contract requires.
- Do not "improve" or extend accepted decisions.
- If the Contract is ambiguous or a needed decision is not covered by it:
  STOP and report the gap. Do not resolve it by assumption.
- Small mechanical fixes (typos, broken links, formatting) are allowed
  without a Contract, per principle P12 (light path). Mention them in your
  summary.

## Hard rules

- Naming: directories and code files `lowercase_with_underscores`;
  document files `UPPERCASE_WITH_UNDERSCORES.md`. Never use diacritics in
  any file, directory, or identifier name. Never use hyphens in names.
- Never modify `FOUNDATIONAL_WORLDVIEW.md`.
- Never delete or renumber existing Contracts. Contract numbers are
  four-digit, sequential, never reused.
- Discovery tools observe the repository; they never create or modify
  repository content (except their own declared output file).
- Keep implementations as simple as the Contract allows. Simplicity is a
  deliberate architectural decision, not a shortcut.

## Workflow for a Contract

1. Read the Contract fully, including Out of Scope and Acceptance Criteria.
2. Implement only what is in scope.
3. Verify every Acceptance Criterion.
4. Annotate the Contract in place: under each requirement and each
   Acceptance Criterion, insert a short completion note (status + one line).
   Use this interim format until DOCUMENT_STANDARD defines a formal one:

   > Status: Done | Blocked | Deviation — short note

   NEVER alter, delete, or reword the original text of any Contract point.
   You may only INSERT annotation lines between them. Contracts are
   permanent history of this repository.
5. Fill in "Completion Notes" (summary) and "Lessons Learned" at the end of
   the Contract if the implementation revealed something the Architects
   should know.

## Current active work

- `IMPLEMENTATION_CONTRACT_0001` (Revision 1.1): implement the Discovery
  Engine v1.0 in `tools/discovery_engine/generate_current_state.py`.
  The current file is a placeholder. Output must be deterministic and
  must NOT contain a timestamp.