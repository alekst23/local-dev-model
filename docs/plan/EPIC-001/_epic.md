# EPIC-001: OpenAI/Anthropic-compatible proxy correctness

**Depends on**: —
**Blocks**: —
**Design**: (not started — run /at-epic-design EPIC-001)

## Description

The proxy exposes `/v1/chat/completions` and `/v1/messages` but four request-handling
defects make it unusable for real project traffic: output is hard-capped at 256 tokens,
the per-request `model` field is ignored, non-user roles (including `system`) are
mislabeled as "Assistant" in the prompt, and token usage is faked as `len/4`. This epic
fixes all four so the proxy works correctly as a drop-in local endpoint for any
OpenAI-style or Anthropic-style client.

## User Story

As a developer using the proxy for local LLM development,
I want the proxy to faithfully pass through `max_tokens`, `model`, message roles,
and token counts,
so that my project's chat completion calls behave the same way against the proxy as
they would against a real API endpoint.

## Ticket Summary

| # | Ticket | Title | Depends On | Status |
|---|--------|-------|------------|--------|
| 1 | T-001-1 | Honor requested `max_tokens` (remove 256 hard cap) | — | Done |
| 2 | T-001-2 | Correct multi-role prompt construction (system/user/assistant) | — | Done |
| 3 | T-001-3 | Honor per-request `model` selection | — | Done |
| 4 | T-001-4 | Report real token usage from Ollama counts | — | Done |
| 5 | T-001-5 | Integration verification + docs update | T-001-1, T-001-2, T-001-3, T-001-4 | Done |

## Dependency Graph

```
T-001-1 ──┐
T-001-2 ──┤
T-001-3 ──┼──> T-001-5
T-001-4 ──┘
```

## Wave Plan

- **Wave 1** (parallel): T-001-1, T-001-2, T-001-3, T-001-4 — no inter-dependencies
- **Wave 2**: T-001-5 — depends on all Wave 1 tickets

## Acceptance Criteria

1. A client requesting `max_tokens: 4096` receives up to 4096 tokens of output; omitting `max_tokens` defaults to 2048 with no hard ceiling below that.
2. A `system` message is correctly distinguished from `user` and `assistant` messages in the prompt sent to Ollama.
3. Passing `model: "llama2"` in a request causes Ollama to use `llama2`, not the startup default.
4. The `usage` object in responses reflects the actual token counts returned by Ollama (`prompt_eval_count` / `eval_count`), not length-divided estimates.
5. All four fixes work for both streaming and non-streaming paths on both `/v1/chat/completions` and `/v1/messages`.
6. The README documents the corrected behavior for each fix.

## Design References

- `src/ollama_proxy/app.py` — all four defects live here; see `_bound_max_tokens`, `_messages_to_prompt`, the `model` config usage, and usage payload construction.
- Ollama `/api/generate` response schema: `prompt_eval_count`, `eval_count` are the real token count fields.

## Out of Scope

- Tool/function calling and multimodal content blocks (planned as EPIC-002).
- Authentication or rate-limiting on the proxy.
- Support for Ollama's `/api/chat` endpoint (uses a different message format than `/api/generate`).
