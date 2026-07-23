# IMPLEMENTATION_CONTRACT_0008

Status: Implemented

---

# Title

Backend Live Audio Endpoint: Gemini Live API session over WebSocket, tool
calling reused, no memory, no desktop client (Phase 4b-1)

---

# Purpose

Give the backend a real-time, bidirectional audio channel: a WebSocket
endpoint that streams microphone-shaped audio in, holds a genuine Gemini
**Live** API session (the mechanism Contract 0005 deliberately did not
use, reserved for exactly this purpose), executes tools through it via
the same mechanism already proven for text, and streams audio + a
transcript back out.

This Contract is backend plumbing only. Variant A was agreed with the
person before drafting: the backend holds the Live session; a desktop (or
any future) client only streams raw audio in and plays audio out — it
never talks to Gemini directly. This keeps the same shared-backend shape
already used for text (P17) and matches `jarvis_cesky`'s own ADR-016
direction.

---

# Intent

- Smallest real slice first (P9): one profile, one Live session per
  WebSocket connection, no memory persistence, no desktop client. Proves
  the plumbing — audio in, tool execution, audio+transcript out — before
  building the hardware-dependent half (Phase 4b-2) or wiring continuity
  (a likely Phase 4b-1-bis, mirroring how 4a → 4a-bis split memory out).
- Reuse, don't duplicate: `execute_tool` (real tool invocation via
  `action_loader`) and the current-time-context injection already exist
  in `gemini_chat_handler.py` (Contract 0005). Both are extracted into a
  shared module so this Contract's Live handler and the existing chat
  handler both call the same code, per P2/P13 — a Live-specific
  reimplementation of tool execution would be exactly the kind of
  duplicated-parallel-logic risk P13/P16 already warn about elsewhere in
  this platform.
- Genuine open API-shape questions are named, not guessed at (P11):
  exact current parameter names/types for enabling audio transcription
  and sending tool results back into a Live session are left for the
  Implementation Agent to verify against current `google-genai`
  documentation, the same posture Contract 0005 took toward its own
  modality question — except this time the answer is expected to exist
  and be usable (Live API's whole purpose is audio), not a dead end.
- This endpoint is separate from `RealtimeEventHub` (Contract 0002):
  that hub broadcasts discrete events (messages, status) to any number of
  subscribed clients; this Contract's endpoint is a dedicated,
  stateful, one-session-per-connection audio pipe. Conflating the two
  would force a broadcast-shaped abstraction onto a fundamentally
  different (bidirectional streaming, single-owner) concern.

---

# Current State

- `gemini_chat_handler.py` (Contract 0005/0006) has `execute_tool`,
  `_current_time_context`, and tool-declaration construction, all
  currently private to that module.
- `backend/services/realtime.py`'s `RealtimeEventHub` already defines
  `audio_mime_type`/`audio_base64` fields on `RealtimeEvent` and lists
  `"audio"` in `SUPPORTED_EVENT_TYPES` — infrastructure anticipated audio
  events but nothing currently produces or consumes them this way; this
  Contract's own endpoint is separate from this hub (see Intent), so
  these fields remain unused by this Contract specifically and are noted
  only to avoid confusion with what this Contract does add.
- `backend/realtime_client.py` (Contract 0002) is a generic event
  subscriber with no audio-specific send/receive methods yet — not reused
  by this Contract, which defines its own protocol (see Outputs); Phase
  4b-2 will build the actual desktop client.
- No Live API code exists anywhere in the transferred platform — Contract
  0005 explicitly avoided it. `jarvis_cesky`'s `main.py` (reference only)
  uses 16-bit PCM, 16kHz mono for microphone input, 24kHz for playback —
  confirmed matching Google's documented Live API audio format.

---

# Inputs

- `gemini_chat_handler.py`'s `execute_tool`, `_current_time_context`
  (extracted, not duplicated — see Outputs).
- `actions/tool_catalog.py`, `actions/action_loader.py`,
  `profiles/profile_loader.py` (existing, unmodified).
- `jarvis_cesky`'s `main.py` audio constants (`SEND_SAMPLE_RATE=16000`,
  `RECV_SAMPLE_RATE=24000`, `FORMAT=pyaudio.paInt16`) as reference for the
  wire format this endpoint expects from any client — not as code to
  transfer.

