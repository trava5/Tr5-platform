# IMPLEMENTATION_CONTRACT_0005

Status: Accepted

---

# Title

Text Agent Runtime Core: connect Gemini (`generate_content`, not Live
API) to `AgentRuntime` (Phase 4a)

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
Gemini connection and tool-calling logic, rebuilt against the platform
already in place — `profile_loader`, `tool_catalog`, `action_loader`, and
`AgentRuntime`'s existing, already-reviewed handler abstraction.

Revision 1.1 (see Architecture Review Round 2 and Revision Notes): this
Contract no longer uses the Gemini **Live** API. Round 1's implementation
attempt found, and the Architect independently confirmed, that every
currently offered Live model is native-audio-only — there is no supported
way to get a text-only response from a Live session today. Live API's
real value is low-latency real-time voice streaming, which is exactly
Phase 4b's concern, not this text-only phase's. This Contract now uses
plain `generate_content` with function calling instead — no WebSocket, no
audio modality question, and, as a bonus, this is also the permanently
correct mechanism for text-based channels like
`features/002_telegram_bridge` (a Telegram message exchange was never a
real-time voice interaction to begin with).

---

# Intent

- Validate the smallest real case first (P9): text in, text out, one
  profile, no persisted conversational memory across messages, no audio.
  Each incoming message is one `generate_content` call, completing one
  turn (including any tool-call round trips within that turn) via
  synchronous request/response — no session, no WebSocket, no connection
  lifecycle to manage. Multi-turn conversational continuity across
  separate messages is a deliberate later step, not attempted here.
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
- `jarvis_cesky`'s `main.py` (reference only, not transferred) uses the
  Gemini **Live** API — not applicable here as of Revision 1.1; see below.
- No `GEMINI_API_KEY` (or equivalent) exists yet in
  `projects/voice_agent/.env.example`.
