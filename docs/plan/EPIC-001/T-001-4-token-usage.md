# T-001-4: Report real token usage from Ollama counts

**Epic**: EPIC-001 (OpenAI/Anthropic-compatible proxy correctness)
**Status**: Done
**Depends on**: —
**Blocks**: T-001-5

## Description

The proxy currently estimates token usage as `len(text) // 4` for both prompt and
completion tokens. Ollama's `/api/generate` response already includes accurate counts
(`prompt_eval_count` for input tokens, `eval_count` for output tokens). The fix reads
those fields and surfaces them in the `usage` object, making token accounting accurate
for clients that depend on it.

## User Story

As a developer monitoring token consumption through the proxy,
I want the `usage` field in responses to reflect actual token counts from Ollama,
so that I can track model usage accurately.

## Acceptance Criteria

1. In non-streaming responses, `usage.prompt_tokens` (OpenAI) / `usage.input_tokens` (Anthropic) equals Ollama's `prompt_eval_count`.
2. In non-streaming responses, `usage.completion_tokens` (OpenAI) / `usage.output_tokens` (Anthropic) equals Ollama's `eval_count`.
3. In streaming responses, the final `usage` event reflects the accumulated `eval_count` from Ollama's stream (Ollama emits counts on the last chunk when `stream: true`).
4. If Ollama omits these fields (older versions), the proxy falls back to `0` rather than crashing.
5. The fix applies to both the OpenAI and Anthropic endpoint response shapes.

## Technical Considerations

Ollama emits `prompt_eval_count` and `eval_count` on the final JSON object of a streaming
response (the chunk where `"done": true`). The streaming generators need to detect and
capture that final chunk to populate usage. The non-streaming path already has the full
response body available.

## Out of Scope

- Aggregating usage across multiple requests (no server-side accounting).
- Streaming usage deltas mid-stream (only the final summary is needed).
