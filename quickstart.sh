#!/bin/bash
# Quick-start script for local LLM development
# This script helps you set up Ollama and test it with Claude CLI

set -e

echo "🚀 Local LLM Development Quick Start"
echo "===================================="
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama is not installed${NC}"
    echo ""
    echo "Install it from: https://ollama.ai"
    echo ""
    echo "Quick install (macOS):"
    echo "  brew install ollama"
    echo ""
    echo "Quick install (Linux):"
    echo "  curl -fsSL https://ollama.ai/install.sh | sh"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓${NC} Ollama is installed"

# Check if Ollama service is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Ollama service is not running${NC}"
    echo ""
    echo "Start it with:"
    echo "  ollama serve"
    echo ""
    echo "In a new terminal, come back to this script once Ollama is running."
    exit 1
fi

echo -e "${GREEN}✓${NC} Ollama service is running on localhost:11434"
echo ""

# Get list of models
echo -e "${BLUE}📦 Available models:${NC}"
ollama list
echo ""

# Ask user which model to use
read -p "Which model should we use? (default: mistral): " MODEL
MODEL=${MODEL:-mistral}

echo ""
echo -e "${BLUE}🤖 Checking if $MODEL is installed...${NC}"
if ! ollama list | grep -q "^$MODEL"; then
    echo -e "${YELLOW}Pulling $MODEL (this may take a few minutes)...${NC}"
    ollama pull "$MODEL"
fi

echo -e "${GREEN}✓${NC} Model '$MODEL' is ready"
echo ""

# Test the model
echo -e "${BLUE}🧪 Testing model with a simple prompt...${NC}"
RESPONSE=$(curl -s http://localhost:11434/api/generate -d "{
  \"model\": \"$MODEL\",
  \"prompt\": \"What is 2+2?\",
  \"stream\": false
}" | grep -o '"response":"[^"]*' | cut -d'"' -f4)

echo "Response: $RESPONSE"
echo -e "${GREEN}✓${NC} Model is working!"
echo ""

# Check for Claude CLI
if ! command -v claude &> /dev/null; then
    echo -e "${YELLOW}⚠️  Claude CLI is not installed${NC}"
    echo ""
    echo "Install it with:"
    echo "  npm install -g claude-cli"
    echo "  # or for Python:"
    echo "  pip install claude-cli"
    echo ""
fi

# Create .env file
echo -e "${BLUE}📝 Creating configuration files...${NC}"

cat > .env << EOF
# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=$MODEL
PROXY_PORT=3000
EOF

echo -e "${GREEN}✓${NC} Created .env file"

# Create a run script
cat > run-proxy.sh << 'EOF'
#!/bin/bash
# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

echo "🚀 Starting Claude Ollama Proxy"
echo "Model: $OLLAMA_MODEL"
echo ""
echo "Configure Claude CLI with:"
echo "  export CLAUDE_API_URL=http://localhost:3000"
echo "  export CLAUDE_API_KEY=local"
echo ""

# Determine which proxy to run
if command -v node &> /dev/null; then
    echo "Using Node.js proxy..."
    node claude-ollama-proxy.js
elif command -v python3 &> /dev/null; then
    echo "Using Python proxy..."
    python3 claude-ollama-proxy.py
else
    echo "Error: Neither Node.js nor Python 3 found!"
    exit 1
fi
EOF

chmod +x run-proxy.sh
echo -e "${GREEN}✓${NC} Created run-proxy.sh"

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}✅ Setup complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1️⃣  Start the proxy in one terminal:"
echo "   ./run-proxy.sh"
echo ""
echo "2️⃣  In another terminal, configure Claude CLI:"
echo "   export CLAUDE_API_URL=http://localhost:3000"
echo "   export CLAUDE_API_KEY=local"
echo ""
echo "3️⃣  Test it:"
echo "   claude 'What is machine learning?'"
echo ""
echo "📚 For more information, see README.md"
echo ""