---

# Outputs

- `backend/services/gemini_common.py` (new): `execute_tool`,
  `_current_time_context` (renamed public if needed), and tool-declaration
  building, moved here from `gemini_chat_handler.py`. `gemini_chat_handler.py`
  updated to import from here instead — behavior unchanged, verified by
  Contract 0005/0006's existing tests still passing against the moved
  code.

  > Status: Done — `current_time_context` (renamed public),
  > `build_system_instruction`, `build_tools` (tool-declaration building),
  > and `execute_tool` (unchanged signature/return type: `types.Part`) all
  > moved here. Added `execute_tool_live` (returns `types.FunctionResponse`,
  > the Live-shaped equivalent) sharing the same private `_invoke_tool`
  > core with `execute_tool`, so tool resolution/invocation/error-handling
  > has exactly one implementation, not two. Contract 0005/0006's own
  > verification scenarios re-run against the refactored code — see
  > Completion Notes.
- `backend/services/gemini_live_audio_handler.py` (new):
  - Opens a Gemini Live session (`client.aio.live.connect(...)`) per
    WebSocket connection, using `profile.prompt` +
    `_current_time_context()` as system instruction and `profile.tools`
    for function declarations (same construction pattern as
    `gemini_common.py`'s shared helper, not a second implementation).
  - `response_modalities=["AUDIO"]`, with transcription enabled for both
    directions (output and input) so a readable transcript is available
    alongside the audio — Implementation Agent verifies the current,
    correct `google-genai` config field names/types for this against
    current documentation and reports what was found in Completion Notes.
  - Forwards inbound binary audio frames from the WebSocket directly into
    the Live session (verify current SDK method for sending realtime
    audio input).
  - On a tool-call event from the Live session: executes it via
    `gemini_common.execute_tool`, sends the result back into the Live
    session (verify current SDK's expected shape for a Live function
    response — likely different from `generate_content`'s
    `types.Part.from_function_response`, confirm rather than assume).
  - Forwards outbound audio chunks and transcript text from the Live
    session back to the WebSocket client as they arrive (streaming, not
    buffered-then-sent).

  > Status: Done — `GeminiLiveAudioHandler.handle_connection` opens one
  > `client.aio.live.connect(...)` session per WebSocket connection and
  > runs two concurrent tasks (`_forward_client_audio`,
  > `_forward_live_events`) via `asyncio.wait(..., return_when=FIRST_COMPLETED)`,
  > cancelling whichever is still pending when the other ends, so neither
  > task can outlive the connection or the Live session. Verified with a
  > fully scripted test (fake `AsyncSession`, no real network) — see
  > Completion Notes for the exact API shapes used and their source.
- `backend/api.py`: new WebSocket route (e.g. `/api/v1/live/audio`),
  independent of `RealtimeEventHub`'s existing route. Requires
  `GEMINI_API_KEY` configured; if absent, the endpoint SHALL reject the
  connection with a clear reason (mirroring `AgentRuntime`'s
  `runtime_unavailable` posture, not a bare connection drop).

  > Status: Done — route is `/api/v1/live/audio` (matches the Contract's
  > own suggested name); accepts then sends
  > `{"type": "error", "status": "runtime_unavailable", "detail": ...}`
  > followed by a close (code 1008) when no handler is configured, verified
  > with an actual connection attempt.
- `projects/voice_agent/README.md` updated: new capability noted;
  limitations state plainly no memory/continuity yet, no desktop client
  yet, single hardcoded profile.

  > Status: Done.

---

# Functional Requirements

The implementation SHALL:

- Extract the shared logic into `gemini_common.py` exactly as scoped, and
  confirm `gemini_chat_handler.py`'s existing behavior is unchanged after
  the move (re-run Contract 0005/0006's existing verification approach
  against the refactored code, not just visually confirm the diff).
- Implement `gemini_live_audio_handler.py` exactly as scoped, using
  `gemini_common` for tool execution and time context — no parallel
  reimplementation.
- Verify, and document in Completion Notes, the exact current
  `google-genai` API shapes used for: enabling input+output audio
  transcription in `LiveConnectConfig`; sending realtime audio input;
  sending a tool's result back into an open Live session. Cite the
  documentation consulted, consistent with how Contract 0005's Round 1
  research was expected to (even though that Round ultimately reported a
  blocker rather than an answer — this Contract expects a working answer
  and still wants it verified, not assumed from training data).
- Reject a connection attempt cleanly with a clear message when
  `GEMINI_API_KEY` is not configured, verified with an actual connection
  attempt in that state.
- Handle a tool-execution failure inside a Live session the same way
  `gemini_common.execute_tool` already does for text (descriptive error
  content back to the model, not a dropped connection) — verified with an
  actual forced-failure test, not by inspection alone.

> Status: Done — all five requirements verified with actual test calls
> against `google-genai` 2.12.1 (installed, matching `requirements.txt`'s
> pin): (1) extraction verified by re-running Contract 0005/0006's own
> scenarios (tool-list match, all-five-tools-resolve, forced failure,
> full multi-turn round trip) against the refactored `gemini_common.py` —
> all pass identically; (2) `gemini_live_audio_handler.py` uses
> `build_system_instruction`/`build_tools`/`execute_tool_live` from
> `gemini_common`, no parallel logic; (3) exact API shapes verified by
> direct introspection of the installed SDK (not docs alone) — see
> Completion Notes; (4) connection rejection verified with an actual
> `TestClient.websocket_connect` attempt against `gemini_api_key=""`; (5) a
> forced tool failure (wrong keyword argument against the real
> `get_weather_summary`) inside a full scripted WebSocket flow produced a
> `FunctionResponse` with `error` content and `id` preserved, sent via
> `send_tool_response`, connection stayed open and completed normally.

---

# Out of Scope

This Contract SHALL NOT:

- Persist anything to `MemoryRepository` or otherwise implement
  cross-session continuity for live audio (deferred — likely
  Phase 4b-1-bis, mirroring the 4a → 4a-bis split).
- Build any desktop/client-side audio capture or playback code (Phase
  4b-2). This Contract's endpoint is verified with a scripted test client
  sending raw bytes over the WebSocket protocol, not a real microphone.
- Modify `RealtimeEventHub`, `realtime_client.py`, `AgentRuntime`, or any
  Contract 0002–0007 deliverable beyond the `gemini_common.py` extraction.
- Implement more than one profile or any profile-switching logic.
- Require or assume a real `GEMINI_API_KEY` or real audio content
  (meaningful speech) during the Architect's own review — full voice
  comprehension verification is, as with every prior live-capability
  Contract, the person's job locally, not verifiable from this review
  environment. Protocol-level and tool-execution-reuse verification is
  this Contract's bar for Architect review.

---

# Acceptance Criteria

The implementation is accepted when:

- `gemini_chat_handler.py`'s prior behavior (Contract 0005/0006's own
  verification scenarios) still passes after the `gemini_common.py`
  extraction.
