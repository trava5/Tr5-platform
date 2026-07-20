# IMPLEMENTATION_CONTRACT_0005

Status: Accepted

---

# Title

Live Agent Runtime Core: connect Gemini Live to `AgentRuntime`, text-only,
no memory, no audio (Phase 4a)

---

# Purpose

Give `projects/voice_agent/backend/services/agent_runtime.py`'s existing
`AgentRuntime` a real handler, so `POST /api/v1/messages` (or whichever
endpoint calls `handle_message`) produces genuine Gemini-driven responses
— including real tool execution — instead of today's
`runtime_unavailable` status.

This is new work, informed by (not copied from) `jarvis_cesky`'s `main.py`,
per this transfer's original Purpose statement (Contract 0002): main.py's
`JarvisLive` class is a 1744-line monolith; this Contract extracts only the
Gemini Live connection and tool-calling logic, rebuilt against the
platform already in place — `profile_loader`, `tool_catalog`,
`action_loader`, and `AgentRuntime`'s existing, already-reviewed handler
abstraction.

---

# Intent

- Validate the smallest real case first (P9): text in, text out, one
  profile, no persisted conversational memory across messages, no audio.
  Each incoming message opens a fresh Gemini Live session, completes one
  turn (including any tool-call round trips within that turn), and closes.
  Multi-turn session continuity is a deliberate later step, not attempted
  here — it introduces session-lifecycle questions (when to keep a session
  open, how long, mapped to which conversation) that deserve their own
  validation once this smaller piece is proven.
- Single source of truth for tools (P13 improvement over the source):
  Gemini's `tools` config is built directly from the resolved
  `Profile.tools` (already in Gemini-compatible `name`/`description`/
  `parameters` shape via `tool_catalog.py`) — not a second, separately
  maintained declarations list like `main.py`'s `TOOL_DECLARATIONS`, which
  this Contract does not transfer.
- Preserve one genuinely good defensive pattern from `main.py`: a tool
  execution failure becomes a descriptive result returned to the model
  (so the model can inform the user), not an unhandled exception that
  kills the session.
- `AgentRuntime` itself (conversation persistence, realtime publishing,
  connected/disconnected state, error/status handling) already exists and
  was already reviewed in Contract 0002 — this Contract does not modify
  it, only supplies the `LiveMessageHandler` it already knows how to
  accept via `.connect(handler)`.

---

# Current State

- `backend/services/agent_runtime.py`'s `AgentRuntime` exists, is wired
  into `backend/app.py` (`app.state.agent_runtime`), and is called from
  `backend/api.py`'s message endpoint — but nothing ever calls
  `.connect(...)`, so every message currently returns status
  `runtime_unavailable`.
- `profiles/profile_loader.py`, `actions/tool_catalog.py`,
  `actions/action_loader.py` exist and are verified working (Contracts
  0003, 0004) but nothing calls them yet.
