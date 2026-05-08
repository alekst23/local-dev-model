import json
from datetime import datetime
from typing import Any

import requests
from flask import Flask, Response, jsonify, request


def create_app(
    ollama_url: str,
    ollama_model: str,
) -> Flask:
    app = Flask(__name__)
    app.config["OLLAMA_URL"] = ollama_url
    app.config["OLLAMA_MODEL"] = ollama_model

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify(
            {
                "status": "ok",
                "model": app.config["OLLAMA_MODEL"],
                "ollama_url": app.config["OLLAMA_URL"],
            }
        )

    @app.route("/api/tags", methods=["GET"])
    def tags():
        try:
            response = requests.get(f"{app.config['OLLAMA_URL']}/api/tags", timeout=10)
            return jsonify(response.json())
        except Exception as err:
            return jsonify({"error": str(err)}), 503

    @app.route("/v1/models", methods=["GET"])
    def models():
        return jsonify(
            {
                "object": "list",
                "data": [
                    {
                        "id": app.config["OLLAMA_MODEL"],
                        "object": "model",
                        "owned_by": "ollama",
                        "permission": [],
                    }
                ],
            }
        )

    @app.route("/v1/chat/completions", methods=["POST"])
    def chat_completion():
        try:
            data = request.get_json(silent=True) or {}
            messages = data.get("messages", [])
            stream = data.get("stream", False)
            temperature = data.get("temperature", 0.7)
            max_tokens = data.get("max_tokens", 2048)

            prompt = _messages_to_prompt(messages)

            if stream:
                return _stream_ollama_response(
                    ollama_url=app.config["OLLAMA_URL"],
                    ollama_model=app.config["OLLAMA_MODEL"],
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            return _non_streaming_completion(
                ollama_url=app.config["OLLAMA_URL"],
                ollama_model=app.config["OLLAMA_MODEL"],
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as err:
            _log(f"chat completion error: {err}")
            return jsonify({"error": str(err)}), 500

    @app.route("/v1/messages", methods=["POST"])
    def anthropic_messages():
        """Anthropic Messages API endpoint — used by Claude Code CLI."""
        try:
            data = request.get_json(silent=True) or {}
            messages = data.get("messages", [])
            stream = data.get("stream", False)
            temperature = data.get("temperature", 0.7)
            max_tokens = data.get("max_tokens", 2048)

            prompt = _messages_to_prompt(messages)

            if stream:
                return _stream_anthropic_response(
                    ollama_url=app.config["OLLAMA_URL"],
                    ollama_model=app.config["OLLAMA_MODEL"],
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            return _non_streaming_anthropic_completion(
                ollama_url=app.config["OLLAMA_URL"],
                ollama_model=app.config["OLLAMA_MODEL"],
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as err:
            _log(f"anthropic messages error: {err}")
            return jsonify({"error": str(err)}), 500

    # Known Ollama passthrough paths
    OLLAMA_PATHS = {"api/tags", "api/generate", "api/chat", "api/show", "api/pull"}

    @app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    def proxy_other(path: str):
        if request.method == "OPTIONS":
            return ""

        # Only forward paths that Ollama actually handles; stub everything else
        if path in OLLAMA_PATHS or path.startswith("api/"):
            try:
                url = f"{app.config['OLLAMA_URL']}/{path}"
                if request.method == "GET":
                    resp = requests.get(url, timeout=10)
                elif request.method == "POST":
                    resp = requests.post(url, json=request.get_json(silent=True), timeout=10)
                else:
                    return jsonify({"error": "Method not supported"}), 405
                return resp.json(), resp.status_code
            except Exception as err:
                _log(f"proxy error: {err}")
                return jsonify({"error": str(err)}), 503

        # Stub out unknown Anthropic/Claude API paths so Claude Code doesn't get hard 404s
        _log(f"stubbed unknown path: {request.method} /{path}")
        return jsonify({"object": "list", "data": []}), 200

    return app


def _messages_to_prompt(messages: list[dict[str, Any]]) -> str:
    lines = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        speaker = "User" if role == "user" else "Assistant"
        lines.append(f"{speaker}: {content}")
    lines.append("Assistant:")
    return "\n".join(lines)


def _bound_max_tokens(max_tokens: int) -> int:
    try:
        requested = int(max_tokens)
    except (TypeError, ValueError):
        return 256
    return max(1, min(requested, 256))


def _non_streaming_completion(
    *,
    ollama_url: str,
    ollama_model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
):
    try:
        bounded_max_tokens = _bound_max_tokens(max_tokens)
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": bounded_max_tokens,
                },
            },
            timeout=300,
        )
        response.raise_for_status()
        ollama_response = response.json()
        assistant_text = ollama_response.get("response", "")

        payload = {
            "id": f"chatcmpl-{int(datetime.now().timestamp() * 1000)}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": ollama_model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": assistant_text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt) // 4,
                "completion_tokens": len(assistant_text) // 4,
                "total_tokens": (len(prompt) + len(assistant_text)) // 4,
            },
        }
        return jsonify(payload)
    except Exception as err:
        _log(f"non-streaming error: {err}")
        return jsonify({"error": str(err)}), 503


