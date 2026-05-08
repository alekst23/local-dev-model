import argparse
import os
import sys

from .app import create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ollama-proxy",
        description="Run a local proxy that maps chat completions to Ollama.",
    )
    parser.add_argument("--host", default=os.getenv("PROXY_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PROXY_PORT", "3000")))
    parser.add_argument(
        "--ollama-url",
        default=os.getenv("OLLAMA_URL", "http://localhost:11434"),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OLLAMA_MODEL", "mistral"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = create_app(ollama_url=args.ollama_url, ollama_model=args.model)

    print("Starting Ollama proxy")
    print(f"Ollama URL: {args.ollama_url}")
    print(f"Model: {args.model}")
    print(f"Proxy URL: http://{args.host}:{args.port}")
    print("")
    print("Configure Claude Code / Claude CLI:")
    print(f"  export ANTHROPIC_BASE_URL=http://{args.host}:{args.port}")
    print("  export ANTHROPIC_API_KEY=local")
    print("")

    try:
        app.run(host=args.host, port=args.port, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down proxy")
        sys.exit(0)
