# Troubleshooting Guide

## Common Issues and Solutions

### 1. Ollama Service Won't Start

**Problem:** `ollama serve` gives errors or won't run

**Solutions:**
```bash
# Check if port 11434 is already in use
lsof -i :11434
# Or on Windows: netstat -ano | findstr :11434

# Kill process using that port (if safe)
kill -9 <PID>  # Linux/macOS
taskkill /PID <PID> /F  # Windows

# Try running without GPU (fallback to CPU)
OLLAMA_DEBUG=1 ollama serve

# Check logs for GPU issues
# On macOS: check System Preferences → General → About (GPU info)
# On Linux: nvidia-smi or rocm-smi
```

### 2. Model Download Fails or is Very Slow

**Problem:** `ollama pull mistral` doesn't complete or is stuck

**Solutions:**
```bash
# Try with debug output
OLLAMA_DEBUG=1 ollama pull mistral

# Check disk space
df -h  # Linux/macOS
wmic logicaldisk get name,size,freespace  # Windows

# Try pulling a smaller model first
ollama pull neural-chat  # 7B, faster to test

# Set custom download location
export OLLAMA_MODELS=/path/to/custom/location
ollama pull mistral
```

### 3. GPU Not Being Used (Slow Generation)

**Problem:** Model generating slowly, GPU idle

**NVIDIA Solution:**
```bash
# Verify CUDA is installed
nvidia-smi
# Should show GPU info and CUDA version

# Force CUDA usage
export CUDA_VISIBLE_DEVICES=0
ollama serve

# Check if CUDA is properly installed
nvcc --version

# Install NVIDIA CUDA if missing:
# Ubuntu: sudo apt install nvidia-cuda-toolkit
# Fedora: sudo dnf install cuda-toolkit
```

**AMD (ROCm) Solution:**
```bash
# Check ROCm installation
rocm-smi

# Install ROCm if missing:
# Ubuntu: https://rocmdocs.amd.com/en/latest/deploy/linux/index.html

# Force ROCm usage
export HIP_VISIBLE_DEVICES=0
ollama serve
```

**Apple Silicon (M1/M2/M3) Solution:**
```bash
# Should work out of the box on Metal
# If slow, check Activity Monitor for GPU usage

# Force Metal GPU usage
# Already default on Apple Silicon

# If still CPU-bound, check:
# - Available RAM
# - Close other applications
# - Model size (try 7B models)
```

**CPU-Only (Fallback):**
```bash
# Works on all systems, but slower
# Usually auto-selected if GPU unavailable

# Optimize for CPU
# - Use smaller models (mistral 7B, neural-chat 7B)
# - Close other applications
# - Increase timeout/patience
```

### 4. "Connection refused" on Port 11434

**Problem:** `curl http://localhost:11434/api/tags` fails

**Solutions:**
```bash
# Check if Ollama is running
ps aux | grep ollama
# or on Windows: tasklist | findstr ollama

# If not running, start it
ollama serve

# If running but still fails, check binding
# Look in Ollama logs for "listening on"
# Default is 127.0.0.1:11434

# Try connecting from localhost specifically
curl http://127.0.0.1:11434/api/tags

# If network issue, try allowing network access
# May need firewall rule on some systems
```

### 5. Proxy Can't Connect to Ollama

**Problem:** Python/Node proxy starts but shows Ollama connection errors

**Solutions:**
```bash
# Check proxy logs for exact error
# Restart proxy with debug logging
UV_LOG_CONTEXT=1 uv run ollama-proxy

# Verify Ollama is running and accessible
curl http://localhost:11434/api/tags

# Check if OLLAMA_URL environment variable is correct
echo $OLLAMA_URL
# Should be: http://localhost:11434

# Try explicit URL
OLLAMA_URL=http://127.0.0.1:11434 uv run ollama-proxy

# If using Docker, Ollama URL should be http://ollama:11434
# (the service name, not localhost)
```

### 6. Claude CLI Can't Connect to Proxy

**Problem:** `claude "Hello"` hangs or shows connection error

**Solutions:**
```bash
# Verify proxy is running
curl http://localhost:3000/health

# Should return: {"status": "ok", "model": "mistral", ...}

# Check environment variables
echo $ANTHROPIC_BASE_URL
echo $ANTHROPIC_API_KEY
# Should be: http://localhost:3000 and local

# Set them if not set
export ANTHROPIC_BASE_URL=http://localhost:3000
export ANTHROPIC_API_KEY=local

# Test with curl
curl http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral","messages":[{"role":"user","content":"hi"}]}'

# If hangs, proxy may not be processing requests
# Check proxy logs and restart it
```