- **Round 1 finding (2026-07-20, preserved in Completion Notes below):**
  every currently offered Gemini Live model
  (`gemini-2.5-flash-native-audio-preview-12-2025`,
  `gemini-3.1-flash-live-preview`) is native-audio-only;
  `response_modalities=["TEXT"]` is not a supported path on any of them.
  The one model that did support it (`gemini-live-2.5-flash-preview`,
  half-cascade) is deprecated and retired. Independently confirmed by the
  Architect against `ai.google.dev` and Firebase AI Logic documentation
  (both current as of this Contract's revision date). This Contract no
  longer targets the Live API at all — see Revision Notes.

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

- A new module, `backend/services/gemini_chat_handler.py` (renamed from
  the Round 1 `gemini_live_handler.py` — see Revision Notes), implementing:
  - `build_generation_config(profile: Profile) -> types.GenerateContentConfig`
    — `system_instruction = profile.prompt`; `tools` built directly from
    `profile.tools` values (`FunctionDeclaration(name, description,
    parameters)` per entry — no separate hand-maintained list).
  - `execute_tool(function_call, profile: Profile) -> types.Part` (or the
    `generate_content` tool-response equivalent) — resolves
    `profile.tools[fc.name]`, calls
    `action_loader.load_action_function(module, function)`, invokes it
    with `fc.args`, catches exceptions and returns a descriptive error
    result rather than raising.
  - `def handle_message(request: MessageRequest, profile: Profile) -> str`
    — one `client.models.generate_content(...)` call per incoming
    message; if the response contains function calls, executes them via
    `execute_tool`, sends the results back as a follow-up turn in the same
    `generate_content` exchange (function-calling round trip), and returns
    the model's final text. No WebSocket, no session object, no connection
    lifecycle.
  - A `GeminiChatHandler` (or equivalent thin adapter) matching the
    `LiveMessageHandler` signature `AgentRuntime.connect()` already
    expects (the name `LiveMessageHandler` in `agent_runtime.py` is a
    pre-existing type name from Contract 0002 and is not being renamed by
    this Contract — it denotes "the live/active handler", not "uses the
    Live API"), with `profile` bound at construction time (loaded once via
    `profile_loader.load_profile("000_base", ...)`).

  > Status: Done — `gemini_chat_handler.py` implements
  > `build_generation_config`, `execute_tool`, `handle_message` (async, see
  > Completion Notes for the one disclosed deviation), and `GeminiChatHandler`
  > exactly as scoped. Verified with real (non-mocked) calls against
  > `profile_loader`/`tool_catalog`/`action_loader`, and a mocked-client
  > structural test for the round trip. See Completion Notes Round 2.
- `backend/app.py` updated: at startup, if `GEMINI_API_KEY` is set and
  non-empty, construct the handler and call
  `agent_runtime.connect(handler, detail=...)`. If unset, leave the
  runtime exactly as today (`runtime_unavailable`) — no behavior change
  for anyone not using this feature yet.

  > Status: Done — verified with an actual `create_app()` call both with
  > `GEMINI_API_KEY` unset (runtime stays `runtime_unavailable`, identical
  > output) and set to a placeholder value (runtime connects, handler is a
  > `GeminiChatHandler` bound to the `000_base` profile). No real network
  > call made in either case.
- `projects/voice_agent/.env.example` extended with `GEMINI_API_KEY=""`
  and `GEMINI_TEXT_MODEL` (a standard Gemini model suitable for
  `generate_content` with function calling — e.g. the `gemini-2.5-flash`
  family already used elsewhere in this project for the Telegram
  transcription model; confirm current recommended model name against
  Google's documentation rather than assuming, since model names and
  availability shift — but this is a much shallower check than Round 1's,
  since `generate_content` with function calling is a stable, widely
  documented, non-preview capability, not a Live-API-specific edge case).

  > Status: Done — default is `models/gemini-2.5-flash`, matching
  > `TELEGRAM_TRANSCRIPTION_MODEL`'s existing convention in
  > `features/002_telegram_bridge/README.md`. Function calling support
  > confirmed against current (2026-07-20) `ai.google.dev` function-calling
  > documentation — stable, non-preview, no fork.
- `google-genai` added to `requirements.txt` (confirm exact package name
  and minimum version against current PyPI documentation).

  > Status: Done — `google-genai>=1.65.0` pinned to the version already
  > present in the environment; confirmed current PyPI latest is 2.12.1
  > (2026-07-16), well above the floor, so the pin does not force a
  > downgrade. Actually installed into `.venv` at 2.12.1 for verification.
- `README.md` updated: "Current capabilities" gains real Gemini-backed
  responses (text-only, single-turn, one profile, via `generate_content`,
  not Live API); "Current limitations" states plainly: no memory across
  messages, no audio, no multi-turn conversational continuity, single
  profile only, and that Live API / real-time voice is Phase 4b's
  concern, not this Contract's.

  > Status: Done — also corrected two now-stale "Current limitations"
  > bullets left over from before this Contract (the `runtime_unavailable`
  > blanket statement, and "profile_loader nothing calls it yet"), and
  > updated "Planned evolution" to match Revision 1.1's phase renumbering
  > (Phase 4a-bis/4b/4c). See Completion Notes.

---

# Functional Requirements

The implementation SHALL:

- Implement `gemini_chat_handler.py` exactly as scoped in Outputs, using
  `client.models.generate_content` (or the SDK's equivalent stable,
  non-Live chat/content-generation call) — not `client.aio.live.connect`
  or any Live API surface.
- Confirm the chosen model (`GEMINI_TEXT_MODEL`'s default) supports
  function calling via `generate_content` in the current SDK/API — this
  is standard, well-documented behavior, not the open question Round 1
  hit; a quick documentation check suffices, no architectural fork is
  expected here.
- Load the `000_base` profile once at handler construction, not per
  message.
- Wire `agent_runtime.connect(...)` conditionally on `GEMINI_API_KEY`
  being set, at backend startup, without altering `AgentRuntime`'s own
  code.
- Ensure a tool execution exception is caught inside `execute_tool` and
  returned as a descriptive error result rather than raising — verified
  with an actual test call using a tool that deliberately raises,
  mirroring the testing approach used in Contract 0004, not just by code
  inspection.
- Ensure `build_generation_config`'s `tools` list, when inspected, matches
  `profile.tools` exactly (same five tools, same names) — no
  hand-maintained duplicate list.
- Implement the function-calling round trip correctly for
  `generate_content`: send the initial message, detect function-call parts
  in the response, execute them, send the function results back as
  conversation turns, and obtain the final text response — verified with
  an actual call structure test (mocking the Gemini client's response
  shape if a real API key is unavailable in the implementation
  environment), not assumed from documentation alone.

> Status: Done — all six requirements verified with actual test calls (not
> code inspection), run against `google-genai` 2.12.1 in
> `Tr5-platform/.venv`: (1) module uses `client.aio.models.generate_content`
> (the SDK's async equivalent, since the surrounding app is fully async
> FastAPI — see Completion Notes for this one disclosed deviation from the
> literal `client.models.generate_content`/`def handle_message` wording),
> no Live API surface anywhere; (2) `gemini-2.5-flash` function-calling
> support confirmed against current docs, no fork; (3) profile loaded once
> in `build_handler`, not per message; (4) `agent_runtime.connect(...)`
> wired conditionally in `app.py`, `AgentRuntime` itself untouched; (5)
> `execute_tool` tested with a deliberately wrong-kwarg call against the
> real `get_weather` tool — caught, descriptive error, no exception
> propagated; (6) `build_generation_config`'s five declared tool names
> verified to exactly match `profile.tools`'s five keys; (7) round trip
> verified with a mocked `client.aio.models.generate_content` returning a
> function-call response then a text response — exactly two calls made,
> second call's `contents` carries all three turns (user, model
> function-call, function-response), final text returned correctly.

---

# Out of Scope

This Contract SHALL NOT:

- Use the Gemini Live API in any form (WebSocket session, `LiveConnectConfig`,
  audio modality of any kind) — established as the wrong tool for this
  phase per Revision 1.1; Live API is reserved for Phase 4b's real-time
  voice use case.
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

- `build_generation_config(profile)` produces a config whose `tools`
  exactly matches `profile.tools`'s five entries, verified by an actual
  call, not by inspection alone.
- `execute_tool` successfully resolves and would correctly invoke each of
  the five real tools (verified via `action_loader` resolution, consistent
  with how Contract 0004 verified `profile_loader` without needing live
  external services where the tool itself needs one, e.g. weather).
- A simulated tool failure is caught and produces a descriptive error
  result, not an unhandled exception — verified with an actual test call.
- With `GEMINI_API_KEY` unset, backend startup behavior is unchanged from
  today (`runtime_unavailable`) — verified by running the existing
  Contract 0002 smoke test again and confirming identical output.
- The function-calling round trip (initial call → function execution →
  follow-up call with results → final text) is verified structurally, and
  the module contains no reference to the Live API surface
  (`aio.live.connect`, `LiveConnectConfig`) anywhere.
- The Contract is annotated per DOCUMENT_STANDARD §3.1.

> Status: Done — every criterion above verified by actual test call (see
> Functional Requirements annotation for details); `grep`-equivalent search
> of `gemini_chat_handler.py` for "live"/"Live" confirms zero references to
> the Live API surface — the only hit is the docstring naming the
> pre-existing `LiveMessageHandler` type, which Outputs already accounts
> for. This annotation pass fulfills the last criterion.

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

### Round 2 — 2026-07-20 — Verdict: Changes Requested (→ Revision 1.1)
Reviewer: Architect

The Implementation Agent correctly declined to resolve a genuine conflict
by assumption (per P11 and Round 1's own instruction) and reported it
instead: no currently offered Gemini Live model supports a text-only
response, and the one that did is retired. Independently verified against
`ai.google.dev/gemini-api/docs/live-api/capabilities` (updated June 2026)
and Firebase AI Logic's Live API capabilities doc (updated May 2026), both
stating native-audio Live models always require and always produce audio.
Agent's citations (`googleapis/python-genai` #1780, `livekit/agents`
#4423, Google AI Developers forum thread on the retired half-cascade
model) were not independently re-verified line-by-line but are consistent
with, and not contradicted by, the primary documentation checked directly.

Resolution: reframe the underlying goal. Live API's value is real-time,
low-latency voice streaming — Phase 4b's actual concern. This Contract's
goal was always "prove the tool-calling loop works, text in, text out" —
a goal `generate_content` with function calling serves directly, with no
audio question at all, and remains the architecturally correct mechanism
permanently for non-realtime text channels (e.g.
`features/002_telegram_bridge`), not just as a stepping stone. This is a
better design than Round 1's, reached only because Round 1 refused to
paper over the conflict — exactly the value P11's "report, don't guess"
stance is meant to produce. Revised as Revision 1.1; see Revision Notes.
Status reset to `Accepted` for a fresh implementation attempt.

---

# Future Evolution

- Phase 4a-bis: wire `PostgresMemoryRepository`/`MemoryRepository` into
  the handler once this core is proven.
- Phase 4b: Gemini **Live** API, introduced here for the first time, for
  real-time voice input/output — this Contract's `gemini_chat_handler.py`
  and Phase 4b's Live-based handler are expected to coexist, not replace
  each other, since they serve genuinely different channel types (text
  request/response vs. real-time voice streaming).
- Phase 4c: enable and verify `features/002_telegram_bridge` end-to-end —
  a natural fit for `gemini_chat_handler.py` specifically, being itself a
  text channel.
- Multi-turn conversational continuity, once a real need (not a guess)
  shows single-turn-per-message is insufficient.
- Phase 4d / `platform_shell`: connects to this same endpoint, per P17.

---

# Completion Notes

## Round 1 (2026-07-14 attempt, superseded by Revision 1.1 — preserved for history)

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

## Round 2 (new attempt, per Revision 1.1)

Implemented as scoped. `backend/services/gemini_chat_handler.py` created
with `build_generation_config`, `execute_tool`, `handle_message`,
`GeminiChatHandler`, `build_handler`. `backend/app.py` wires
`agent_runtime.connect(...)` conditionally on `GEMINI_API_KEY`.
`.env.example` gained `GEMINI_API_KEY=""` and
`GEMINI_TEXT_MODEL="models/gemini-2.5-flash"`. `requirements.txt` gained
`google-genai>=1.65.0`. `README.md` updated (see Outputs annotations).

One disclosed deviation from the Contract's literal text: Outputs describes
`def handle_message(request: MessageRequest, profile: Profile) -> str` and
Functional Requirements names `client.models.generate_content` (the sync
call). The implementation uses `async def handle_message(...)` calling
`client.aio.models.generate_content` (the SDK's documented async
equivalent) instead. Reason: `backend/app.py`, `backend/api.py`, and every
existing repository/service in this codebase are `async`; `AgentRuntime`'s
own `LiveMessageHandler` type already explicitly supports
`Awaitable[str | MessageResponse]` for exactly this reason
(`agent_runtime.py`'s `handle_message` does
`if inspect.isawaitable(response): response = await response`). Using the
blocking sync client would stall the FastAPI event loop for the duration
of every Gemini call. Functional Requirements' own parenthetical — "(or the
SDK's equivalent stable, non-Live chat/content-generation call)" — was read
as covering this. Flagged here per this repository's disclosure convention
rather than left silent.

Verification performed (all against `google-genai` 2.12.1, installed into
`Tr5-platform/.venv` for this purpose — the project's `requirements.txt`
was previously never installed anywhere; also confirmed the pinned SDK
version's `types.FunctionDeclaration`/`types.Part`/`types.Tool` accept the
project's existing dict-shaped tool schemas directly, coercing into
`Schema` objects without modification):

- `build_generation_config(profile).tools[0].function_declarations` names,
  sorted, exactly equal `profile.tools.keys()`, sorted — both equal the
  five expected tool names.
- `execute_tool` resolves all five real tools via `action_loader` (`get_weather`,
  `get_calendar_events`, `add_calendar_event`, `delete_calendar_event`,
  `open_app`) — confirmed callable, not just importable.
- `execute_tool` called with a deliberately wrong keyword argument against
  the real `get_weather_summary` function raises `TypeError` internally,
  caught, returned as
  `{"error": "Nastroj 'get_weather' selhal: get_weather_summary() got an
  unexpected keyword argument 'not_a_real_kwarg'"}` — not an unhandled
  exception. Also verified the unknown-tool-name path separately.
- `create_app()` with `GEMINI_API_KEY` unset: `agent_runtime.state.connected`
  is `False`; `POST /api/v1/messages` returns `status: "runtime_unavailable"`
  with the same text/detail as before this Contract — identical to the
  pre-existing Contract 0002 behavior.
- `create_app()` with `GEMINI_API_KEY` set to a placeholder (non-network)
  value: `agent_runtime.state.connected` is `True`, handler is a
  `GeminiChatHandler` bound to the `000_base` profile and the configured
  model — no network call made or required for this check.
- Function-calling round trip verified structurally with a mocked
  `client.aio.models.generate_content` (`unittest.mock.AsyncMock`,
  `side_effect` returning a function-call response then a text response):
  exactly two calls made; the second call's `contents` list has three
  turns (user text, model's function-call turn, function-response turn);
  final returned text matches the mocked second response exactly.
- No real Gemini API key was available or used anywhere in this
  verification, per Out of Scope — everything above is either a real,
  local call (profile/tool/action resolution, FastAPI app construction) or
  a structurally-mocked one (the actual Gemini network call).

---

# Implementation Review

(To be completed after implementation.)

---

# Lessons Learned

- Round 1's refusal to paper over the Live-API text-modality conflict
  produced a strictly better Contract on revision, not just an unblocked
  one — worth treating "report, don't guess" as a design tool, not only a
  safety rule.
- When a Contract's Outputs literally names a sync SDK call
  (`client.models.generate_content`) but the surrounding application is
  fully async (as this whole backend is, and as `AgentRuntime`'s own
  `LiveMessageHandler` type already anticipates via
  `Awaitable[str | MessageResponse]`), treat the Functional Requirements'
  "or the SDK's equivalent" escape hatch as covering the async client too
  — but disclose the substitution explicitly rather than silently
  swapping, the same way Contract 0004 disclosed its `core/prompt.txt`
  substitution.
- Neither this project's `.venv` nor the global Python install had the
  project's own `requirements.txt` installed before this Contract — worth
  checking early when a Contract's Acceptance Criteria require actual test
  calls (not just code inspection), since "verify structurally" still
  needs a real interpreter with the real dependencies importable.

---

# Revision Notes

## Revision 1.1

- Replaced the Gemini **Live** API (`aio.live.connect`,
  `LiveConnectConfig`, `response_modalities`) with plain
  `generate_content` and function calling. Reason: every currently
  offered Live model is native-audio-only; no supported text-only path
  exists (confirmed independently by the Architect, not just by the
  Implementation Agent's Round 1 research). Live API is reserved for
  Phase 4b, where real-time voice is the actual point.
  `gemini_live_handler.py` renamed to `gemini_chat_handler.py`;
  `build_live_config` renamed to `build_generation_config`.
  `runtime_unavailable` default behavior, tool-catalog-as-single-source-
  of-truth design, and the deferred-memory decision are unchanged from
  the original Contract.
- This is also a permanent architectural clarification, not just an
  unblocking fix: `generate_content` remains the correct mechanism for
  text-based channels (e.g. the Telegram bridge) even after Phase 4b adds
  Live API for voice — the two are not sequential steps toward the same
  end state, they serve different channel types side by side.