def _stream_ollama_response(
    *,
    ollama_url: str,
    ollama_model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
):
    def generate():
        try:
            bounded_max_tokens = _bound_max_tokens(max_tokens)
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "num_predict": bounded_max_tokens,
                    },
                },
                stream=True,
                timeout=300,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    json_data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                token = json_data.get("response")
                if token:
                    chunk = {
                        "choices": [
                            {
                                "delta": {"content": token},
                                "index": 0,
                            }
                        ]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as err:
            _log(f"streaming error: {err}")
            yield f"data: {json.dumps({'error': str(err)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


def _non_streaming_anthropic_completion(
    *,
    ollama_url: str,
    ollama_model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
):
    """Return a response shaped like Anthropic's Messages API."""
    try:
        bounded_max_tokens = _bound_max_tokens(max_tokens)
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": bounded_max_tokens,
                },
            },
            timeout=300,
        )
        response.raise_for_status()
        ollama_response = response.json()
        assistant_text = ollama_response.get("response", "")

        payload = {
            "id": f"msg_{int(datetime.now().timestamp() * 1000)}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": assistant_text}],
            "model": ollama_model,
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": len(prompt) // 4,
                "output_tokens": len(assistant_text) // 4,
            },
        }
        return jsonify(payload)
    except Exception as err:
        _log(f"anthropic non-streaming error: {err}")
        return jsonify({"error": str(err)}), 503


def _stream_anthropic_response(
    *,
    ollama_url: str,
    ollama_model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
):
    """Stream a response shaped like Anthropic's SSE format."""
    def generate():
        msg_id = f"msg_{int(datetime.now().timestamp() * 1000)}"
        output_tokens = 0
        # Opening events expected by Claude Code
        yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'content': [], 'model': ollama_model, 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"
        yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
        yield "event: ping\ndata: {\"type\": \"ping\"}\n\n"

        try:
            bounded_max_tokens = _bound_max_tokens(max_tokens)
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "num_predict": bounded_max_tokens,
                    },
                },
                stream=True,
                timeout=300,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    json_data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                token = json_data.get("response")
                if token:
                    output_tokens += max(1, len(token) // 4)
                    delta = {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": token}}
                    yield f"event: content_block_delta\ndata: {json.dumps(delta)}\n\n"

            yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
            yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': {'output_tokens': output_tokens}})}\n\n"
            yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"

        except Exception as err:
            _log(f"anthropic streaming error: {err}")
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': {'type': 'api_error', 'message': str(err)}})}\n\n"
            yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
            yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'error', 'stop_sequence': None}, 'usage': {'output_tokens': output_tokens}})}\n\n"
            yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


def _log(msg: str) -> None:
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] {msg}")
