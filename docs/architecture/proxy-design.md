# Proxy Design

This doc covers the design of the Ollama proxy — its API contract, routing model,
and the key decisions that shape how requests from clients reach Ollama. Intended
for developers integrating the proxy into projects or extending its behavior.

## Dual API Surface

The proxy exposes two distinct HTTP endpoint families from a single Ollama backend:

| Family | Endpoint | Shaped like |
|--------|----------|-------------|
| OpenAI-compatible | `POST /v1/chat/completions` | OpenAI Chat Completions API |
| Anthropic-compatible | `POST /v1/messages` | Anthropic Messages API |
| Model discovery | `GET /v1/models` | OpenAI models list |
| Health | `GET /health` | Proxy-specific |
| Ollama passthrough | `GET/POST /api/*` | Ollama native API |

Both `/v1/chat/completions` and `/v1/messages` accept the same underlying input
(a `messages` array, `model`, `max_tokens`, `temperature`, `stream`) and route to
Ollama's `/api/generate`. The difference is purely in the response envelope shape,
not in how the request is processed.

The OpenAI family is the right choice for clients using the `openai` Python/JS SDK
or any tool expecting OpenAI-style responses. The Anthropic family is used by
Claude Code / Claude CLI when `ANTHROPIC_BASE_URL` is pointed at the proxy.

## Model Selection

The startup model (`--model` / `OLLAMA_MODEL` env var) is a **default**, not a lock.
Clients may override it per-request via the `model` field:

| Request `model` field | Behaviour |
|-----------------------|-----------|
| Non-empty string | That model is sent to Ollama as `model` |
| Empty string or omitted | Startup `OLLAMA_MODEL` is used |

`GET /v1/models` returns the live list of models Ollama has installed by proxying
`/api/tags` — it does not return a static single-model list. This means clients
that enumerate models before making a request see the actual installed set.

## Prompt Construction

Ollama's `/api/generate` accepts a single flat `prompt` string, not a structured
messages array. The proxy converts the `messages` array into a prompt using a
role-prefix format:

| Message role | Prefix in prompt |
|--------------|-----------------|
| `system` | `System: <content>` |
| `user` | `User: <content>` |
| `assistant` | `Assistant: <content>` |
| Any other role | `User: <content>` (fallback) |

A trailing `Assistant:` line is appended after all messages to prompt the model
to continue as the assistant. This format works portably across instruct-tuned
models without requiring model-specific templates.

**Limitation**: this flat-text format is vulnerable to turn-delimiter injection
if message content contains newlines followed by role prefixes. It also does not
support structured content blocks (arrays of `{type, text}` objects) — content
is assumed to be a plain string. See the out-of-scope note in the epic plan for
the roadmap item that addresses this via Ollama's `/api/chat`.

## Token Counting

Non-streaming responses include a `usage` object populated from Ollama's own
token counts, not from text-length estimation:

| Usage field (OpenAI) | Usage field (Anthropic) | Source |
|----------------------|------------------------|--------|
| `prompt_tokens` | `input_tokens` | `prompt_eval_count` from Ollama |
| `completion_tokens` | `output_tokens` | `eval_count` from Ollama |
| `total_tokens` | — | sum of the two |

For streaming Anthropic responses, the counts are captured from the final Ollama
chunk (the one with `"done": true`) and emitted in the `message_delta` SSE event.
If Ollama omits these fields (older versions), the proxy defaults to `0` rather
than crashing.

## Output Length

`max_tokens` from the request is passed directly to Ollama as `num_predict`.
When omitted or invalid (zero, negative, non-numeric), the proxy defaults to
`2048`. There is no artificial ceiling — clients requesting large outputs receive
them, subject to the model's context window and the Ollama process's resources.

## References

- [`src/ollama_proxy/app.py`](../../src/ollama_proxy/app.py) — all routing and
  transformation logic lives here
- [`docs/architecture/README.md`](README.md) — index of architecture docs
