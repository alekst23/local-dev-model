# Dockerfile for Claude Ollama Proxy

# Build stage for Node.js proxy
FROM node:18-alpine as node-proxy
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY claude-ollama-proxy.js .
EXPOSE 3000
CMD ["node", "claude-ollama-proxy.js"]

# Runtime stage with Python proxy option
FROM python:3.11-alpine as python-proxy
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY claude-ollama-proxy.py .
EXPOSE 3000
CMD ["python3", "claude-ollama-proxy.py"]

# Default to Node.js proxy
FROM node-proxy as final
