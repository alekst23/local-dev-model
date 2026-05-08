# Dockerfile for Claude Ollama Proxy (Python + uv)
FROM python:3.11-alpine
WORKDIR /app
RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY README.md ./
COPY src ./src

RUN uv sync

EXPOSE 3000
CMD ["uv", "run", "ollama-proxy"]
