# T-001-3: Honor per-request `model` selection

**Epic**: EPIC-001 (OpenAI/Anthropic-compatible proxy correctness)
**Status**: Done
**Depends on**: —
**Blocks**: T-001-5

## Description

The proxy configures a single model at startup (`--model` / `OLLAMA_MODEL`) and ignores
the `model` field in incoming requests entirely. Every request is routed to the startup
model regardless of what the client asked for. The fix passes the request's `model`
through to Ollama when provided, using the startup model as the default/fallback.

## User Story

As a developer calling the proxy with `model: "llama2"`,
I want Ollama to use `llama2` for that request,
so that I can switch models per-call without restarting the proxy.

## Acceptance Criteria

1. When a request includes a non-empty `model` field, that model name is sent to Ollama as the `model` parameter.
2. When a request omits `model` or sends an empty string, the startup `OLLAMA_MODEL` is used.
3. The `/v1/models` endpoint returns a list that reflects all models currently available in Ollama (via `/api/tags`), not just the startup model.
4. The fix applies to both streaming and non-streaming paths on both endpoints.
5. If Ollama returns an error for an unknown model, the proxy surfaces that error to the client with an appropriate HTTP status (≥ 400).

## Technical Considerations

`app.config["OLLAMA_MODEL"]` is currently the only model reference. After this fix it
becomes the fallback default. The `models()` route should proxy `/api/tags` from Ollama
rather than returning a static one-model list.

## Out of Scope

- Model aliasing or name translation.
- Caching the Ollama model list; a live proxy call is sufficient.
