#!/usr/bin/env node
/**
 * Claude CLI Proxy for Ollama
 * 
 * This proxy wraps Ollama's OpenAI-compatible API to work with Claude CLI.
 * It runs on port 3000 and translates requests to/from Ollama format.
 * 
 * Usage:
 *   node claude-ollama-proxy.js
 * 
 * Then configure Claude CLI:
 *   export CLAUDE_API_URL=http://localhost:3000
 *   export CLAUDE_API_KEY=local
 */

const http = require('http');
const https = require('https');
const url = require('url');

const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434';
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || 'mistral';
const PROXY_PORT = process.env.PROXY_PORT || 3000;

console.log(`🚀 Claude CLI Proxy for Ollama`);
console.log(`📡 Ollama URL: ${OLLAMA_URL}`);
console.log(`🤖 Model: ${OLLAMA_MODEL}`);
console.log(`🔌 Proxy running on: http://localhost:${PROXY_PORT}`);
console.log(`\n📝 Configure Claude CLI:\n`);
console.log(`  export CLAUDE_API_URL=http://localhost:${PROXY_PORT}`);
console.log(`  export CLAUDE_API_KEY=local\n`);

const server = http.createServer(async (req, res) => {
  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  const pathname = url.parse(req.url).pathname;
  const query = url.parse(req.url, true).query;

  console.log(`[${new Date().toISOString()}] ${req.method} ${pathname}`);

  // Health check
  if (pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', model: OLLAMA_MODEL }));
    return;
  }

  // Ollama API endpoints
  if (pathname === '/api/tags') {
    return forwardToOllama(req, res, '/api/tags');
  }

  // Claude API compatibility
  if (pathname === '/v1/models') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      object: 'list',
      data: [
        {
          id: OLLAMA_MODEL,
          object: 'model',
          owned_by: 'ollama',
          permission: []
        }
      ]
    }));
    return;
  }

  // Chat completion endpoint
  if (pathname === '/v1/chat/completions') {
    return handleChatCompletion(req, res);
  }

  // Fallback: try to forward to Ollama
  forwardToOllama(req, res, pathname);
});

function forwardToOllama(req, res, pathname) {
  let body = '';
  
  req.on('data', chunk => {
    body += chunk.toString();
  });

  req.on('end', async () => {
    try {
      const ollamaUrl = `${OLLAMA_URL}${pathname}`;
      const requestOptions = {
        hostname: new URL(ollamaUrl).hostname,
        port: new URL(ollamaUrl).port || 11434,
        path: new URL(ollamaUrl).pathname + (new URL(ollamaUrl).search || ''),
        method: req.method,
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body)
        }
      };

      const protocol = ollamaUrl.startsWith('https') ? https : http;
      const ollamaReq = protocol.request(requestOptions, (ollamaRes) => {
        res.writeHead(ollamaRes.statusCode, ollamaRes.headers);
        ollamaRes.pipe(res);
      });

      ollamaReq.on('error', (err) => {
        console.error('Ollama error:', err.message);
        res.writeHead(503, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Ollama service unavailable: ' + err.message }));
      });

      if (body) {
        ollamaReq.write(body);
      }
      ollamaReq.end();
    } catch (err) {
      console.error('Proxy error:', err);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    }
  });
}

function handleChatCompletion(req, res) {
  let body = '';

  req.on('data', chunk => {
    body += chunk.toString();
  });

  req.on('end', async () => {
    try {
      const request = JSON.parse(body);
      const messages = request.messages || [];
      const stream = request.stream || false;
      const temperature = request.temperature || 0.7;

      // Convert Claude chat format to Ollama prompt
      const prompt = messages
        .map(m => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`)
        .join('\n') + '\nAssistant:';

      if (stream) {
        // Streaming response
        res.writeHead(200, {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive'
        });

        await streamOllamaResponse(req, res, prompt, temperature);
      } else {
        // Non-streaming response
        const ollamaResponse = await callOllama(prompt, temperature);
        
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          id: `chatcmpl-${Date.now()}`,
          object: 'chat.completion',
          created: Math.floor(Date.now() / 1000),
          model: OLLAMA_MODEL,
          choices: [
            {
              index: 0,
              message: {
                role: 'assistant',
                content: ollamaResponse.response
              },
              finish_reason: 'stop'
            }
          ],
          usage: {
            prompt_tokens: request.messages.join('').length / 4,
            completion_tokens: ollamaResponse.response.length / 4,
            total_tokens: (request.messages.join('').length + ollamaResponse.response.length) / 4
          }
        }));
      }
    } catch (err) {
      console.error('Chat completion error:', err);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    }
  });
}

function callOllama(prompt, temperature) {
  return new Promise((resolve, reject) => {
    const requestBody = JSON.stringify({
      model: OLLAMA_MODEL,
      prompt: prompt,
      temperature: temperature,
      stream: false
    });

    const requestOptions = {
      hostname: new URL(OLLAMA_URL).hostname,
      port: new URL(OLLAMA_URL).port || 11434,
      path: '/api/generate',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(requestBody)
      }
    };

    const protocol = OLLAMA_URL.startsWith('https') ? https : http;
    const ollamaReq = protocol.request(requestOptions, (ollamaRes) => {
      let data = '';
      ollamaRes.on('data', chunk => data += chunk);
      ollamaRes.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error('Invalid Ollama response: ' + data));
        }
      });
    });

    ollamaReq.on('error', reject);
    ollamaReq.write(requestBody);
    ollamaReq.end();
  });
}

function streamOllamaResponse(req, res, prompt, temperature) {
  return new Promise((resolve) => {
    const requestBody = JSON.stringify({
      model: OLLAMA_MODEL,
      prompt: prompt,
      temperature: temperature,
      stream: true
    });

    const requestOptions = {
      hostname: new URL(OLLAMA_URL).hostname,
      port: new URL(OLLAMA_URL).port || 11434,
      path: '/api/generate',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(requestBody)
      }
    };

    const protocol = OLLAMA_URL.startsWith('https') ? https : http;
    const ollamaReq = protocol.request(requestOptions, (ollamaRes) => {
      let buffer = '';

      ollamaRes.on('data', (chunk) => {
        buffer += chunk.toString();
        const lines = buffer.split('\n');
        buffer = lines.pop();

        lines.forEach(line => {
          if (line.trim()) {
            try {
              const json = JSON.parse(line);
              if (json.response) {
                res.write(`data: ${JSON.stringify({
                  choices: [{
                    delta: { content: json.response },
                    index: 0
                  }]
                })}\n\n`);
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        });
      });

      ollamaRes.on('end', () => {
        res.write('data: [DONE]\n\n');
        res.end();
        resolve();
      });
    });

    ollamaReq.on('error', (err) => {
      res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
      res.end();
      resolve();
    });

    ollamaReq.write(requestBody);
    ollamaReq.end();
  });
}

server.listen(PROXY_PORT, () => {
  console.log(`✅ Proxy listening on http://localhost:${PROXY_PORT}`);
  console.log(`\nMaking requests to Ollama at ${OLLAMA_URL}\n`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n\n👋 Shutting down proxy...');
  server.close();
  process.exit(0);
});
