# IMPLEMENTATION_CONTRACT_0006

Status: Implemented

---

# Title

Wire short-term memory (`MemoryRepository`) into the Gemini chat handler,
enabling multi-turn continuity backed by Postgres (Phase 4a-bis)

---

# Purpose

Give `gemini_chat_handler.py` access to recent conversation history, so a
follow-up message ("30 minut, můj kalendář") can be understood in the
context of what was just asked — closing the multi-turn gap Contract 0005
explicitly deferred — while also making that history durable across
restarts once `DATABASE_URL` points at a real PostgreSQL instance (in this
case, the person's home server).

This Contract wires existing, already-reviewed infrastructure
(`MemoryRepository`, `PostgresMemoryRepository`, `FallbackMemoryRepository`,
schema auto-creation via `initialize_database`, all from Contract 0002) —
it does not design new storage.

---

# Intent

- Use `MemoryRepository`'s `short_term_memory_turns` — not
  `ConversationRepository`'s `messages` table — as the source for prompt
  context. Both tables store similar-shaped data, but serve different
  purposes: `messages` is the permanent, multi-client-facing transcript;
  `short_term_memory_turns` is a bounded (31-day retention), purgeable,
  full-text-searchable working set explicitly meant to feed a model's
  context, independent of any single conversation thread. This distinction
  is stated explicitly because it was not obvious on first read of the two
  repositories, and a future Contract should not have to rediscover it.
- `long_term_decisions` (confirmed, durable facts) remains out of scope —
  it needs a confirmation UX (per its `confirmed`/`confirmation_text`
  fields) that does not exist yet, and is a separate, later decision.
- Map `session_id` (memory's key) to the resolved `conversation_id`
  (conversations' key) for now — the simplest correct mapping given only
  one profile and one channel type exist today (P2). Revisit only if a
  real case shows session and conversation identity need to differ (e.g.
  memory persisting across separate conversation threads for the same
  user) — not designed for speculatively.
- Persist only the semantic turns (the user's message text, the model's
  final response text) to short-term memory — not intermediate tool-call/
  tool-response parts, which stay internal to a single `generate_content`
  exchange. Keeps stored memory readable and directly replayable as plain
  conversational turns.
- `FallbackMemoryRepository` already catches storage failures and
  degrades to an in-memory fallback (Contract 0002, already reviewed) — no
  additional defensive error handling around memory calls is needed in
  this Contract's new code; duplicating that resilience layer would be
  redundant per P2.

---

# Current State

- `backend/app.py`'s `create_app()` already creates
  `memory = create_memory_repository(settings)`, but never passes it to
  `build_handler`/`gemini_chat_handler` — it is currently only threaded
  into `create_api_router(..., memory=memory, ...)` for (presumably)
  direct memory-inspection endpoints, unrelated to chat.
- `create_memory_repository` already switches between
  `PostgresMemoryRepository` (wrapped in `FallbackMemoryRepository`) and
  `InMemoryMemoryRepository` based on `settings.database_configured` — the
  same proven pattern as `conversations`. No new switching logic needed.
- `PostgresMemoryRepository`/`PostgresConversationRepository` both call
  `initialize_database(engine, schema)` internally on first real use,
  which creates the schema (if named) and all tables via SQLAlchemy
  `Base.metadata.create_all` — no manual migration step required. Verified
  by reading `backend/db/session.py` directly, not assumed.
- `AgentRuntime.handle_message()` resolves `conversation.conversation_id`
  (via `self._conversations.get_or_create(...)`) but calls
  `handler(request)` — passing only the original request, never the
  resolved ID. `request.conversation_id` is `None` on a client's first
  message, so the handler currently has no reliable session key.
- The person has a running, network-reachable PostgreSQL instance on their
  home server (host/port available); `DATABASE_URL` etc. in
  `projects/voice_agent/.env` are not yet pointed at it.

---

# Inputs

- `backend/services/agent_runtime.py`'s `AgentRuntime`,
  `LiveMessageHandler` (existing, minimally modified — see Functional
  Requirements).
- `backend/services/memory.py`'s `MemoryRepository` interface (existing,
  unmodified).
- `backend/services/gemini_chat_handler.py` (Contract 0005, extended here).

---

# Outputs

- `backend/services/agent_runtime.py`: `LiveMessageHandler` signature
  extended to `Callable[[MessageRequest, str], ...]`, where the second
  argument is the resolved `conversation_id`.
  `handler(request, conversation.conversation_id)` replaces
  `handler(request)`. This is the disclosed, narrow exception to Contract
  0005's "do not modify `AgentRuntime`" boundary, agreed with the person
  before drafting this Contract.

  > Status: Done — `LiveMessageHandler` is now
  > `Callable[[MessageRequest, str], ...]`; the single call site at
  > `agent_runtime.py`'s `handle_message` passes
  > `conversation.conversation_id`. No other line in `agent_runtime.py`
  > touched.
- `backend/app.py`: `build_handler(...)` call extended with `memory=memory`
  (the already-created repository, simply threaded through — no new
  factory logic).

  > Status: Done — `memory` (already created earlier in `create_app()`)
  > passed straight through to `build_handler(...)`; no new factory logic
  > added.
- `backend/services/gemini_chat_handler.py`:
  - `build_handler(...)` accepts and stores `memory: MemoryRepository`.
  - `handle_message(request, conversation_id, ...)` — updated signature.
    Before calling Gemini: loads
    `await memory.recent_short_term_turns(limit=MEMORY_RECENT_TURNS_LIMIT,
    session_id=conversation_id)`, converts each into a `types.Content`
    (role mapping: stored `"assistant"` → Gemini `"model"`, stored
    `"user"` → `"user"`), and prepends them to the `contents` list before
    the new user turn. After obtaining the final text response: saves the
    new user turn and the assistant's final text via
    `memory.save_short_term_turn(...)` (two calls, both awaited).
  - `MEMORY_RECENT_TURNS_LIMIT` defined as a module constant (default 20,
    matching `MemoryRepository`'s own interface default — not a new
    number invented here).

  > Status: Done — `build_handler` now accepts and stores `memory`;
  > `handle_message` loads `recent_short_term_turns` before the Gemini
  > call, maps roles via `_content_from_memory_item`, and saves exactly
  > the user text and final assistant text (not intermediate tool-call
  > parts) after the round trip completes — via a single `for...else` loop
  > so the save happens exactly once regardless of exit path. Verified
  > with `InMemoryMemoryRepository` (no real database) — see Completion
  > Notes for the full account, including a testing-methodology mistake
  > that was caught, disclosed, and corrected mid-verification.
- `projects/voice_agent/README.md` updated: "Current capabilities" gains
  multi-turn continuity backed by short-term memory; "Current limitations"
  notes long-term decisions remain unimplemented.

  > Status: Done.

---

# Functional Requirements

The implementation SHALL:

- Modify `LiveMessageHandler`'s type alias and `AgentRuntime.handle_message`'s
  single call site exactly as scoped — no other change to `AgentRuntime`.
- Implement the history-loading and history-saving logic exactly as scoped
  in Outputs.
- Verify the role-mapping (`"assistant"` → `"model"`) is correct against
  the actual `types.Content`/`types.Part` construction already used
  elsewhere in `gemini_chat_handler.py` (Contract 0005) — reuse the same
  `Content`/`Part` construction pattern already present, don't introduce a
  second one.
- Verify, with an actual test (constructing a fake `MemoryRepository` or
  using `InMemoryMemoryRepository` directly — no real Postgres connection
  needed for this), that: (a) a second `handle_message` call for the same
  `conversation_id` includes the first exchange in the `contents` sent to
  Gemini; (b) a call for a *different* `conversation_id` does not.
- Confirm, structurally, that `initialize_database` requires no manual
  step beyond `DATABASE_URL` being set — do not add a separate schema-init
  script or command; the existing lazy-initialization behavior (Contract
  0002) is sufficient and SHALL NOT be duplicated.
- Update `.env.example` only if any new variable is genuinely required —
  `DATABASE_URL`/`DATABASE_NAME`/`DATABASE_USER`/`DATABASE_PASS`/
  `DATABASE_SCHEMA` already exist from Contract 0002; this Contract adds
  no new environment variables unless implementation reveals a real need
  (report if so, per P11, rather than inventing one).

> Status: Done — all five requirements verified with actual test calls
> against `InMemoryMemoryRepository` and a hand-built, `.env`-bypassing
> `BackendSettings` (never against the real Postgres instance, per Out of
> Scope): (1) `LiveMessageHandler`/call site changed exactly as scoped,
> nothing else in `agent_runtime.py` touched; (2) history load/save
> implemented exactly as scoped; (3) role mapping reuses the existing
> `types.Content`/`types.Part` construction from Contract 0005's code, no
> second pattern introduced; (4) same-conversation history inclusion and
> different-conversation exclusion both verified with `InMemoryMemoryRepository`;
> (5) confirmed no new env var was needed — `.env.example` untouched by
> this Contract. `initialize_database`'s lazy schema/table creation was
> exercised for real (see Completion Notes) but only as an unplanned
> consequence of a disclosed testing mistake, not as this Contract's
> verification method.

---

# Out of Scope

This Contract SHALL NOT:

- Implement `long_term_decisions` or any confirmation UX for it.
- Use `ConversationRepository`/`messages` as a memory source (see Intent
  for why `MemoryRepository` was chosen instead).
- Modify anything in `AgentRuntime` beyond the single disclosed signature/
  call-site change.
- Modify `PostgresMemoryRepository`, `FallbackMemoryRepository`,
  `InMemoryMemoryRepository`, or `initialize_database` — all already
  reviewed (Contract 0002) and sufficient as-is.
- Require or assume a live connection to the person's home Postgres server
  during automated verification — the Architect has no network path to it
  from this review environment (same limitation stated in Contract 0005);
  structural/mocked verification is this Contract's bar, live confirmation
  against the real server is the person's job afterward, same division as
  every prior live-tested Contract.
- Add configuration for `MEMORY_RECENT_TURNS_LIMIT` beyond a code
  constant — no env var for it yet; revisit only if a real need appears
  (P2).

---

# Acceptance Criteria

The implementation is accepted when:

- `LiveMessageHandler` and its one call site are updated exactly as
  scoped; `gemini_chat_handler.py`'s `handle_message` accepts and uses
  `conversation_id`.
- A test using `InMemoryMemoryRepository` (no real database) demonstrates:
  a first message and a follow-up message in the *same* `conversation_id`
  produce a `contents` list on the second Gemini call that includes the
  first exchange; a follow-up in a *different* `conversation_id` does not.
- After a successful exchange, exactly two new entries exist in the memory
  repository for that `conversation_id`/`session_id`: the user's text and
  the assistant's final text — not any intermediate tool-call content.
- With `GEMINI_API_KEY` unset, backend startup and message-handling
  behavior is unchanged from Contract 0005 (`runtime_unavailable`) —
  regression-verified, not assumed.
- The Contract is annotated per DOCUMENT_STANDARD §3.1.

> Status: Done — every criterion verified with actual test calls, all
> against `InMemoryMemoryRepository` and isolated settings, never the real
> Postgres instance or a real Gemini key (see Completion Notes for the
> testing-methodology issue that was hit and corrected along the way): (1)
> confirmed by code read and the annotations above; (2) same/different
> `conversation_id` history inclusion/exclusion both demonstrated; (3)
> exactly two new entries (user text, assistant final text, no
> intermediate tool-call content) confirmed for a tool-calling exchange;
> (4) `GEMINI_API_KEY` unset regression confirmed unchanged from Contract
> 0005; (5) this annotation pass fulfills the last criterion.

---

# Architecture Review

### Round 1 — 2026-07-21 — Verdict: Accepted
Reviewer: Architect

The scope was narrowed twice during drafting, both times before writing
any code, and both are recorded here rather than left implicit: first,
recognizing that "wire memory" and "fix multi-turn continuity" are the
same underlying need and can be solved together (per P9 — validate the
smallest real case, here meaning don't build two separate mechanisms for
what turns out to be one gap); second, correcting an initial instinct to
read history from `ConversationRepository` instead of `MemoryRepository`,
after checking `jarvis_cesky`'s original `memory_manager.py` (neither
existing repository is a direct port of it, but `MemoryRepository`'s
bounded/searchable/purgeable design is the closer functional match for
model-context use, while `ConversationRepository` serves client-facing
display — confirmed by reading both interfaces directly, not assumed from
naming). The disclosed `AgentRuntime` signature change was agreed with the
person explicitly before this Contract was drafted, consistent with P12 —
this narrow exception to Contract 0005's stated boundary is proportionate
to what it unlocks (real conversational continuity), not a reopening of
`AgentRuntime`'s design generally. No conflict with
`FOUNDATIONAL_WORLDVIEW.md` or `PRINCIPLES.md`. Accepted as drafted.

---

# Future Evolution

- `long_term_decisions` + confirmation UX, once a real need for durable
  cross-session facts (not just recent-turn continuity) is identified.
- Revisit `session_id` = `conversation_id` mapping if multiple channels
  for the same person need shared memory across separate conversation
  threads.
- `MEMORY_RECENT_TURNS_LIMIT` configurability, if 20 turns proves wrong in
  practice.
- Phase 4b: audio; Phase 4c: Telegram bridge end-to-end (will also benefit
  from this Contract's continuity, being itself a text channel).

---

# Completion Notes

Implemented as scoped. `agent_runtime.py`'s `LiveMessageHandler` and its
one call site updated. `gemini_chat_handler.py` gained
`MEMORY_RECENT_TURNS_LIMIT`, `_content_from_memory_item`, and an extended
`handle_message`/`GeminiChatHandler`/`build_handler` that load history
before and save the new exchange after each Gemini call. `app.py` threads
`memory` into `build_handler(...)`. `README.md` updated (see Outputs
annotations). No new environment variables were needed.

**Disclosed incident during verification, fully resolved:** partway
through re-verifying Contract 0005's "`GEMINI_API_KEY` unset ⇒
`runtime_unavailable`" regression for this Contract, a real `.env` file
was discovered to now exist in `projects/voice_agent/` (it did not exist
during Contract 0005's own verification) containing a real `GEMINI_API_KEY`
and a real `DATABASE_URL` pointing at the person's home Postgres server.
Two mistakes in test methodology, both now understood and corrected:

1. `os.environ.pop("GEMINI_API_KEY", None)` does not simulate "unset" —
   `config.py`'s `_load_env_file()` only skips a key already present in
   `os.environ`; popping it makes the loader silently reload the real
   value from the real `.env` file on the next `load_settings()` call.
2. `backend/app.py` has a module-level `app = create_app()` (needed for
   uvicorn's `backend.app:app` import string) that runs as a side effect
   of merely importing the module — with `settings=None`, this always
   calls the real `load_settings()`/`_load_env_file()`, regardless of any
   isolated `BackendSettings` object constructed afterward in the same
   process, because `GEMINI_API_KEY`/`GEMINI_TEXT_MODEL` are read directly
   from `os.environ` in `create_app`, not from the `BackendSettings` object.

Net effect: two test scripts made real calls to the real Gemini API (one
each), and the first of the two also wrote real rows (two throwaway
conversations, channel `"api"`, with junk text like `"ahoj"` /
`"Ahoj, jak ti mohu pomoci?"` / `"Test odpoved."`) to the person's real
Postgres database, alongside four `short_term_memory_turns` rows. Both
were disclosed to the person immediately on discovery, before any further
action. With explicit permission, the exact junk rows were identified by
content match (`conv_766b749eb508463a9831a6ec31274940`,
`conv_7bbe0f78ff8141d2a991f7047d5b35c5` — confirmed by listing, not
guessed from memory) and deleted via a targeted `DELETE ... WHERE id IN
(...)`, verified afterward against the real database: zero matching junk
rows remain, and all eight pre-existing legitimate conversations (channels
`desktop`/`test`, dated 2026-06-20/21, from earlier manual testing) are
untouched, confirmed by re-listing before and after.

Corrected methodology used for all verification from that point on, and
the basis for every Status: Done annotation above: pre-set (never pop)
`GEMINI_API_KEY`, `GEMINI_TEXT_MODEL`, and `DATABASE_URL` to blank strings
in `os.environ` *before* importing `backend.app` at all, so `_load_env_file`
skips reloading the real values regardless of the unavoidable module-level
`create_app()` import side effect; additionally monkeypatch the real
`GeminiChatHandler`'s `._client.aio.models.generate_content` even when a
placeholder key is used, so no real network call can occur under any
circumstance. All Acceptance Criteria above were (re-)verified this way,
never against the real Postgres instance or a real Gemini key, consistent
with this Contract's own Out of Scope.

---

# Implementation Review

### Round 1 — 2026-07-22 — Verdict: Accepted, with a serious flagged incident
Reviewer: Architect

Functional verification independently re-confirmed, safely, in the
Architect's own sandbox (no `.env` present there at all, so no real
credentials were ever reachable — different safety margin than the
Implementation Agent had, which ran on the person's own machine with a
real `.env` present):

- Built a fake `genai.Client` via `AsyncMock` and an `InMemoryMemoryRepository`
  (no real network, no real database anywhere in this test): confirmed a
  second `handle_message` call in the *same* `conversation_id` sends 3
  `contents` on the second Gemini call and includes the first exchange's
  text; a call in a *different* `conversation_id` sends only 1 (no
  cross-contamination). Confirmed exactly 4 stored turns for the first
  conversation after 2 exchanges, exactly 2 for the second after 1 —
  matching the Contract's Acceptance Criteria precisely.
- Re-ran the `GEMINI_API_KEY`-unset regression: identical `status` output
  to Contracts 0002/0005. Confirmed safe: this Architect's sandbox has no
  `.env` file at all (it is gitignored and was never part of any clone),
  so `_load_env_file` had nothing to load regardless of any pop/unset
  question — this environment was never at risk of repeating the
  Implementation Agent's incident, by construction rather than by care
  taken in the moment.

**The incident disclosed in Completion Notes is accepted as correctly
handled, but is the dominant finding of this review, not a footnote.**
Real external systems (the person's actual Gemini quota/cost and actual
home database) were touched by verification code. The Agent's own
disclosure, permission-seeking, and precise remediation are commended
explicitly — this is exactly the standard expected when something goes
wrong, per P11's spirit applied to mistakes, not just to open questions.
Extracted as P21 (new, safety-relevant) and a priority backlog item in
PRINCIPLES.md — the underlying structural gap
(`backend/app.py`'s import-time `create_app()` side effect) is not fixed
by this Contract and remains open.

**This Architect cannot independently verify the person's real database
state** — the deletion's correctness rests on the Implementation Agent's
own before/after listing, not on independent confirmation. The person is
asked directly, outside this Contract text, to verify their own database.

Status changed to `Implemented` — the delivered code meets its Acceptance
Criteria — but flagged: the next Contract touching anything with real
external side effects (Phase 4c, Telegram bridge, most likely) should not
proceed until the P21 backlog item is at least discussed, given it already
caused one real incident.

**Person's independent confirmation (2026-07-22):** verified their own
production database directly — exactly 8 conversations present, matching
the Agent's own before/after count, and confirmed the permission to delete
the two junk conversations was theirs, given directly to the Implementation
Agent. Incident considered closed on the data-integrity question; the
structural gap itself (P21, backlog) remains open and unresolved by this
Contract.

---

# Lessons Learned

- A module with a top-level `app = create_app()` (needed for `uvicorn`'s
  import-string convention) makes plain `import` unsafe for isolated
  testing once any real secret exists in a real `.env` file anywhere the
  process can see it — the import alone triggers a full real-settings
  `create_app()` as a side effect, before any test code runs. Future
  verification against this backend should pre-set (never pop) every
  secret-bearing env var to a blank string *before* the first import of
  `backend.app`, not rely on constructing an isolated `BackendSettings`
  object afterward — that only isolates fields that actually live on
  `BackendSettings` (like `database_url`), not ones read directly from
  `os.environ` inside `create_app` (like `GEMINI_API_KEY`).
- `os.environ.pop(key, None)` and "unset" are not equivalent whenever a
  real `.env` file is reachable — `_load_env_file`'s own skip condition
  (`key in os.environ`) means popping *invites* a reload, while setting the
  key to `""` first reliably blocks it. Worth remembering for any future
  Contract's "verify X unset" acceptance criterion in this codebase.
- When a testing mistake touches a real external system (here: a real API
  key and a real, person-owned database), disclose immediately and fully
  before taking any further action, then ask before touching that system
  again (even for cleanup) — identify affected rows by content/attribute
  match and verify the fix afterward, don't reconstruct IDs from memory or
  assume a blast radius without checking it directly.
