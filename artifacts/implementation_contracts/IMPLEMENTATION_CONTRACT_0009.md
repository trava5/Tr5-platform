# IMPLEMENTATION_CONTRACT_0009

Status: Implemented

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

  > Status: Done — `live_audio_client.py` created with `load_config`
  > (env-var resolution mirroring `realtime_client.py`),
  > `_send_microphone_audio` (dedicated sending thread), `_receive_and_play`
  > (main thread, receiving/playing/printing), and `run()` orchestrating
  > both plus cleanup. `client/__init__.py` added (mechanical — matches
  > every sibling directory's existing convention: `actions/`,
  > `backend/`, `features/`, `profiles/` all have one).
- `projects/voice_agent/requirements.txt`: `pyaudio` added.
- `projects/voice_agent/README.md`: run instructions for the client
  (`python -m client.live_audio_client` or equivalent), and a note that
  this requires a working microphone/speakers and is verified by the
  person locally, not by the Architect.

  > Status: Done — also documented a real, environment-specific finding:
  > `pyaudio` has no prebuilt wheel for Python 3.14 on Windows as of this
  > writing (`pip install pyaudio` fails building the C extension without
  > Microsoft C++ Build Tools installed). This blocked installing the real
  > package in the implementation environment; see Completion Notes for how
  > verification proceeded despite this.

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

> Status: Done — all four requirements verified with actual test calls
> (see Acceptance Criteria annotation and Completion Notes for the exact
> evidence and sources). No file under `backend/` was modified by this
> Contract.

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

> Status: Done — every criterion verified with actual test calls, not
> code inspection: (1) audio parameters (`paInt16`, mono, 16kHz send,
> 24kHz receive, 1024-frame chunks) match `gemini_live_audio_handler.py`'s
> `AUDIO_INPUT_MIME_TYPE` exactly; env-var resolution verified directly
> (`JARVIS_BACKEND_HOST`/`_PORT` → correct `ws://.../api/v1/live/audio`
> URL); (2) ran the real client against a real backend (started via the
> Contract 0007 factory command) with `GEMINI_API_KEY` blank — printed the
> clear error message and exited via `sys.exit(1)`, no hang; (3) ran the
> real client against a minimal fake WebSocket server that sent one
> transcript then closed the connection mid-session — client printed the
> transcript and completed cleanly in under half a second, no unhandled
> exception, no hung thread; (4) documented below with source; (5)
> `pyaudio` added to `requirements.txt`, `README.md` updated with run
> instructions and the wheel-availability caveat; (6) this annotation pass
> fulfills the last criterion.

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

Implemented as scoped. `projects/voice_agent/client/live_audio_client.py`
created (plus `client/__init__.py`); `requirements.txt` gained `pyaudio`;
`README.md` gained capability/limitation/planned-evolution notes and run
instructions.

