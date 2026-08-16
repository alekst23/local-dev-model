# T-001-2: Correct multi-role prompt construction (system/user/assistant)

**Epic**: EPIC-001 (OpenAI/Anthropic-compatible proxy correctness)
**Status**: Done
**Depends on**: —
**Blocks**: T-001-5

## Description

`_messages_to_prompt` maps any non-`user` role to the "Assistant:" prefix, so a
`system` message becomes "Assistant: You are a helpful assistant." This corrupts the
prompt structure and causes the model to ignore system instructions or misattribute them.
The fix correctly distinguishes `system`, `user`, and `assistant` roles in the
constructed prompt.

## User Story

As a developer passing a `system` message to configure model behavior,
I want the proxy to represent that message as a system instruction in the Ollama prompt,
so that the model applies the system context correctly.

## Acceptance Criteria

1. A message with `role: "system"` is prefixed with `System:` (or equivalent Ollama-appropriate marker) in the constructed prompt, distinct from `User:` and `Assistant:`.
2. A message with `role: "assistant"` is prefixed with `Assistant:` in the constructed prompt.
3. A message with `role: "user"` is prefixed with `User:` in the constructed prompt.
4. An unrecognized role value does not crash the proxy; it is treated as `user`.
5. The fix applies identically to both the OpenAI (`/v1/chat/completions`) and Anthropic (`/v1/messages`) code paths, since both call `_messages_to_prompt`.

## Technical Considerations

Ollama's `/api/generate` accepts a raw `prompt` string; there is no native system-message
field in that API. The conventional approach for instruct-tuned models is to prefix system
content with a `[INST]`/`<<SYS>>` marker or simply "System:\n<text>\n\n" before the
dialogue. Using `System:` as the prefix is the simplest portable option.

## Out of Scope

- Structured content blocks (`content` as an array instead of a string) — handled in EPIC-002.
- Model-specific prompt templates (e.g., Llama-2 chat format) — out of scope for this epic.
