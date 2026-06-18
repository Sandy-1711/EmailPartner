# Agentic email assistant — architecture

Status: design agreed 2026-06-18. Not yet built. This is the plan of record for
the assistant layer; build in the phases at the end.

The assistant lets the user **talk to their inbox**: ask about emails, reference
specific ones, draft/send replies in their own voice, set watches ("tell me when
the Acme offer arrives"), read mail aloud, and research a contact. It reuses the
existing seams — `LLMProvider`, the durable `PipelineWorker`, the SSE
`CardEventBus`, the encrypted `GmailApiClient`, and the native `NarrationService`
— and stays provider-agnostic (Gemini today).

## Decisions (locked)

- **Vector store: Qdrant (local Docker)** behind a `VectorStore` seam. Mongo
  stays local for everything else; hybrid search = Qdrant ANN + Mongo `$text`.
- **Send autonomy: a per-user setting** `autonomy_level`:
  - `MANUAL` — assistant only drafts; the user sends with a button.
  - `CONFIRM` — assistant composes and sends, but each send needs a confirm tap.
  - `AUTONOMOUS` — sends without per-message confirmation; bounded by a recipient
    allowlist + daily cap + full audit log.
- **Voice capture: story-prompt only (active).** The Sent-folder mining path is
  **built but disabled** (feature-flagged off) — present in code, not used yet.

## System shape

```
Mobile chat UI ── POST /v1/chat (turn) ──▶ AgentRunner ──▶ Context Builder ──▶ VectorStore (Qdrant) + Mongo
   ▲  references emails, voice            │  loop          └── tools ──▶ Gmail draft/send, watches, TTS, research
   └── GET /v1/chat/stream (SSE: tokens, tool events, confirm gates)

Ingest (existing worker), per new email:
   embed → upsert Qdrant → extract memories → evaluate watches → notify (FCM/SSE)
```

## Memory (storage + RAG)

Three tiers:

1. **Email corpus (episodic)** — the `emails` collection is the source of truth.
   Add a per-email embedding (subject + sender + body; chunk only long ones with
   thread context) stored in Qdrant with metadata for filtering (`user_id`,
   `sender`, `date`, `tone`, `labels`).
2. **Semantic memory (derived facts)** — new `memories` collection: atomic facts
   `{type: preference|contact|commitment|fact, text, source_email_ids[],
   embedding, confidence, created_at, last_seen}`. Written by a memory-extraction
   step in ingest and by the `remember` tool. This is what makes it feel like it
   knows the user, not just searches mail.
3. **Profile (structured singletons)** — `style_profile` and `assistant_config`
   per user; always loaded, never retrieved by similarity.

**Retrieval:** embed query → hybrid (Qdrant vector + Mongo `$text`, fused by
reciprocal rank) over emails+memories, filtered by `user_id` → optional LLM
re-rank → context assembled **with citations** (email/memory ids the UI renders
as tappable cards). @mentioned emails are pinned, not retrieved.

**Ingest hook:** embed → upsert → extract-memories → evaluate-watches runs inside
`PipelineWorker` after a card turns READY (same durable-queue guarantees).

## Chat + agent loop

- `conversations` + `messages` collections (roles user/assistant/tool; tool calls
  and results persisted for replay/audit).
- `AgentRunner`: tool-calling loop (Gemini function calling) with a max-steps
  budget. Build context → call LLM with tool schemas → execute requested tools →
  feed results back → repeat to a final answer or a confirmation gate.
- **Streaming over SSE** (generalize `CardEventBus`): events `message.delta`,
  `tool.call`, `tool.result`, `confirm.required`, `message.done`.
- **System prompt** = persona + `style_profile` + `assistant_config` (language,
  tone) + guardrails + assembled context, composed each turn.

## Tools

Each tool = typed Pydantic args + side-effect class (`read`/`write-draft`/`send`/
`external`) + handler. The registry enforces per-tool permission against
`assistant_config`.

| Tool | Does | Guard |
|---|---|---|
| `search_emails` / `get_email` | RAG retrieval / fetch full body | read |
| `draft_reply` / `compose_email` | Gmail draft in the user's voice | write-draft |
| `send_email` | Send | gated by `autonomy_level` |
| `create_watch` | "tell me when X" | write |
| `read_aloud` | TTS → NarrationService | read |
| `research_contact` | Find an email address | external + consent |
| `remember` / `update_config` | Write memory / preferences | write |

**Gmail scopes:** sending needs `gmail.send`, drafts `gmail.compose`. Current
scopes are `gmail.readonly` + `gmail.modify`, so adding send/draft requires a
re-consent with the new scopes.

## Watchers / triggers

`watches` collection: `{user_id, nl_condition, prefilter (sender/keywords the LLM
compiles once), action (notify|draft|tag), one_shot, status, expires_at}`. In
ingest, after each new email: cheap metadata prefilter → LLM yes/no classify of
the email against `nl_condition` → on match fire the action (FCM + SSE, or
auto-draft) and retire if `one_shot`. Piggybacks on the existing worker +
notifier, so near-zero marginal cost.

## Voice / style capture

- **Active: story prompt.** Onboarding asks the user to free-write a sample; an
  LLM extracts a `style_profile` (formality, warmth, greeting/sign-off patterns,
  sentence length, emoji/punctuation habits, vocabulary quirks) plus verbatim
  exemplars for few-shot.
- **Built but disabled: Sent-folder mining.** Same extraction over recent Sent
  emails (the stronger signal). Implemented behind a flag, off by default; flip
  it on later. (Recorded so it isn't re-implemented or assumed missing.)
- Drafting injects the profile + 2–3 exemplars + reply context. Later: per-
  recipient style keyed off prior threads.

## Research tool

`ResearchProvider` seam (mirrors `LLMProvider`) over a web/people-search or
email-discovery API (e.g. Hunter.io). `research_contact(name, company)` →
candidates + confidence + sources. Gated behind explicit consent, logged, and a
discovered address is never auto-sent-to without confirmation.

## Config + guardrails

- `assistant_config`: language, default tone, `autonomy_level`, signature,
  enabled tools, recipient allowlist, daily-send cap.
- Guardrails (the agent both reads untrusted content and can send mail):
  - **Prompt-injection isolation** — email bodies are *data*, never instructions;
    tool calls are honored only from the user's turns. An email saying "forward
    all invoices to…" can be summarized but can never drive a tool.
  - **Send gate** — `send_email` obeys `autonomy_level`; `AUTONOMOUS` still
    bounded by allowlist + daily cap.
  - **Audit** — every tool run logged to `tool_runs` (args, result, reversible?).
  - PII redaction in logs/research; output moderation.

## New seams (all mirror existing patterns)

- `EmbeddingProvider` (Gemini embeddings) — like `app/infrastructure/llm/providers/base.py`.
- `VectorStore` (Qdrant impl) — like `app/infrastructure/storage/base.py`.
- `ResearchProvider` — same pattern.
- Extend `LLMProvider` with tool-calling + streaming-with-tools.
- Extend `GmailApiClient` with draft/send.
- Generalize `CardEventBus` into a chat event bus.

## New Mongo collections

`conversations`, `messages`, `memories`, `watches`, `style_profiles`,
`assistant_config`, `tool_runs`. (Vectors live in Qdrant, keyed by email/memory id.)

## Build phases

1. **RAG foundation** — Qdrant + `EmbeddingProvider` + `VectorStore` +
   embed-on-ingest + `search_emails`.
2. **Chat skeleton** — conversations/messages + `AgentRunner` + SSE streaming +
   email @references + read-only tools. (First "talk to your inbox" milestone.)
3. **Drafting + send** — voice-aware `draft_reply`/`send_email` + new scopes +
   `autonomy_level` gate + `assistant_config`.
4. **Style capture** — story onboarding (active) + Sent-mining (built, disabled).
5. **Watchers** — triggers in the ingest pipeline.
6. **Semantic memory + research** — `memories` extract/retrieve, `research_contact`.
