# Testing Guide

This guide helps you verify everything is working correctly.

## Step-by-Step Testing

### 1. Verify Ollama Installation

```bash
ollama --version
# Output: ollama version X.X.X
```

### 2. Start Ollama Service

```bash
ollama serve
# Output: listening on 127.0.0.1:11434
```

**Keep this terminal open.** In a new terminal, proceed with Step 3.

### 3. Pull a Model

```bash
ollama pull mistral
# or try: llama2, neural-chat, dolphin-mixtral, etc.
```

### 4. Test Ollama API Directly

```bash
# Test basic generation
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Hello! What is your name?",
  "stream": false
}' | jq .

# List available models
curl http://localhost:11434/api/tags | jq .

# Show model details
curl http://localhost:11434/api/show -d '{"name": "mistral"}' | jq .
```

Expected responses:
- Generation returns JSON with `response` field
- Tags returns list of installed models
- Show returns model details

### 5. Set Up Python Proxy (Option A)

```bash
# Install dependencies
pip install -r requirements.txt

# Start the proxy
python3 claude-ollama-proxy.py
```

Expected output:
```
🚀 Claude CLI Proxy for Ollama (Python)
📡 Ollama URL: http://localhost:11434
🤖 Model: mistral
🔌 Proxy running on: http://localhost:3000

📝 Configure Claude CLI:
  export CLAUDE_API_URL=http://localhost:3000
  export CLAUDE_API_KEY=local

✅ Proxy starting...
```

**Keep this terminal open.** In a new terminal, proceed with Step 6.

### 5B. Set Up Node.js Proxy (Option B, Alternative to 5)

```bash
# Install dependencies (optional)
npm install

# Start the proxy
node claude-ollama-proxy.js
```

Expected output:
```
🚀 Claude CLI Proxy for Ollama
📡 Ollama URL: http://localhost:11434
🤖 Model: mistral
🔌 Proxy running on: http://localhost:3000
```

### 6. Test the Proxy

In a new terminal:

```bash
# Test health check
curl http://localhost:3000/health | jq .

# Expected:
# {
#   "status": "ok",
#   "model": "mistral",
#   "ollama_url": "http://localhost:11434"
# }

# Test chat completion
curl http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [
      {"role": "user", "content": "What is Python?"}
    ],
    "stream": false
  }' | jq .

# Expected response with assistant message
```

### 7. Test with Claude CLI

```bash
# Install Claude CLI if not already installed
npm install -g claude-cli
# or: pip install claude-cli

# Configure for local model
export CLAUDE_API_URL=http://localhost:3000
export CLAUDE_API_KEY=local

# Test it!
claude "What is machine learning?"

# You should see a response from your local model
```

### 8. Test Streaming

```bash
# Streaming chat completion
curl http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [
      {"role": "user", "content": "Tell me a joke"}
    ],
    "stream": true
  }'

# Should see server-sent events (SSE) with streaming response
```

## Troubleshooting

### Ollama not responding

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If fails, start Ollama
ollama serve
```

### Proxy not connecting to Ollama

```bash
# Check Ollama is accessible
curl http://localhost:11434/api/tags

# Check proxy logs for specific error
# Restart proxy with correct OLLAMA_URL
OLLAMA_URL=http://localhost:11434 python3 claude-ollama-proxy.py
```

### Claude CLI not finding proxy

```bash
# Verify proxy is running
curl http://localhost:3000/health

# Check environment variables
echo $CLAUDE_API_URL
echo $CLAUDE_API_KEY

# Should output:
# http://localhost:3000
# local
```

### Slow responses

```bash
# Check which model is running
ollama list

# Monitor GPU usage
nvidia-smi  # for NVIDIA
rocm-smi    # for AMD

# Tips:
# - Use smaller models (7B instead of 70B)
# - Close other applications
# - Ensure CUDA/ROCm is properly installed
```

### Out of memory errors

```bash
# Check available GPU memory
nvidia-smi  # for NVIDIA
rocm-smi    # for AMD

# Switch to smaller model
ollama pull mistral    # 7B
ollama pull neural-chat  # 7B
# Instead of
ollama pull dolphin-mixtral  # 48GB+
```

## Performance Benchmarks

Approximate response times on different hardware (first response includes model loading):

### NVIDIA RTX 4090 (24GB VRAM)
- Mistral 7B: ~1-2 tokens/sec
- Llama2 70B: ~2-4 tokens/sec

### NVIDIA RTX 3060 (12GB VRAM)
- Mistral 7B: ~0.5-1 token/sec
- Larger models: may require offloading

### CPU Only (Apple M1 Max)
- Mistral 7B: ~0.2-0.5 tokens/sec
- Larger models: not recommended

## Advanced Testing

### Custom prompts
```bash
# Multi-turn conversation
curl http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hi! How can I help?"},
      {"role": "user", "content": "What is 2+2?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }' | jq .
```

### Load testing
```bash
# Simple load test (requires 'ab' - Apache Bench)
ab -n 10 -c 1 \
  -p request.json \
  -T application/json \
  http://localhost:3000/v1/chat/completions

# Create request.json with your prompt first
echo '{
  "model": "mistral",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}' > request.json
```

## Next Steps

1. ✅ All tests passing? Great! You're ready to use it.
2. Try different models to find your sweet spot
3. Adjust temperature and max_tokens for your use case
4. Consider containerizing with Docker for reproducibility

For more info, see [README.md](README.md)
