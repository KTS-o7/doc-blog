+++
title = "Freeseek: Turning DeepSeek's Web Chat into an OpenAI-Compatible API"
date = 2026-03-14T00:00:00+05:30
draft = false
math = false
+++

I wanted to use DeepSeek with tools that only speak OpenAI's API. DeepSeek's official API has rate limits and costs money. Their web chat is free and unrestricted but it isn't an API — it's a browser session with Cloudflare protection, Proof-of-Work challenges, and a proprietary SSE format.

So I built [freeseek-proxy](https://github.com/KTS-o7/freeseek-proxy): a local proxy that sits between OpenAI-compatible clients (opencode, Claude Code, any SDK) and DeepSeek's web chat backend. You send standard `/v1/chat/completions` requests; it handles sessions, PoW, TLS fingerprinting, and SSE translation behind the scenes.

This post covers the four hardest problems I had to solve.

## The architecture (it's two processes, not one)

The proxy is split into two halves that talk over localhost:

```
                  ┌──────────────────────────┐
                  │   Client                 │
                  │   (opencode / curl / SDK)│
                  └────────────┬─────────────┘
                               │
                  POST /v1/chat/completions
                       (OpenAI format)
                               │
                  ┌────────────▼─────────────┐
                  │   TypeScript Proxy       │
                  │   Hono on Bun :9123      │
                  │                          │
                  │   · Request normalization│
                  │   · Tool-call compat     │
                  │   · SSE reformatting     │
                  │   · Session management   │
                  └────────────┬─────────────┘
                               │
                    HTTP localhost:8081
                               │
                  ┌────────────▼─────────────┐
                  │   Python Backend         │
                  │   FastAPI + uvicorn      │
                  │                          │
                  │   · curl_cffi (TLS spoof)│
                  │   · WASM PoW solver      │
                  │   · Cookie management    │
                  │   · Auth (token / login) │
                  └────────────┬─────────────┘
                               │
                   HTTPS chat.deepseek.com
                               │
                  ┌────────────▼─────────────┐
                  │      DeepSeek API        │
                  └──────────────────────────┘
```

Why two languages? DeepSeek does browser fingerprinting. Their servers check TLS fingerprints, and if yours looks like `python-requests` or `node-fetch`, you get blocked. The Python side uses `curl_cffi` with `impersonate="chrome120"` to produce a TLS handshake indistinguishable from Chrome. The TypeScript side handles everything else — request translation, streaming, tool calls — where Bun's performance and type safety matter more.

## Problem 1: Proof-of-Work with a WASM SHA3 solver

DeepSeek doesn't just check your auth token. Before every chat completion, you must solve a Proof-of-Work challenge. The flow is:

1. Request a challenge from `/api/v0/chat/create_pow_challenge`
2. The server returns a challenge string, salt, difficulty, and expiry
3. You run a SHA3-based hash computation until you find a valid answer
4. Encode the answer as base64 JSON and send it as `x-ds-pow-response` header

The catch: DeepSeek's PoW algorithm is implemented in a WebAssembly module. In the browser, this runs natively. Outside the browser, you need a WASM runtime.

The solver uses `wasmtime` (a standalone WASM runtime for Python) to load DeepSeek's own `sha3_wasm_bg.wasm` binary and call its exported `wasm_solve` function:

```python
class DeepSeekHash:
    def init(self, wasm_path: str):
        engine = wasmtime.Engine()
        with open(wasm_path, "rb") as f:
            wasm_bytes = f.read()
        module = wasmtime.Module(engine, wasm_bytes)
        self.store = wasmtime.Store(engine)
        linker = wasmtime.Linker(engine)
        linker.define_wasi()
        self.instance = linker.instantiate(self.store, module)
        self.memory = self.instance.exports(self.store)["memory"]
        return self

    def calculate_hash(self, algorithm, challenge, salt, difficulty, expire_at):
        prefix = f"{salt}_{expire_at}_"
        # Allocate WASM memory, write challenge + prefix
        challenge_ptr, challenge_len = self._write_to_memory(challenge)
        prefix_ptr, prefix_len = self._write_to_memory(prefix)
        # Call the exported solver
        self.instance.exports(self.store)["wasm_solve"](
            self.store, retptr,
            challenge_ptr, challenge_len,
            prefix_ptr, prefix_len,
            float(difficulty),
        )
        # Read the answer from WASM memory
        value_bytes = bytes(memory_view[retptr + 8 : retptr + 16])
        value = np.frombuffer(value_bytes, dtype=np.float64)[0]
        return int(value)
```

The memory management is manual — you allocate via `__wbindgen_export_0`, write UTF-8 bytes one at a time, call the solver, then read the result from a return pointer. Stack pointer cleanup happens in a `finally` block. It's the kind of code where one off-by-one error means silent corruption.

**Why Python 3.11 specifically?** The `wasmtime` + `numpy` + `curl_cffi` stack was verified working on 3.11. Python 3.14 caused silent failures in the WASM path during testing — the process would get `killed` mid-computation with no error message. This isn't a "should work" situation; it's a "was tested and doesn't" situation.

## Problem 2: TLS fingerprinting and Cloudflare

DeepSeek sits behind Cloudflare. Standard HTTP clients get 403s or "Just a moment..." challenge pages because their TLS Client Hello doesn't match what a real browser sends.

The fix is `curl_cffi` with browser impersonation:

```python
response = requests.post(
    f"{BASE_URL}{path}",
    headers=headers,
    json=body,
    cookies=cookies,
    impersonate="chrome120",  # TLS fingerprint matches Chrome 120
    stream=stream,
)
```

`impersonate="chrome120"` makes the TLS handshake (cipher suites, extensions, ALPN) identical to Chrome 120. This is why the backend is Python, not Node — there's no equivalent library in the JS ecosystem that matches real browser TLS fingerprints this precisely.

The cookie management layer adds another defense: if a request hits Cloudflare anyway, the proxy can automatically refresh cookies via a configurable shell command:

```python
def refresh_cookies(self) -> dict[str, str]:
    if not self.refresh_command:
        return self.load_cookies()
    subprocess.run(self.refresh_command, shell=True, check=True)
    cookies = self.load_cookies()
    self.save_cookies(cookies)
    return cookies
```

This lets you plug in whatever cookie extraction tool you prefer — a headless browser script, a browser extension export, etc.

## Problem 3: Translating SSE formats 

DeepSeek's streaming format is not OpenAI's streaming format. Both use Server-Sent Events, but the payload structure is completely different.

**OpenAI format** (what clients expect):
```json
data: {"choices":[{"delta":{"content":"Hello"},"index":0}],"model":"gpt-4"}
```

**DeepSeek format** (what the server sends):
```json
data: {"v":{"response":{"fragments":[{"type":"text","content":"Hello"}]}},"o":"APPEND"}
```

DeepSeek uses a nested structure where content lives inside `response.fragments`, operations can be `APPEND`, `SET`, or `BATCH`, and thinking content is separated from regular content by fragment type. There's also metadata like `response/status` and `response/accumulated_token_usage` mixed into the stream that clients don't want.

The proxy handles this translation in `parseSSELine` and `extractDeepSeekContent`:

```typescript
function extractDeepSeekContent(
  data: DeepSeekSSEData,
  includeThinking: boolean
): string {
  // DeepSeek nests content in multiple possible locations
  const target = data.v?.response ?? data.response ?? data;
  const fragments = target?.fragments;

  if (Array.isArray(fragments)) {
    return fragments
      .filter(f => includeThinking || f.type !== "thinking")
      .map(f => f.content)
      .join("");
  }

  // Fallback: direct content field
  if (typeof data.v === "string") return data.v;
  if (typeof data.content === "string") return data.content;
  return "";
}
```

For streaming responses, each DeepSeek SSE chunk gets translated into an OpenAI `chat.completion.chunk` on the fly. For non-streaming, the proxy accumulates all chunks, then builds a single `chat.completion` response.

## Problem 4: Tool calls on a model that doesn't support them

This is the most interesting problem. DeepSeek's web chat API doesn't support OpenAI-style tool calls. There's no `tools` parameter, no `tool_choice`, no `tool_calls` in the response. But clients like opencode and Claude Code rely heavily on tool use — without it, the agent can't read files, run commands, or interact with your codebase.

The solution is a prompt-engineering compatibility layer. When the proxy detects tool-related fields in the request, it:

1. **Injects a system prompt** describing available tools and the expected JSON format
2. **Flattens the conversation** into a single prompt (including tool results from previous turns)
3. **Parses the model's response** for JSON tool call envelopes
4. **Translates back** into OpenAI's `tool_calls` format

The injected system prompt instructs the model to output tool calls as JSON:

```typescript
function buildToolSystemPrompt(tools, toolChoice) {
  return [
    "You are replying through an OpenAI-compatible proxy that supports tool use.",
    toolChoiceRule, // varies by mode: auto/required/none/function
    `If you decide to call a tool, output only valid JSON with this exact shape:`,
    `{"opencode_tool_call": {"name": "tool_name", "arguments": { ... }}}.`,
    `For multiple calls: {"opencode_tool_calls": [...]}.`,
    "Do not wrap the JSON in markdown.",
    "Available tools:",
    availableTools, // name, description, JSON schema for each
  ].join("\n\n");
}
```

The conversation history gets flattened because DeepSeek's chat API takes a single prompt string, not an array of messages:

```typescript
function formatConversationForDeepSeek(messages) {
  return messages.map(message => {
    if (message.role === "system") return `System: ${content}`;
    if (message.role === "user") return `User: ${content}`;
    if (message.role === "assistant") {
      if (message.tool_calls?.length)
        return `Assistant tool request: ${formatted calls}`;
      return `Assistant: ${content}`;
    }
    if (message.role === "tool")
      return `Tool (${message.tool_call_id}) result: ${content}`;
  }).join("\n\n");
}
```

On the response side, `parseToolEnvelope` scans the model output for JSON objects containing `opencode_tool_call` or `opencode_tool_calls` keys, validates that the function names match known tools, and converts them into proper OpenAI `tool_calls` with generated IDs:

```typescript
function parseToolEnvelope(text, tools) {
  for (const candidate of extractJsonObjectCandidates(text.trim())) {
    const payload = JSON.parse(candidate);
    const rawCalls = payload.opencode_tool_calls ?? [payload.opencode_tool_call];
    const toolCalls = rawCalls
      .filter(call => tools.some(t => t.function.name === call.name))
      .map(call => ({
        id: `call_${uuidv4()}`,
        type: "function",
        function: { name: call.name, arguments: JSON.stringify(call.arguments) },
      }));
    if (toolCalls.length) return { toolCalls };
  }
  return null;
}
```

The JSON extraction is deliberately robust — it uses a bracket-depth parser to find JSON objects embedded in natural language, handles escaped strings, and tries multiple candidates. This matters because the model sometimes wraps tool calls in explanatory text despite being told not to.

For streaming with tools, there's an extra step. The proxy can't stream tool calls token-by-token (the client needs the complete tool call object). So when tools are present, the proxy collects the full response first, parses tool calls, then re-streams the result as a synthetic SSE sequence. This adds ~latency but is the only correct approach.

## What the client sees

After all this translation, what comes out the other end is a standard OpenAI response:

```bash
curl http://localhost:9123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

```
data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","choices":[{"delta":{"role":"assistant"},"index":0}]}
data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","choices":[{"delta":{"content":"Hello"},"index":0}]}
data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","choices":[{"delta":{"content":"!"},"index":0}]}
data: [DONE]
```

Indistinguishable from OpenAI. Any client that speaks the OpenAI protocol works without modification.

## What I learned

### WASM outside the browser is viable but fragile

The `wasmtime` runtime works, but debugging WASM memory issues from Python is miserable. There's no stack trace when you read the wrong offset — you just get garbage bytes. The debug flags in `pow.py` exist because I needed them.

### TLS fingerprinting is the real gate, not auth tokens

I initially thought the hard part would be authentication. It wasn't. The hard part was making HTTP requests that don't get blocked. `curl_cffi` with browser impersonation is the only reliable solution I found for Python. If you're building any kind of web scraper or API proxy in 2026, TLS fingerprinting is the first problem you'll hit.

### Tool call compatibility via prompting is surprisingly reliable

I expected the prompt-engineering approach to tool calls to be flaky. It's not. DeepSeek's models are good at following structured output instructions, and the JSON extraction parser handles edge cases well. The key is being very explicit about the expected format and validating against the known tool list.

### Two-process architecture was the right call

Splitting into TypeScript + Python felt like overengineering at first. It wasn't. Each language does what it's best at: Python for the "pretend to be a browser" parts (TLS, WASM), TypeScript for the "translate between API formats" parts (streaming, types, request handling). Trying to do both in one language would have meant worse tooling for at least half the problem.

## Links

- **Repo**: [freeseek-proxy](https://github.com/KTS-o7/freeseek-proxy)
- **curl_cffi**: [docs](https://curl-cffi.readthedocs.io/) — Python HTTP client with browser TLS impersonation
- **wasmtime-py**: [GitHub](https://github.com/bytecodealliance/wasmtime-py) — Python bindings for the Wasmtime WASM runtime
- **Hono**: [hono.dev](https://hono.dev/) — Lightweight web framework for Bun/Node/Deno