- A scripted WebSocket test client can open a connection to the new
  endpoint, and the connection is cleanly rejected with a clear reason
  when `GEMINI_API_KEY` is unset — verified by an actual connection
  attempt.
- `gemini_live_audio_handler.py` correctly resolves and would invoke each
  of the five real tools via `gemini_common.execute_tool`, and a forced
  tool failure produces descriptive error content rather than dropping
  the connection or crashing — verified with actual test calls.
- The exact current API shapes for transcription config, realtime audio
  input, and Live function-response are documented with their source in
  Completion Notes.
- No file naming or directory naming violates the Tr5 naming convention.
- The Contract is annotated per DOCUMENT_STANDARD §3.1.

> Status: Done — every criterion verified with actual test calls (see
> Functional Requirements annotation for the concrete evidence). New files
> (`gemini_common.py`, `gemini_live_audio_handler.py`) are
> `lowercase_with_underscores`, ASCII, no hyphens — compliant. This
> annotation pass fulfills the last criterion.

---

# Architecture Review

### Round 1 — 2026-07-23 — Verdict: Accepted
Reviewer: Architect

Checked against the agreed Variant A (backend holds the Live session) —
this Contract implements exactly that, with no client-side Gemini access
introduced anywhere. Checked against P9: scope deliberately excludes
memory and the desktop client, mirroring the 4a → 4a-bis split that
worked well previously — a large capability (real-time voice) is being
built in the same small-step discipline as everything before it, not as
an exception. Checked against P2/P13: the shared-module extraction
(`gemini_common.py`) is called out explicitly to prevent tool-execution
logic from silently forking into two maintained copies, which would be
exactly the kind of risk P16 named in a different context. Checked
against P11: genuinely version-sensitive Live API details (transcription
config, function-response shape) are named as open questions for the
Implementation Agent to resolve against current documentation, not
asserted from this Architect's training data, which may be stale for a
fast-moving API surface. No conflict with `FOUNDATIONAL_WORLDVIEW.md` or
`PRINCIPLES.md`. Accepted as drafted.