- `jarvis_cesky`'s `main.py` (reference only, not transferred) uses
  `google-genai`'s `Client().aio.live.connect(model=LIVE_MODEL,
  config=types.LiveConnectConfig(...))` with
  `model = "models/gemini-2.5-flash-native-audio-latest"`, and builds
  `tools` from a separately hardcoded `TOOL_DECLARATIONS` list — the
  duplication this Contract deliberately avoids.
- No `GEMINI_API_KEY` (or equivalent) exists yet in
  `projects/voice_agent/.env.example`.

---

# Inputs

- `projects/voice_agent/profiles/profile_loader.py`,
  `actions/tool_catalog.py`, `actions/action_loader.py` (existing,
  unmodified).
- `backend/services/agent_runtime.py`'s `AgentRuntime`,
  `LiveMessageHandler` type, `MessageRequest`/`MessageResponse` schemas
  (existing, unmodified).
- `jarvis_cesky`'s `main.py`, `_build_config`/`_execute_tool` methods, as
  design reference only (not copied).

---

# Outputs

- A new module, `backend/services/gemini_live_handler.py`, implementing:
  - `build_live_config(profile: Profile) -> types.LiveConnectConfig` —
    `system_instruction = profile.prompt`; `tools` built from
    `profile.tools` values; `response_modalities = ["TEXT"]` (confirm
    against current Gemini Live API documentation whether the audio-native
    model supports text-only responses cleanly, or whether a different
    Live-capable model should be used for this text-only phase — this is
    a genuine open question this Contract does not presume the answer to;
    see Functional Requirements).

    > Status: Blocked — neither anticipated resolution holds against
    > current (2026-07-20) documentation; see Completion Notes.
  - `execute_tool(function_call, profile: Profile) -> types.FunctionResponse`
    — resolves `profile.tools[fc.name]`, calls
    `action_loader.load_action_function(module, function)`, invokes it
    with `fc.args`, catches exceptions and returns a descriptive error
    result rather than raising.
  - `async def handle_message(request: MessageRequest, profile: Profile) ->
    str` — opens one Live session per call, sends `request.text`,
    processes any `tool_call` events via `execute_tool`, accumulates and
    returns the model's final text output for that turn.
  - A `GeminiLiveHandler` (or equivalent thin adapter) matching the
    `LiveMessageHandler` signature `AgentRuntime.connect()` already
    expects, with `profile` bound at construction time (loaded once via
    `profile_loader.load_profile("000_base", ...)`).
- `backend/app.py` updated: at startup, if `GEMINI_API_KEY` is set and
  non-empty, construct the handler and call
  `agent_runtime.connect(handler, detail=...)`. If unset, leave the
  runtime exactly as today (`runtime_unavailable`) — no behavior change
  for anyone not using this feature yet.
- `projects/voice_agent/.env.example` extended with `GEMINI_API_KEY=""`
  and `GEMINI_LIVE_MODEL` (default matching `jarvis_cesky`'s
  `models/gemini-2.5-flash-native-audio-latest`, overridable — do not
  hardcode without an escape hatch, since the exact right model for
  text-only Live sessions is the open question noted above).
- `google-genai` added to `requirements.txt` (confirm the exact package
  name and minimum version against current PyPI/Google documentation
  rather than assuming from `jarvis_cesky`'s own `requirements.txt`, since
  this Contract's model-choice question may affect the required SDK
  version).
- `README.md` updated: "Current capabilities" gains real Gemini-backed
  responses (text-only, single-turn, one profile); "Current limitations"
  states plainly: no memory across messages, no audio, no multi-turn
  session continuity, single profile only.

---

# Functional Requirements

The implementation SHALL:

- Implement `gemini_live_handler.py` exactly as scoped in Outputs.
- Resolve the text-only response question explicitly rather than guessing:
  consult current Google Gemini Live API documentation for whether
  `models/gemini-2.5-flash-native-audio-latest` supports
  `response_modalities=["TEXT"]`, or whether a different model is
  appropriate for a text-only Live session. Document the finding and the
  chosen model in Completion Notes. If genuinely ambiguous or blocked
  without a real API key to test against, report this explicitly (per
  P11) rather than shipping an unverified guess.

  > Status: Blocked — documentation was consulted (no API key needed for
  > this part); the finding is not an ambiguity resolvable by picking a
  > model, but a conflict with this Contract's own Out of Scope clause.
  > See Completion Notes; sent back to Architect per user decision
  > (2026-07-20) rather than resolved by Implementation Agent assumption.
- Load the `000_base` profile once at handler construction, not per
  message.
- Wire `agent_runtime.connect(...)` conditionally on `GEMINI_API_KEY`
  being set, at backend startup, without altering `AgentRuntime`'s own
  code.
- Ensure a tool execution exception is caught inside `execute_tool` and
  returned as a `FunctionResponse` describing the failure — verified with
  an actual test call using a tool that deliberately raises (e.g. by
  monkeypatching or a temporary broken profile, mirroring the testing
  approach used in Contract 0004), not just by code inspection.
- Ensure `build_live_config`'s `tools` list, when inspected, matches
  `profile.tools` exactly (same five tools, same names) — no
  hand-maintained duplicate list.

---

# Out of Scope

This Contract SHALL NOT:

- Implement audio input or output (Phase 4b).
- Implement memory persistence or read/write against
  `PostgresMemoryRepository`/`MemoryRepository` (explicitly deferred, per
  the earlier agreed "smallest case first" decision — the infrastructure
  already exists in `backend/services/` from Contract 0002, but is not
  wired into this handler).
- Implement multi-turn session continuity across separate
  `handle_message` calls within one conversation.
- Modify `AgentRuntime`, `MessageRequest`/`MessageResponse`, or any
  Contract 0002/0003/0004 deliverable.
- Enable or test `features/002_telegram_bridge` end-to-end — it already
  talks to the same backend endpoint this Contract brings to life, so it
  may start working as a side effect, but verifying that requires a real
  Telegram bot token and is not this Contract's job to set up or claim.
- Require or assume network access to any real Gemini API key during
  automated verification — the Architect does not have one available in
  this review environment either (see Architecture Review).

---

# Acceptance Criteria

The implementation is accepted when:

- `build_live_config(profile)` produces a config whose `tools` exactly
  matches `profile.tools`'s five entries, verified by an actual call, not
  by inspection alone.
- `execute_tool` successfully resolves and would correctly invoke each of
  the five real tools (verified via `action_loader` resolution, consistent
  with how Contract 0004 verified `profile_loader` without needing live
  external services where the tool itself needs one, e.g. weather).
- A simulated tool failure is caught and produces a `FunctionResponse`
  with descriptive error content, not an unhandled exception — verified
  with an actual test call.
- With `GEMINI_API_KEY` unset, backend startup behavior is unchanged from
  today (`runtime_unavailable`) — verified by running the existing
  Contract 0002 smoke test again and confirming identical output.
- The chosen Live model and text-only-response approach is documented with
  its rationale in Completion Notes, explicitly flagged if it could not be
  verified end-to-end against a real API key.
- The Contract is annotated per DOCUMENT_STANDARD §3.1.

---

# Architecture Review

### Round 1 — 2026-07-14 — Verdict: Accepted
Reviewer: Architect

Checked against P9: scope is deliberately the smallest slice that makes
`AgentRuntime` do something real — one profile, one turn, text only, no
persisted memory — rather than attempting Phase 4 as one large Contract.
Checked against P13: tool declarations are derived from the already-proven
`tool_catalog`, avoiding the exact duplication risk `main.py` itself
carries (two parallel lists that can drift). Checked against P2: memory
wiring is deferred even though the Postgres infrastructure already exists,
per the explicit decision made before drafting this Contract, not because
the work is hard but because validating the smaller case first is the
stated priority. One genuine open technical question — whether the
audio-native Live model cleanly supports text-only responses — is not
resolved here by assumption; the Contract requires the Implementation
Agent to verify it against current documentation and report findings,
consistent with P11 (report gaps, don't guess). Noted limitation for this
review itself: this Architect has no live Gemini API key in this
environment, so acceptance verification here will be structural
(imports resolve, config shape is correct, error handling works under
simulation) rather than a live end-to-end call — full live verification is
the Architect-with-real-key's job outside this chat, and is called out
explicitly rather than silently assumed complete. Accepted as drafted.

---

# Future Evolution

- Phase 4a-bis: wire `PostgresMemoryRepository`/`MemoryRepository` into
  the handler once this core is proven.
- Phase 4b: audio input/output.
- Phase 4c: enable and verify `features/002_telegram_bridge` end-to-end.
- Multi-turn session continuity, once a real need (not a guess) shows
  single-turn-per-message is insufficient.
- Phase 4d / `platform_shell`: connects to this same endpoint, per P17.

---

# Completion Notes

**Implementation not started.** Research into the Contract's own flagged
open question (text-only response modality) surfaced a conflict between
two of this Contract's clauses, not a simple documentation lookup. Sent
back to the Architect per an explicit user decision on 2026-07-20 rather
than resolved by assumption, per this repository's Hard Rules.

Finding, sourced against current (2026-07-20) documentation:

- Every Gemini Live API model currently offered
  (`gemini-2.5-flash-native-audio-preview-12-2025`,
  `gemini-3.1-flash-live-preview`) is native-audio-only. Google's own Live
  API capabilities guide states these models "only support `AUDIO`
  response modality" and that text must be obtained via the output audio
  transcription feature, not via `response_modalities=["TEXT"]` directly.
- Forcing `response_modalities=["TEXT"]` on a native-audio model is a
  reported, unresolved failure, not a supported path
  (`googleapis/python-genai` issue #1780; `livekit/agents` issue #4423).
- The one model that did cleanly support `response_modalities=["TEXT"]`,
  the half-cascade `gemini-live-2.5-flash-preview`, has been deprecated
  and retired — confirmed via the Google AI Developers forum thread
  "Bring back the Half Cascade gemini-live-2.5-flash-preview model"
  (accessed 2026-07-20), where Google support's stated current guidance
  is: use `AUDIO` output modality with output transcription enabled, and
  read the transcript text instead of the audio.
- Consequence: neither outcome this Contract's Outputs section
  anticipated ("confirm... whether the audio-native model supports
  text-only responses cleanly, or whether a different Live-capable model
  should be used") is available. The only working path to get any text
  out of a Live session today requires requesting `AUDIO` response
  modality — which sits in direct tension with this Contract's own Out of
  Scope clause ("SHALL NOT: Implement audio input or output (Phase 4b)"),
  even though no audio would ever reach a user (it would be requested,
  received, and discarded, keeping only the transcript).

This is an architectural fork, not an implementation detail — it affects
cost (audio-generation billing for what is meant to be a text-only phase),
wire-format complexity (receiving binary audio frames even if unused), and
whether "Live API" is still the right vehicle for a *text-only* Phase 4a at
all (a plain, non-Live `generateContent`/chat call would avoid all of this
but would deviate from the Contract's Title/Purpose). Presented to the
user as four options (audio+transcription workaround / ship TEXT anyway
flagged-unverified / switch to non-Live API / pause for Architect
revision); the user chose to pause for Architect revision. No code was
written under this Contract; no files listed in Outputs were created or
modified.

---

# Implementation Review

(To be completed after implementation.)

---

# Lessons Learned

(To be completed after implementation.)
