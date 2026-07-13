# IMPLEMENTATION_CONTRACT_0001

Status: Implemented (Revision 1.1)

---

# Title

Implement Tr5 Discovery Engine v1.0

---

# Purpose

Implement the first version of the Tr5 Discovery Engine.

The Discovery Engine is responsible for discovering objective facts about the repository and producing an objective representation of its current state.

Version 1.0 validates the Tr5 Discovery Pipeline and the complete implementation workflow.

---

# Intent

This implementation is intentionally simple.

Its purpose is not to build a complete repository analysis framework.

Its purpose is to validate:

- Discovery Pipeline
- Implementation Pipeline
- Implementation Contracts
- Current State generation
- Human → Machine handoff

The implementation is expected to evolve together with the Tr5 Platform.

Simplicity is a deliberate architectural decision.

---

# Current State

The current repository contains the initial Tr5 documentation.

The implementation SHALL represent the repository exactly as it exists today.

No assumptions shall be made about future repository structure.

---

# Inputs

Repository Root

---

# Outputs

TR5_CURRENT_STATE.md

---

# Functional Requirements

The implementation SHALL:

- recursively scan the repository
- discover directories
- discover files
- classify artifacts
- collect basic metadata
- generate TR5_CURRENT_STATE.md

> Status: Done — implemented in `tools/discovery_engine/generate_current_state.py`
> (scan_repository, classify_artifact, render_markdown, save_current_state).
> `.git/`, `.venv/`, `.idea/` are excluded from the scan (see Completion Notes).

---

# Artifact Classification

Version 1.0 classifies artifacts only by type.

Supported artifact types:

- Directory
- Markdown Document
- Python Source
- JSON Document
- YAML Document
- Unknown

---

# Metadata

For every discovered artifact collect only:

- Name
- Relative Path
- Artifact Type

No additional metadata shall be collected in Version 1.0.

---

# Output Format

The generated document SHALL contain:

- Repository structure
- Artifact list
- Generator identification (name and version)

The output SHALL be deterministic:
the same repository state SHALL always produce byte-identical output.

For this reason the output SHALL NOT contain a generation timestamp.
(Timestamps belong to version control, not to the Current State document.)

> Status: Done — verified by running the generator twice against an
> unchanged repository state and diffing the output (byte-identical).
> No timestamp is written.

---

# Repository Structure

Create:

```text
tools/
└── discovery_engine/
    ├── README.md
    └── generate_current_state.py
```

---

# Discovery Engine README

Create README.md describing:

- Purpose
- Responsibilities
- Current capabilities
- Current limitations
- Expected evolution

> Status: Done — `tools/discovery_engine/README.md` rewritten with exactly
> these five sections. Renamed from `READMe.md` (casing typo) to `README.md`
> to match the Repository Structure section below (light-path fix, P12).

---

# Out of Scope

Version 1.0 SHALL NOT:

- inspect file contents
- parse Markdown
- parse Python
- inspect Git history
- validate artifacts
- detect dependencies
- perform reasoning
- use AI
- modify repository contents

---

# Acceptance Criteria

The implementation is accepted when:

- the repository is successfully scanned
- all artifacts are discovered
- artifact types are classified
- TR5_CURRENT_STATE.md is generated
- the output is deterministic
- README.md exists for the Discovery Engine

> Status: Done — all six criteria verified. See Completion Notes.

---

# Architecture Review

### Round 1 — 2026-07-09 — Verdict: Accepted
Reviewer: Architect

Checked against four questions agreed for this Contract: does the
implementation serve its purpose (yes); does it add unnecessary complexity
(no); does it implement only Current State (yes); is it ready to evolve
without pre-building that evolution (yes). Marked Ready for Implementation.

### Round 2 — 2026-07-12 — Verdict: Changes Requested
Reviewer: Architect

Reviewed the repository against this Contract before implementation had
happened. Found: (1) the Output Format required both a deterministic output
and a generation timestamp — self-contradictory, since a timestamp changes
on every run; (2) file names used hyphens
(`FOUNDATION-WORLDVIEW.md`, `IMPLEMENTATION-CONTRACT-0001.md`) inconsistent
with the accepted `UPPERCASE_WITH_UNDERSCORES` convention; (3) the root
README linked a Worldview filename that did not match the actual file;
(4) `.idea/` was committed. Resolved via Revision 1.1: timestamp requirement
removed from Output Format (see Revision Notes below), naming and README
link corrected directly in the repository (outside this Contract's own
text, as housekeeping per P12), `.gitignore` added.

---

# Future Evolution

Potential future capabilities include:

- Git Discovery
- Markdown Discovery
- Python Discovery
- Metadata Extraction
- Validation
- Dependency Discovery
- Repository Metrics
- AI Context Generation

These capabilities are intentionally excluded from Version 1.0.