### 7. Out of Memory (OOM) Errors

**Problem:** Model crashes with "out of memory" after starting

**Solutions:**
```bash
# Check available GPU memory
nvidia-smi  # NVIDIA
rocm-smi    # AMD
free -h     # System RAM

# Use smaller model
ollama pull mistral  # 7B is ~5GB
# Instead of:
ollama pull dolphin-mixtral  # 48GB+

# Run with fewer layers on GPU
# Edit model loading (advanced)
# Usually not needed with smaller models

# For CPU, increase swap space
# Linux: sudo fallocate -l 16G /swapfile

# Monitor during generation
watch nvidia-smi  # Keep tab open while generating
```

### 8. Port Already in Use

**Problem:** "Address already in use" error

**For Port 11434 (Ollama):**
```bash
# Find process using port
lsof -i :11434

# Kill it (if safe)
kill -9 <PID>

# Or use different port
export OLLAMA_HOST=127.0.0.1:11435
ollama serve

# Then update proxy config
export OLLAMA_URL=http://localhost:11435
uv run ollama-proxy
```

**For Port 3000 (Proxy):**
```bash
# Find process
lsof -i :3000

# Kill it
kill -9 <PID>

# Or use different port
export PROXY_PORT=3001
uv run ollama-proxy

# Update Claude Code CLI config
export ANTHROPIC_BASE_URL=http://localhost:3001
```

### 9. Model Takes Too Long to Load/Generate

**Problem:** First response takes minutes

**Causes and Solutions:**
```bash
# First generation loads model (normal, can be slow)
# Subsequent generations should be faster

# If consistently slow:

# 1. Check GPU usage during generation
watch -n 0.1 nvidia-smi  # Check Processes section

# 2. Switch to smaller model
ollama pull mistral

# 3. Check available VRAM
nvidia-smi

# 4. Close other GPU applications
# - Chrome/Firefox with GPU rendering
# - Video editing software
# - Game launchers
# - Other AI tools

# 5. Try CPU mode to diagnose
# If still slow on CPU, model is normal speed

# 6. Monitor temperature
watch sensors  # Linux

# 7. Check system load
top  # or 'htop' if installed
```

### 10. Proxy Shows No Error But Returns Empty Response

**Problem:** Claude CLI works but gets no response from model

**Solutions:**
```bash
# Test model directly
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Hello",
  "stream": false
}'

# Check if model is actually loaded
ollama list
ollama show mistral

# Verify model file exists and isn't corrupted
# Location typically:
# - Linux: ~/.ollama/models
# - macOS: ~/.ollama/models
# - Windows: %USERPROFILE%\.ollama\models

# Try pulling model again
ollama pull mistral --insecure

# Check proxy logs for specific errors
# Look for JSON parsing or streaming issues
```

## Performance Optimization

### For GPU Users

```bash
# Monitor during operation
watch -n 1 nvidia-smi

# Look for:
# - GPU-Util should be 90%+
# - Memory-Usage should be 80%+ of allocated
# - Process section should show ollama

# If GPU-Util is low:
# 1. Model might not fit on GPU (use smaller)
# 2. CPU bottleneck (less common)
# 3. Network/I/O bottleneck (rare)
```

### For CPU Users

```bash
# Monitor with top
top

# Look for:
# - ollama process using 80%+ CPU
# - If lower, model may be I/O bound

# Optimization:
# - Close other apps
# - Use smaller 7B models, not 70B
# - Increase RAM if swapping occurs
```

## Getting Help

If issues persist:

1. **Check Ollama documentation:** https://github.com/ollama/ollama
2. **Check Claude CLI docs:** https://claude.ai/cli
3. **Check proxy logs:** Enable debug mode and save output
4. **Collect system info:**
   ```bash
   # On Linux/macOS
   uname -a
   nvidia-smi  # or rocm-smi, or skip if CPU-only
   free -h
   df -h
   
   # On Windows
   systeminfo
   wmic os get osarchitecture
   ```
5. **Share logs when reporting issues**

## Quick Checklist for Fresh Start

```bash
☐ Ollama installed and running (ollama serve)
☐ Model pulled (ollama pull mistral)
☐ API accessible (curl http://localhost:11434/api/tags)
☐ Proxy running (uv run ollama-proxy)
☐ Proxy accessible (curl http://localhost:3000/health)
☐ Claude CLI installed
☐ Environment variables set:
  ☐ export ANTHROPIC_BASE_URL=http://localhost:3000
  ☐ export ANTHROPIC_API_KEY=local
☐ Test with claude command
```

If all checks pass but issues remain, check the specific error logs.
