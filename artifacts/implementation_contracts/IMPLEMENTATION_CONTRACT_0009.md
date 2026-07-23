# IMPLEMENTATION_CONTRACT_0009

Status: Accepted

---

# Title

Desktop Audio Client: microphone capture and playback against the
`/live/audio` WebSocket endpoint (Phase 4b-2)

---

# Purpose

Give the platform its first real, audible voice interaction: a standalone
script that captures microphone audio, streams it to the backend's
`/api/v1/live/audio` endpoint (Contract 0008), and plays back the model's
spoken response — closing the loop Phase 4b set out to build.

This is intentionally a plain console client, not a GUI. `platform_shell`
(P17, not yet scheduled) is where a real interface eventually lives; this
Contract proves the audio path works at all.

---

# Intent

- Reuse the platform's own established backend-location convention
  (`JARVIS_BACKEND_BASE_URL` / `JARVIS_BACKEND_HOST` / `JARVIS_BACKEND_PORT`,
  already defined and used by `realtime_client.py`, Contract 0002) rather
  than inventing new environment variables for "where is the backend" —
  per P13, this is exactly the kind of already-proven convention that
  should be extended, not duplicated under a different name.
- Reuse `jarvis_cesky`'s confirmed audio parameters (16-bit PCM, mono,
  16kHz send / 24kHz receive, 1024-frame chunks) — already validated as
  correct against Gemini Live's actual requirements by Contract 0008's
  `AUDIO_INPUT_MIME_TYPE`.
