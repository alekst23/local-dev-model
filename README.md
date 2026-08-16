# Local LLM Development with Ollama and Claude CLI

This setup allows you to run open-source LLMs locally using Ollama and integrate them with Claude CLI.

## Architecture

- **Ollama**: Runs LLM models locally with an OpenAI-compatible API
- **Local Proxy App (Python + uv)**: Routes Claude CLI requests to your local Ollama instance
- **Claude CLI**: Standard CLI tool configured to use local model

## Prerequisites

- GPU support (NVIDIA CUDA or AMD ROCm recommended for better performance)
- ~8GB VRAM minimum for small models (7B), more for larger models
- Linux/macOS/Windows with Docker or native support

## Installation Steps

### 1. Install Ollama

Download from https://ollama.ai or install via package manager:

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Or visit https://ollama.ai for Windows
```

Start Ollama:
```bash
ollama serve
```

### 2. Pull a Model

In another terminal, choose a model:

```bash
# Recommended for Claude CLI (7B, balanced)
ollama pull mistral

# Or other options:
ollama pull llama2          # 7B, good quality
ollama pull neural-chat     # 7B, instruction-tuned
ollama pull dolphin-mixtral # 8x7B MoE (requires more VRAM)
```

### 3. Test Ollama API

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

### 4. Install Claude CLI

```bash
npm install -g claude-cli
# or pip install claude-cli (Python version)
```

### 5. Install uv and Sync Dependencies

```bash
# Install uv (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync project dependencies from pyproject.toml
uv sync
```

### 6. Configure Claude CLI for Local Model

The Python proxy now lives in a mini app/module under src/ollama_proxy and is launched with uv.

## Usage

### Option A: Run the Proxy App (Recommended)

```bash
# Start the proxy
uv run ollama-proxy

# In another terminal, configure Claude Code CLI
export ANTHROPIC_BASE_URL=http://localhost:3000
export ANTHROPIC_API_KEY=local

# Use Claude CLI normally
claude "What is machine learning?"
```

### Option B: Run as a Python Module

```bash
uv run python -m ollama_proxy
```

### Option C: Direct Ollama Integration

Use Ollama's OpenAI-compatible API directly with tools that support custom endpoints.

### Option D: Claude Code via Ollama Launch (No Proxy)

If you want Claude Code to run against a local Ollama model directly, you can use Ollama's built-in integration launcher.

1. Ensure Ollama is running.

```bash
# If using systemd service (common on Linux)
sudo systemctl status ollama

# If not using service, run manually in one terminal
ollama serve
```

Note: if you see "bind: address already in use", Ollama is already running on port 11434. In that case, do not start another ollama serve process.

2. Pull a coding model.

```bash
ollama pull qwen2.5-coder:latest
```

3. Configure and launch Claude Code with the local model.

```bash
ollama launch claude --config --model qwen2.5-coder:latest -y
claude
```

4. Verify local runtime health.

```bash
ollama ps
nvidia-smi
```

If generation is very slow and ollama ps shows CPU processing, your local Ollama runtime is likely not using GPU acceleration.

5. Optional: store Ollama models on a larger disk.

```bash
export OLLAMA_MODELS=/media/aleks/data2/ollama-models
mkdir -p "$OLLAMA_MODELS"
ollama pull qwen2.5-coder:latest
```

## API Usage

The proxy exposes two API shapes — OpenAI-compatible (`/v1/chat/completions`) and
Anthropic-compatible (`/v1/messages`) — both backed by your local Ollama instance.

### max_tokens

- If omitted, the proxy defaults to **2048** tokens.
- If provided, the requested value is passed through to Ollama with no artificial ceiling.
- Example: `"max_tokens": 4096` will allow up to 4096 tokens of generation.

### model selection

- Pass `"model"` in the request body to use any model Ollama has available.
- If omitted, the proxy falls back to the model set at startup via `--model` or
  the `OLLAMA_MODEL` environment variable.
- `GET /v1/models` returns all models Ollama currently has loaded (proxies
  `/api/tags`), not just the default model.

### message roles

All three standard roles are correctly mapped in the prompt sent to Ollama:

| Role | Prompt prefix |
|------|---------------|
| `system` | `System:` |
| `user` | `User:` |
| `assistant` | `Assistant:` |

### token usage

Responses include actual token counts from Ollama (`prompt_eval_count` /
`eval_count`), not estimates.

- **OpenAI shape**: `usage.prompt_tokens` / `usage.completion_tokens`
- **Anthropic shape**: `usage.input_tokens` / `usage.output_tokens`

Streaming Anthropic responses capture counts from Ollama's final `"done": true`
chunk and report them in the `message_delta` usage event.

### Example: OpenAI library

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:3000/v1",
    api_key="local",  # any non-empty string
)

response = client.chat.completions.create(
    model="qwen2.5-coder:latest",   # any model Ollama has pulled
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain what a Python generator is."},
    ],
    max_tokens=1024,
)

print(response.choices[0].message.content)
print("tokens used:", response.usage.completion_tokens)
```

## Model Recommendations

| Model | Size | Speed | Quality | VRAM |
|-------|------|-------|---------|------|
| mistral | 7B | Fast | Good | 8GB |
| llama2 | 7B | Medium | Good | 8GB |
| neural-chat | 7B | Fast | Excellent | 8GB |
| dolphin-mixtral | 8x7B | Slower | Excellent | 48GB |
| llama2-70b | 70B | Very Slow | Excellent | 48GB |

## Performance Tips

- GPU acceleration is critical for reasonable inference speed
- Start with 7B models; they're fast and quality is good
- Use `ollama list` to see installed models
- Run `ollama show <model>` to see model details

## Troubleshooting

**Ollama not responding:**
```bash
curl http://localhost:11434/api/tags  # Check if Ollama is running
```

**Models running slowly:**
- Check GPU utilization: `nvidia-smi` or `rocm-smi`
- Reduce model size or context window
- Allocate more GPU memory

**Memory issues:**
- Monitor with `watch nvidia-smi` (NVIDIA) or `watch rocm-smi` (AMD)
- Close other GPU applications
- Use smaller models
