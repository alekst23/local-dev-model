# T-001-1: Honor requested `max_tokens` (remove 256 hard cap)

**Epic**: EPIC-001 (OpenAI/Anthropic-compatible proxy correctness)
**Status**: Done
**Depends on**: —
**Blocks**: T-001-5

## Description

`_bound_max_tokens` in `app.py` clamps every request's `max_tokens` to a maximum of 256
regardless of what the client requested. This silently truncates long responses and makes
the proxy unusable for tasks requiring more than a short paragraph of output. The fix
removes the artificial ceiling while keeping the 2048 default for requests that omit
`max_tokens`.

## User Story

As a developer calling the proxy with `max_tokens: 4096`,
I want Ollama to actually generate up to 4096 tokens,
so that long responses are not silently cut off.

## Acceptance Criteria

1. When a request includes `max_tokens: N` where N > 256, Ollama receives `num_predict: N`.
2. When a request omits `max_tokens`, Ollama receives `num_predict: 2048`.
3. The fix applies to both streaming and non-streaming paths.
4. The fix applies to both the OpenAI-compatible (`/v1/chat/completions`) and Anthropic (`/v1/messages`) endpoints.
5. Passing `max_tokens: 0` or a negative value does not crash the proxy; it falls back to the 2048 default.

## Technical Considerations

The `_bound_max_tokens` helper is the only change point; both streaming and non-streaming
callers use it. Ollama's `num_predict: -1` means unlimited — avoid passing that unless
we explicitly want to expose an "unlimited" sentinel.

## Out of Scope

- Enforcing a server-side maximum (no rate-limiting or resource protection is in scope).