---

# Completion Notes

Implemented `tools/discovery_engine/generate_current_state.py` per the
pipeline described in the Discovery Engine README: filesystem discovery →
artifact classification → metadata collection → markdown rendering →
`TR5_CURRENT_STATE.md`.

`generate_current_state.py` walks the Repository Root (defaults to the
directory two levels above the script, i.e. the repository root; overridable
via an optional CLI argument), classifies each artifact, and writes
`TR5_CURRENT_STATE.md` at the Repository Root with LF line endings and no
timestamp. Verified deterministic by running it twice against an unchanged
repository state and diffing the byte-identical output.

`tools/discovery_engine/READMe.md` was renamed to `README.md` (casing typo)
and rewritten to the five sections required by this Contract.

Ran against the actual repository; output reviewed manually and matches the
current repository contents (see `TR5_CURRENT_STATE.md`).

---

# Implementation Review

### Round 1 — 2026-07-13 — Verdict: Accepted
Reviewer: Architect

Verified by cloning the repository fresh and inspecting the result
directly, not just reading the Agent's notes. Confirmed:
`generate_current_state.py` is a real, executable implementation (not the
placeholder that preceded it); `TR5_CURRENT_STATE.md` exists at the
repository root with no timestamp; the file's own header identifies the
generator and version. Re-ran the generator conceptually via the Agent's
own determinism check described in Completion Notes (byte-identical output
across two runs) — accepted the Agent's verification rather than
re-executing it myself, since the method described (diff of two runs) is
sufficient evidence and independently reproducible. Confirmed per-point
annotations exist under Functional Requirements and Acceptance Criteria,
in the format defined by §3.1, with original Contract text left untouched.
Status changed to `Implemented`.

### Round 2 — 2026-07-13 — Verdict: Accepted
Reviewer: Architect

Discovered while testing Contract 0002 (unrelated task): running `uvicorn`
against the transferred `voice_agent/backend` created local `__pycache__/`
directories. Re-ran the Discovery Engine and found they appeared in
`TR5_CURRENT_STATE.md` despite being gitignored — confirming, with a real
case, the risk flagged in this Contract's original Lessons Learned. Applied
Revision 1.2 directly (light path, P12): replaced the hardcoded exclusion
set with `.gitignore`-aware logic covering both directories and files.
Verified: (1) `python3 -m py_compile` passes; (2) fresh run produces zero
`__pycache__`/`.pyc` entries; (3) `.idea`/`.venv` remain excluded, now via
`.gitignore` rather than a hardcoded name; (4) two consecutive runs are
still byte-identical (determinism preserved). Generator version confirmed
as `1.1` in the rendered header.

---

# Lessons Learned

The working tree contains directories that are not Tr5 platform content:
`.git/` (VCS internals), `.venv/` (virtual environment, 764 files — the
large majority of the raw filesystem), and `.idea/` (IDE state). The
Contract did not specify how to treat these, and scanning them literally
would have made `TR5_CURRENT_STATE.md` almost entirely pip-package noise
rather than a representation of the platform. Per P11, this was raised to
the Architect rather than decided unilaterally; the Architect chose to
exclude `.git/`, `.venv/`, and `.idea/` by name
(`EXCLUDED_DIRECTORY_NAMES` in `generate_current_state.py`).

This exclusion list is currently hardcoded and undocumented at the Contract
level. A future Contract revision may want to formalize an ignore-list
mechanism (e.g. respecting `.gitignore`, or an explicit Discovery Engine
config) rather than relying on a hardcoded constant in the implementation.
---

# Revision Notes

## Revision 1.1

- Removed the generation timestamp from the required output.
  Reason: a timestamp contradicts the requirement of deterministic output.
  Determinism is the more important property — it makes changes to
  TR5_CURRENT_STATE.md meaningful in version control.
- File and output names aligned with the accepted naming convention
  (UPPERCASE_WITH_UNDERSCORES, no hyphens, no diacritics).

## Revision 1.2

- Replaced the hardcoded `EXCLUDED_DIRECTORY_NAMES` set with
  `.gitignore`-aware exclusion (directories and, newly, files). Reason:
  confirmed by a real case (see Implementation Review Round 2) that the
  hardcoded list drifted from `.gitignore` — `__pycache__/` and `*.pyc`
  were gitignored (never actually committed) but still appeared in
  `TR5_CURRENT_STATE.md`, violating P4 (Current State contains facts).
  `.git` remains hardcoded as a permanent baseline exclusion, independent
  of `.gitignore` content. This resolves the backlog item raised in this
  Contract's original Lessons Learned and closes P14's "provisional"
  status. Generator version bumped to 1.1.
- This is a small, reversible change (P12 — light path): fixed directly,
  documented here rather than via a new Contract, per the same housekeeping
  precedent as Revision 1.1.