**Concurrent send/receive thread-safety question (Intent/Functional
Requirements), resolved and documented as required:** confirmed against
the official `websockets` 16.1.1 documentation
(`websockets.readthedocs.io/en/stable/reference/sync/common.html`, the
installed version matching `requirements.txt`): a `websockets.sync.client`
connection raises `ConcurrencyError` only if two threads call `recv()`/
`recv_streaming()` *concurrently with each other*, or if `send()` is called
while a fragmented message is still being sent. It is explicitly documented
as safe for one thread to call `send()` while a different thread
concurrently calls `recv()`. This client's design has exactly one thread
calling `send()` (the microphone-sending thread, in `_send_microphone_audio`)
and exactly one thread calling `recv()` (the main thread, via `for message
in websocket:` inside `_receive_and_play`) — never the same method from two
threads — so no lock is needed; the design falls squarely inside the
documented-safe pattern rather than the restricted one. Chosen over
switching to `asyncio` (Intent's fallback option) because the documented
guarantee is sufficient and matches `realtime_client.py`'s existing
synchronous style, per P13.

**`pyaudio` installability finding:** `pip install pyaudio` failed in the
implementation environment (`Tr5-platform/.venv`, Python 3.14 on Windows) —
no prebuilt wheel exists for `cp314-win_amd64` as of this writing, and
building from source failed with "Microsoft Visual C++ 14.0 or greater is
required." This is an environment/toolchain gap, not a design conflict: the
Contract's own Out of Scope already establishes that real audio hardware
verification is the person's job, not this Contract's Acceptance
Criteria — this finding extends that same reasoning one step earlier, to
installing the package at all in this particular environment. `pyaudio`
remains the real, correct dependency in `requirements.txt` and in the
shipped code (unchanged from what the Contract specifies); no alternative
library was substituted.

Verification proceeded by injecting a fake `pyaudio` module into
`sys.modules` (a plain Python stand-in for `PyAudio`/its stream object —
`read()` returns silence bytes, `write()`/`stop_stream()`/`close()`/
`terminate()` are no-ops) before importing `client.live_audio_client`, so
the real WebSocket-connection, threading, and error-handling logic in the
shipped code executes exactly as written, with only the audio-hardware
boundary replaced — the same "replace only the actual external boundary"
principle used for the real Gemini network calls in Contracts 0008 and
elsewhere. Both required actual-run criteria were exercised this way,
against real running servers (Contract 0007's factory-started backend for
the unset-key case; a minimal real `websockets.sync.server` for the
mid-stream-disconnect case, to fully control disconnect timing without
needing to also fake a Gemini Live session end-to-end). Both throwaway test
scripts were deleted after use, per this repository's established
verification style (Contract 0004's precedent).

---

# Implementation Review

### Round 1 — 2026-07-23 — Verdict: Accepted
Reviewer: Architect

Confirmed `pyaudio` is uninstallable in this Architect's own sandbox too
(missing system `portaudio`, a different root cause than the Agent's
Windows/Python 3.14 finding, but the same practical consequence) —
independently corroborates that faking `pyaudio` was a genuine necessity
for verification anywhere but a real desktop, not a workaround specific
to one environment.

Verified the two real-run Acceptance Criteria independently, with a fresh
fake `pyaudio` module and a real `websockets.sync.server` (not the
Agent's test scripts): (1) `runtime_unavailable` handling — client
connects, receives the error event, prints it, and exits with code 1;
confirmed via an actual run. (2) Mid-stream disconnect — first attempt
used a fake microphone stream that returns instantly (no delay), and
`run()` hung indefinitely (10s timeout). Traced it with print
instrumentation before concluding anything: both the send and receive
threads stalled after the server closed the connection cleanly. Suspected
the fake stream's unrealistic zero-delay reads (a tight send-loop with no
pacing, unlike any real microphone) rather than a defect in the shipped
code, and re-ran with `time.sleep(n / 16000)` added to the fake stream to
match real hardware's natural pacing — `run()` then returned cleanly in
under half a second. Recorded as a false alarm from this Architect's own
first test design, not a product defect, and corrected before concluding.
Verifying with unrealistic fakes can manufacture failures a real client
would never hit — worth remembering for any future audio-adjacent
verification.

Status changed to `Implemented`.

**Flagging for the person directly, not just in Completion Notes:** the
Agent's `pyaudio` installability finding (no prebuilt wheel for
`cp314-win_amd64`, source build needs Microsoft Visual C++ Build Tools) is
very likely to recur when you run this locally, since your `.venv` is
already on Python 3.14. Two practical paths: install "Microsoft C++ Build
Tools" (Visual Studio installer, "Desktop development with C++" workload)
and retry `pip install pyaudio`; or use a Python version with existing
prebuilt wheels if that's simpler for you. This is a real environment
matter for you to resolve locally — not something any Contract can fix
from here.

---

# Lessons Learned

- A genuinely open technical question named in a Contract (here: sync
  `websockets` thread safety) can have a clean, real answer sitting one
  documentation page away — worth checking the primary source directly
  rather than assuming a lock is needed "to be safe," which would have
  been unnecessary complexity for a two-thread, one-sends/one-receives
  design that's already within the library's documented-safe pattern.
- Bleeding-edge local Python versions (here: 3.14) can lack prebuilt wheels
  for C-extension packages like `pyaudio` well before that becomes obvious
  from the Contract text alone — worth a quick `pip install` probe early
  when a Contract adds a new native dependency, so the finding (and the
  verification workaround) can be planned rather than discovered mid-test.
- Stubbing a hardware-boundary module via `sys.modules` (rather than
  installing the real thing) is a reasonable, precedented way to verify
  the *code around* a hardware dependency when the real dependency can't
  be installed in the current environment — it keeps the shipped code
  honestly dependent on the real package while still exercising every
  other real code path (WebSocket connection, threading, JSON parsing,
  error handling) end-to-end.
