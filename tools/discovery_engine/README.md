# Tr5 Discovery Engine

Status: Active

---

## Purpose

The Tr5 Discovery Engine is responsible for discovering objective facts about
the repository and producing an objective representation of its current
state.

It never performs reasoning.
It never makes decisions.
It never modifies the repository.

---

## Responsibilities

- Recursively scan the Repository Root
- Discover directories and files
- Classify each discovered artifact by type
- Collect basic metadata for each artifact
- Generate TR5_CURRENT_STATE.md

The Discovery Engine only reports what exists. It never prescribes or
generates repository structure.

---

## Current capabilities (v1.0)

- Recursive repository scan, excluding `.git/`, `.venv/`, and `.idea/`
  (VCS internals, virtual environment, and IDE state — not platform content)
- Artifact classification: Directory, Markdown Document, Python Source,
  JSON Document, YAML Document, Unknown
- Metadata collection per artifact: Name, Relative Path, Artifact Type
- Deterministic generation of TR5_CURRENT_STATE.md (no timestamp)

---

## Current limitations

Version 1.0 does not:

- inspect file contents
- parse Markdown or Python
- inspect Git history
- validate artifacts
- detect dependencies
- perform reasoning
- use AI
- modify repository contents

---

## Expected evolution

The Discovery Engine is expected to evolve together with the Tr5 Platform.
Future capabilities may include:

- Git Discovery
- Markdown Discovery
- Python Discovery
- Metadata Extraction
- Validation
- Dependency Discovery
- Repository Metrics
- AI Context Generation

These capabilities are intentionally excluded from Version 1.0.
