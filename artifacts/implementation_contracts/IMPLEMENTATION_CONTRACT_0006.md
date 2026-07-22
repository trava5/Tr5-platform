# IMPLEMENTATION_CONTRACT_0006

Status: Accepted

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
- `backend/app.py`: `build_handler(...)` call extended with `memory=memory`
  (the already-created repository, simply threaded through — no new
  factory logic).
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
- `projects/voice_agent/README.md` updated: "Current capabilities" gains
  multi-turn continuity backed by short-term memory; "Current limitations"
  notes long-term decisions remain unimplemented.

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

(To be completed after implementation.)

---

# Implementation Review

(To be completed after implementation.)

---

# Lessons Learned

(To be completed after implementation.)
