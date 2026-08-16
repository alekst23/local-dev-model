# T-001-5: Integration verification + docs update

**Epic**: EPIC-001 (OpenAI/Anthropic-compatible proxy correctness)
**Status**: Done
**Depends on**: T-001-1, T-001-2, T-001-3, T-001-4
**Blocks**: —

## Description

After the four correctness fixes land, this ticket verifies that they work together
end-to-end (streaming and non-streaming, both endpoints) and updates the README to
document the corrected behavior so users know what to expect.

## User Story

As a developer reading the README before using the proxy in a project,
I want accurate documentation of what `max_tokens`, `model`, message roles, and usage
fields do,
so that I can integrate the proxy correctly without discovering limitations by trial and error.

## Acceptance Criteria

1. A manual or automated end-to-end test hits `/v1/chat/completions` with `max_tokens: 1024`, a `system` message, and a non-default `model`; the response contains more than 256 tokens, the system instruction is reflected in the reply, and `usage.completion_tokens` matches the actual output length.
2. The same test passes for `/v1/messages` (Anthropic shape).
3. The same test passes with `stream: true` on both endpoints.
4. The README's "Usage" section documents: actual `max_tokens` behavior (default and pass-through), per-request model selection, supported message roles, and accurate token usage reporting.
5. No regression in the Claude Code / Claude CLI flow (the `/v1/messages` path still works with `ANTHROPIC_BASE_URL` set).

## Out of Scope

- Automated CI pipeline setup.
- Performance benchmarking.