- Mirror `realtime_client.py`'s synchronous `websockets.sync.client`
  style (Contract 0002's proven pattern) rather than introducing `asyncio`
  just for this client — consistency over cleverness (P13), unless the
  Implementation Agent finds a concrete reason this specific case needs
  otherwise, in which case report and justify it rather than switching
  silently.
- Genuinely open technical question, named rather than guessed: whether
  `websockets.sync.client`'s connection object supports safe concurrent
  use from two threads (one continuously sending microphone audio, one
  continuously receiving playback audio/transcripts). The Implementation
  Agent SHALL verify this against current `websockets` library
  documentation/behavior and choose a safe approach (e.g. a lock, a
  single-threaded event-driven loop, or confirmed-safe concurrent use) —
  report which was found and why, per P11.
- No GUI, no `platform_shell` integration, no wake-word, no
  push-to-talk — continuous streaming while the script runs, stopped with
  Ctrl+C. Simplicity matches what Phase 4b-1 already proved; anything
  fancier belongs to `platform_shell`'s eventual design.

---

# Current State

- `backend/services/gemini_live_audio_handler.py` (Contract 0008) accepts
  raw binary PCM audio frames over `/api/v1/live/audio` and sends back:
  binary audio frames (24kHz PCM), and JSON messages
  (`{"type": "transcript", "role": ..., "text": ...}`,
  `{"type": "turn_complete"}`, and an error shape if the runtime is
  unavailable).
- `backend/realtime_client.py` establishes the env var convention and
  sync-websockets style this Contract reuses; it is not itself extended
  or modified — this Contract adds a new, separate client script.
- No audio-capable client exists anywhere in Tr5 yet; `pyaudio` is not in
  `requirements.txt`.
- `jarvis_cesky`'s `main.py` (reference only) confirms:
  `FORMAT=pyaudio.paInt16`, `CHANNELS=1`, `SEND_SAMPLE_RATE=16000`,
  `RECV_SAMPLE_RATE=24000`, `CHUNK_SIZE=1024`.

---

# Inputs

- `backend/realtime_client.py`'s env-var/URL-construction pattern
  (reference for consistency, not imported directly — this client can run
  on a different machine than the backend, so it gets its own small,
  self-contained copy of the same logic rather than a cross-package
  import of another module's private helpers).
- `jarvis_cesky`'s `main.py` audio constants (reference only).

---

# Outputs

- `projects/voice_agent/client/live_audio_client.py` (new):
  - Resolves the backend WebSocket URL using the same env vars as
    `realtime_client.py` (`JARVIS_BACKEND_BASE_URL` /
    `JARVIS_BACKEND_HOST` / `JARVIS_BACKEND_PORT`, plus an explicit
    override var for the audio path if useful), pointed at `/live/audio`
    instead of `/realtime`.
  - Opens a microphone input stream (`pyaudio`, 16-bit PCM, mono, 16kHz,
    1024-frame chunks) and continuously sends each chunk as a binary
    WebSocket message.
  - Opens a speaker output stream (24kHz) and plays back each binary
    message received from the server.
  - Parses non-binary (text/JSON) messages and prints transcripts to the
    console in a readable form (e.g. `"[user] ..."` / `"[assistant]
    ..."`), and handles the error shape from Contract 0008 (prints a
    clear message and exits, rather than crashing unhelpfully, when the
    server reports `runtime_unavailable`).
  - Clean shutdown on Ctrl+C / connection close: streams and the
    WebSocket connection are closed properly, no orphaned threads.
- `projects/voice_agent/requirements.txt`: `pyaudio` added.
- `projects/voice_agent/README.md`: run instructions for the client
  (`python -m client.live_audio_client` or equivalent), and a note that
  this requires a working microphone/speakers and is verified by the
  person locally, not by the Architect.

---

# Functional Requirements

The implementation SHALL:

- Implement `live_audio_client.py` exactly as scoped above.
- Resolve and document (in Completion Notes) the concurrent send/receive
  safety question named in Intent, with the approach actually used and
  why.
- Handle the `runtime_unavailable` error message from the server
  gracefully (clear console message, clean exit) — verified with an
  actual test against a running backend that has no `GEMINI_API_KEY`
  configured (this part *is* testable without real audio or a real key,
  and SHALL be verified this way rather than only by inspection).
- Handle a mid-stream server disconnect gracefully (no unhandled
  exception, no hung process) — verified with an actual test (e.g. the
  server closing the connection during an active session).
- Not require any change to `backend/` — this Contract is client-only.

---

# Out of Scope

This Contract SHALL NOT:

- Modify anything under `backend/` — if the client reveals a real defect
  in the Contract 0008 endpoint, report it (per P11) rather than silently
  patching the server from a client-focused Contract.
- Build any GUI, tray icon, hotkey, or `platform_shell` integration.
- Implement wake-word detection, push-to-talk, or any activation gating —
  the script streams continuously while running.
- Verify actual voice comprehension end-to-end — that requires the
  person's own microphone, speakers, and real `GEMINI_API_KEY`, and is
  explicitly their verification step, not this Contract's Acceptance
  Criteria.

---

# Acceptance Criteria

The implementation is accepted when:

- `live_audio_client.py` exists, uses the specified env-var convention,
  and its audio parameters match Contract 0008's expectations exactly
  (16-bit PCM mono, 16kHz send, matching `AUDIO_INPUT_MIME_TYPE`).
- Running the client against a backend with no `GEMINI_API_KEY`
  configured prints a clear message and exits cleanly — verified by an
  actual run, not code inspection.
- A simulated mid-stream server disconnect is handled without an
  unhandled exception or a hung process — verified by an actual test.
- The concurrent send/receive approach is documented with its rationale
  in Completion Notes.
- `pyaudio` is added to `requirements.txt`; `README.md` has clear run
  instructions.
- The Contract is annotated per DOCUMENT_STANDARD §3.1.

---

# Architecture Review

### Round 1 — 2026-07-23 — Verdict: Accepted
Reviewer: Architect

Checked against P13 twice: reusing `realtime_client.py`'s env var names
(not inventing new ones) and its synchronous-websockets style, both
because they are already proven in this codebase, not because they are
objectively the only valid choice. Checked against P9: scope stops at "a
script that streams audio and plays it back, with graceful error
handling" — no GUI, no activation logic, no `platform_shell` integration,
consistent with treating this as one more small, verifiable step rather
than reaching for the full end-state interface. Checked against P11: the
concurrent-thread-safety question for the sync websockets client is
named explicitly rather than assumed either way, since getting it wrong
silently (e.g. corrupted frames from unsynchronized concurrent writes)
would be a subtle, hard-to-diagnose defect exactly of the kind this
platform's process is meant to catch before it ships. No conflict with
`FOUNDATIONAL_WORLDVIEW.md`/`PRINCIPLES.md`. Accepted as drafted.

Noted for the record: this Contract's Acceptance Criteria are
deliberately narrower than what "Phase 4b-2 works" actually means in
practice — real voice comprehension can only be confirmed by the person,
locally, with real hardware. This Contract's bar is "the client is
correctly built and fails safely," not "the conversation worked," the
same division of labor used for every prior live-capability Contract.

---

# Future Evolution

- `platform_shell` (P17): the eventual real interface, likely replacing
  this console script's role rather than building on top of it directly.
- Phase 4b-1-bis (memory for live audio, if still pending): once
  available, this client would benefit without needing its own changes,
  since memory lives entirely on the backend side.
- Activation gating (wake-word or push-to-talk), if continuous streaming
  proves impractical in real use — not designed for speculatively now.

---

# Completion Notes

(To be completed after implementation.)

---

# Implementation Review

(To be completed after implementation.)

---

# Lessons Learned

(To be completed after implementation.)