---

# Future Evolution

- Phase 4b-1-bis: memory/continuity for live audio sessions, once this
  core is proven — likely reusing `MemoryRepository` the same way
  Contract 0006 did for text, with the open design question of whether a
  live session should load prior short-term turns as initial context.
- Phase 4b-2: real desktop audio client (`pyaudio` capture/playback)
  talking to this endpoint — the person's own hardware-dependent
  verification, same division of labor as every prior live-tested
  Contract.
- Eventually, `platform_shell` connects to this same endpoint for its
  voice-enabled surface, per P17.

---

# Completion Notes

Implemented as scoped. `gemini_common.py` created with `current_time_context`,
`build_system_instruction`, `build_tools`, `execute_tool`, `execute_tool_live`
(plus a private `_invoke_tool` shared core). `gemini_chat_handler.py` now
imports from it — `build_generation_config` reduced to two lines calling
the shared helpers. `gemini_live_audio_handler.py` created with
`build_live_config`, `_forward_client_audio`, `_forward_live_events`,
`GeminiLiveAudioHandler`, `build_handler`. `backend/api.py` gained the
`/live/audio` WebSocket route; `backend/app.py` builds and threads the
live audio handler alongside the existing chat handler, gated on the same
`settings.gemini_api_key`.

**Exact `google-genai` API shapes (source: direct introspection of the
installed SDK, version 2.12.1, matching `requirements.txt`'s pin — not
documentation summaries, to avoid the kind of stale-docs mismatch that
could recur on a fast-moving preview API):**

- `client.aio.live.connect(*, model, config)` returns an async context
  manager yielding an `AsyncSession` — used as
  `async with client.aio.live.connect(model=..., config=...) as session:`.
- Transcription: `types.LiveConnectConfig.input_audio_transcription` and
  `.output_audio_transcription`, both `types.AudioTranscriptionConfig | None`.
  An empty `types.AudioTranscriptionConfig()` (all fields — `language_codes`,
  `language_auto`, `language_hints`, `adaptation_phrases` — optional)
  enables transcription with defaults; confirmed by constructing one and
  inspecting `LiveConnectConfig`'s resolved fields directly.
- Realtime audio input: `AsyncSession.send_realtime_input(*, audio:
  types.Blob | types.BlobDict | None, ...)` — `types.Blob(data: bytes,
  mime_type: str)`. Used here as
  `session.send_realtime_input(audio=types.Blob(data=chunk,
  mime_type="audio/pcm;rate=16000"))` per message.
- Tool result back into a Live session: `AsyncSession.send_tool_response(*,
  function_responses: types.FunctionResponse | Sequence[...])` — **not**
  `generate_content`'s `types.Part.from_function_response`, confirmed
  different as the Contract predicted. Critically, Live's `FunctionCall`
  and `FunctionResponse` both carry an `id` field that `generate_content`'s
  do not; the response must set `id=function_call.id` (not just `name`) or
  the model has no way to match the response to its call. This is the one
  genuinely new detail this Contract's research surfaced beyond what was
  already anticipated.
