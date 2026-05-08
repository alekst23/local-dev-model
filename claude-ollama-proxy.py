#!/usr/bin/env python3
"""
Claude CLI Proxy for Ollama (Python Version)

This proxy wraps Ollama's OpenAI-compatible API to work with Claude CLI.
It runs on port 3000 and translates requests to/from Ollama format.

Usage:
    python claude-ollama-proxy.py

Then configure Claude CLI:
    export CLAUDE_API_URL=http://localhost:3000
    export CLAUDE_API_KEY=local

Requirements:
    pip install flask requests
"""

import os
import json
import requests
from flask import Flask, request, jsonify, Response
from datetime import datetime
import sys

# Configuration
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'mistral')
PROXY_PORT = int(os.getenv('PROXY_PORT', 3000))

app = Flask(__name__)

# Logging helper
def log(msg):
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] {msg}")

log("🚀 Claude CLI Proxy for Ollama (Python)")
log(f"📡 Ollama URL: {OLLAMA_URL}")
log(f"🤖 Model: {OLLAMA_MODEL}")
log(f"🔌 Proxy running on: http://localhost:{PROXY_PORT}\n")

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'model': OLLAMA_MODEL,
        'ollama_url': OLLAMA_URL
    })

@app.route('/api/tags', methods=['GET'])
def tags():
    """Proxy Ollama tags endpoint"""
    try:
        response = requests.get(f'{OLLAMA_URL}/api/tags', timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 503

@app.route('/v1/models', methods=['GET'])
def models():
    """Claude API compatible models endpoint"""
    return jsonify({
        'object': 'list',
        'data': [
            {
                'id': OLLAMA_MODEL,
                'object': 'model',
                'owned_by': 'ollama',
                'permission': []
            }
        ]
    })

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completion():
    """Main chat completion endpoint"""
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        stream = data.get('stream', False)
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 2048)

        # Convert to prompt
        prompt = '\n'.join([
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in messages
        ]) + '\nAssistant:'

        if stream:
            return stream_ollama_response(prompt, temperature, max_tokens)
        else:
            return non_streaming_completion(prompt, temperature, max_tokens, data)

    except Exception as e:
        log(f"❌ Chat completion error: {e}")
        return jsonify({'error': str(e)}), 500

def non_streaming_completion(prompt, temperature, max_tokens, original_request):
    """Non-streaming chat completion"""
    try:
        response = requests.post(
            f'{OLLAMA_URL}/api/generate',
            json={
                'model': OLLAMA_MODEL,
                'prompt': prompt,
                'temperature': temperature,
                'num_predict': max_tokens,
                'stream': False
            },
            timeout=300
        )
        response.raise_for_status()
        ollama_response = response.json()

        return jsonify({
            'id': f'chatcmpl-{int(datetime.now().timestamp() * 1000)}',
            'object': 'chat.completion',
            'created': int(datetime.now().timestamp()),
            'model': OLLAMA_MODEL,
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': ollama_response.get('response', '')
                },
                'finish_reason': 'stop'
            }],
            'usage': {
                'prompt_tokens': len(prompt) // 4,
                'completion_tokens': len(ollama_response.get('response', '')) // 4,
                'total_tokens': (len(prompt) + len(ollama_response.get('response', ''))) // 4
            }
        })
    except Exception as e:
        log(f"❌ Non-streaming error: {e}")
        return jsonify({'error': str(e)}), 503

def stream_ollama_response(prompt, temperature, max_tokens):
    """Streaming chat completion"""
    def generate():
        try:
            response = requests.post(
                f'{OLLAMA_URL}/api/generate',
                json={
                    'model': OLLAMA_MODEL,
                    'prompt': prompt,
                    'temperature': temperature,
                    'num_predict': max_tokens,
                    'stream': True
                },
                stream=True,
                timeout=300
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    try:
                        json_data = json.loads(line)
                        if 'response' in json_data:
                            chunk = {
                                'choices': [{
                                    'delta': {'content': json_data['response']},
                                    'index': 0
                                }]
                            }
                            yield f'data: {json.dumps(chunk)}\n\n'
                    except json.JSONDecodeError:
                        pass

            yield 'data: [DONE]\n\n'

        except Exception as e:
            log(f"❌ Streaming error: {e}")
            yield f'data: {json.dumps({"error": str(e)})}\n\n'

    return Response(generate(), mimetype='text/event-stream')

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy_other(path):
    """Proxy other requests to Ollama"""
    try:
        method = request.method
        url = f'{OLLAMA_URL}/{path}'
        
        if method == 'OPTIONS':
            return ''
        
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=request.get_json(), timeout=10)
        else:
            return jsonify({'error': 'Method not supported'}), 405

        return response.json()

    except Exception as e:
        log(f"❌ Proxy error: {e}")
        return jsonify({'error': str(e)}), 503

if __name__ == '__main__':
    try:
        print(f"\n📝 Configure Claude CLI:\n")
        print(f"  export CLAUDE_API_URL=http://localhost:{PROXY_PORT}")
        print(f"  export CLAUDE_API_KEY=local\n")
        print("✅ Proxy starting...\n")
        
        app.run(host='localhost', port=PROXY_PORT, debug=False)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down proxy...")
        sys.exit(0)