- Receiving: `AsyncSession.receive()` yields
  `AsyncIterator[types.LiveServerMessage]`. Fields used:
  `message.tool_call.function_calls` (`list[types.FunctionCall] | None`);
  `message.server_content.model_turn` (`types.Content | None`, whose parts
  carry `part.inline_data.data: bytes` for audio chunks);
  `message.server_content.input_transcription`/`.output_transcription`
  (`types.Transcription | None`, with a `.text` field);
  `message.server_content.turn_complete` (`bool`).

Verification approach: no real `GEMINI_API_KEY` or real audio was used or
required, per Out of Scope. The full connection flow (client audio in →
tool call → forced failure → error response sent back with `id` preserved
→ audio/transcript/turn_complete out) was verified with a fully scripted
fake `AsyncSession` (a plain Python class with `AsyncMock` methods and an
async-generator `receive()`) monkeypatched onto `AsyncLive.connect`, driven
through a real `TestClient.websocket_connect` — exercising the actual
WebSocket route, the actual `GeminiLiveAudioHandler.handle_connection`
task orchestration, and the actual `gemini_common.execute_tool_live`, with
only the Gemini network boundary itself replaced.

---

# Implementation Review

### Round 1 — 2026-07-23 — Verdict: Accepted
Reviewer: Architect

Verified independently, not by trusting Completion Notes' SDK-shape
claims alone: (1) regression — re-ran Contract 0006's multi-turn
continuity test against the refactored `gemini_chat_handler.py`, passed
identically, confirming the `gemini_common.py` extraction changed nothing
observable; (2) confirmed a connection to `/api/v1/live/audio` is cleanly
rejected with a `runtime_unavailable`-shaped JSON error, not a bare drop,
when `GEMINI_API_KEY` is unset — via a real `TestClient.websocket_connect`
call, not inspection; (3) wrote an independent (not the Agent's) fully
scripted fake Live `AsyncSession` and fake WebSocket, drove
`GeminiLiveAudioHandler.handle_connection` directly with a deliberately
unknown tool name, and confirmed: the outgoing `FunctionResponse.id`
matches the incoming `FunctionCall.id` exactly (the specific, easy-to-miss
detail Completion Notes highlighted as the one genuinely new finding);
the error content is descriptive, not a raised exception; audio bytes,
transcript, and `turn_complete` all forward correctly to the client in
order. This independently corroborates the Agent's central technical
claim rather than merely accepting it. The SDK-shape findings themselves
(exact parameter names, the `id`-matching requirement) were obtained by
introspecting the installed package directly rather than summarizing
documentation — a sound choice for a preview-stage API, and the resulting
claims held up against this Architect's own from-scratch test. Status
changed to `Implemented`.

Standing limitation, unchanged from every prior live-capability Contract:
no real `GEMINI_API_KEY` or real audio was used in this review — full
voice comprehension against the real Live API is the person's own
verification once Phase 4b-2 (desktop client) exists to actually produce
real microphone audio; this Contract's endpoint has no way to be
exercised end-to-end without one.

---

# Lessons Learned

- Live API's `FunctionCall`/`FunctionResponse` carrying an `id` field that
  `generate_content`'s equivalents don't have is the kind of detail that's
  easy to miss by pattern-matching against the already-proven
  `generate_content` tool-calling code — direct SDK introspection (`dir()`,
  `model_fields`) caught it before it became a runtime bug, where the
  Contract's own instruction to "confirm rather than assume" the
  function-response shape paid off concretely.
- Two concurrent tasks bridging a WebSocket and an external async stream
  need an explicit joint-termination strategy (`asyncio.wait(...,
  return_when=FIRST_COMPLETED)` + cancel the loser) — without it, a closed
  client connection or an ended Live session can leave the other task
  running forever. Worth remembering for any future bidirectional-stream
  endpoint on this backend.
- A fully scripted fake session (plain class + `AsyncMock` + async
  generator) driven through a real `TestClient.websocket_connect` exercises
  the actual route, task orchestration, and tool-execution code with only
  the external network boundary replaced — meaningfully stronger evidence
  than isolated unit tests of each function, and still requires no real API
  key or real audio, consistent with every prior live-capability Contract's
  division of labor.
