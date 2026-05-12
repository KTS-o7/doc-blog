+++
title = "Fixing Silent $0 Streaming Costs in AgentBudget: An OSS Contribution"
date = 2026-04-16T00:00:00+05:30
draft = false
math = false
+++

AgentBudget patches the OpenAI and Anthropic SDKs to track the cost of every LLM call. Set a budget, get a hard limit. Simple premise.

Except there was a gap. Every streaming call cost $0.00 in the ledger. Silently. No error, no warning -- just wrong numbers.

I found the gap, fixed it, and got the PR merged. This is the story of how streaming cost tracking actually works.

## What AgentBudget does

AgentBudget is an open-source SDK that puts a hard dollar limit on AI agent sessions. Two lines, no infrastructure:

```python
import agentbudget
agentbudget.init("$5.00")
```

It works by monkey-patching `Completions.create` (OpenAI) and `Messages.create` (Anthropic) at init time. Every call goes through a wrapper that looks up the model cost, accumulates spend, and raises `BudgetExhausted` when the limit is hit.

The non-streaming path worked fine. The streaming path did not.

## The bug

When `stream=True`, the patched method receives a `Stream` object back from the SDK -- not a completed response with token counts. The original code had no handling for this case. It silently passed the stream through untracked.

Every streaming call registered as $0.00 in the ledger. Any agent using streaming could blow past its budget with zero resistance. The circuit breaker was blind to half its traffic.

## Why streaming is harder to cost

Non-streaming is straightforward: the response comes back with a `usage` object containing `prompt_tokens` and `completion_tokens`. Multiply by the per-token rate, done.

Streaming returns a sequence of chunks. Token counts are not available upfront -- they only appear after the stream is exhausted. For OpenAI specifically, usage data on the final chunk is opt-in: you need `stream_options={"include_usage": True}` in the request, otherwise the final chunk carries no usage data and there is nothing to cost.

Anthropic handles it differently. Usage data is always present, split across two events: `message_start` carries input tokens, `message_delta` carries output tokens at the end.

## The fix: transparent wrapper classes

The solution is four wrapper classes that intercept the stream, yield every chunk unchanged, and record cost after the iterator is exhausted:

| Class | Wraps |
|---|---|
| `_OpenAIStreamWrapper` | `openai.Stream[ChatCompletionChunk]` |
| `_AsyncOpenAIStreamWrapper` | `openai.AsyncStream[ChatCompletionChunk]` |
| `_AnthropicStreamWrapper` | `anthropic.Stream[RawMessageStreamEvent]` |
| `_AsyncAnthropicStreamWrapper` | `anthropic.AsyncStream[RawMessageStreamEvent]` |

Each wrapper is fully transparent to the caller. The existing code pattern -- `for chunk in stream:` or `async for chunk in stream:` or `with client.stream(...) as stream:` -- continues to work without any changes.

The wrapper accumulates token counts as chunks arrive, then records the cost in the session ledger once the stream ends.

For OpenAI:

```python
class _OpenAIStreamWrapper:
    def __init__(self, stream, session, model):
        self._stream = stream
        self._session = session
        self._model = model

    def __iter__(self):
        for chunk in self._stream:
            # Track usage from the final chunk
            if chunk.usage:
                cost = price(self._model, chunk.usage)
                self._session.record(cost)
            yield chunk

    # Full protocol: __enter__, __exit__, close()
```

For Anthropic, the accumulation spans two event types:

```python
class _AnthropicStreamWrapper:
    def __iter__(self):
        input_tokens = 0
        output_tokens = 0
        for event in self._stream:
            if event.type == "message_start":
                input_tokens = event.message.usage.input_tokens
            elif event.type == "message_delta":
                output_tokens = event.usage.output_tokens
            yield event
        cost = price(self._model, input_tokens, output_tokens)
        self._session.record(cost)
```

The detection of whether a response is a stream happens via `isinstance` checks guarded by `ImportError`, so the wrapper degrades gracefully if only one SDK is installed.

## Implementing the full protocol

The tricky part is not the cost tracking logic -- it is making the wrapper implement the full stream protocol correctly.

Python streams support multiple usage patterns: iterator (`for chunk in stream`), context manager (`with stream`), async iterator, async context manager, and explicit `close()`/`aclose()`. Missing any of these means certain callers will break with an `AttributeError` or a resource leak.

The wrapper needs to implement all of them:

```python
# Sync: iterator + context manager + close
def __iter__(self): ...
def __enter__(self): return self
def __exit__(self, *args): self.close()
def close(self): self._stream.close()

# Async: async iterator + async context manager + aclose
async def __aiter__(self): ...
async def __aenter__(self): return self
async def __aexit__(self, *args): await self.aclose()
async def aclose(self): await self._stream.aclose()
```

Getting this wrong is invisible in unit tests with mocks but breaks immediately against real SDK objects.

## Tests

The PR added 19 tests covering:

- Cost recorded correctly after stream exhaustion
- Chunks with no usage data skipped without error
- Passthrough identity -- every chunk the caller sees is unchanged
- `BudgetExhausted` propagates correctly mid-stream
- Both `for chunk in stream:` and `with client.stream() as stream:` patterns
- `close()` and `aclose()` delegation to the underlying stream
- Drop-in mode (`agentbudget.init()`) wrapping end-to-end
- No-session noop -- if no budget session is active, streaming is fully transparent

All 129 pre-existing tests continued to pass. 148 total passing at merge.

## The known limitation

OpenAI streaming requires the caller to pass `stream_options={"include_usage": True}`. Without it, the final chunk carries no usage data, and the cost is silently $0.

This is OpenAI's API behaviour -- usage data on streams is opt-in. The limitation is documented in the module docstring. A future improvement could auto-inject the option at the patch layer, but that requires modifying the outbound request, which is a bigger change than this PR intended to be.

Anthropic has no equivalent limitation -- usage is always present.

## What I learned

**Transparent wrappers need the full protocol.** It is tempting to implement just `__iter__` and call it done. But real callers use context managers, explicit close, and async variants. Implementing the minimum breaks production code in ways that are hard to debug.

**Streaming costs are provider-specific.** OpenAI and Anthropic have different conventions for where usage data appears in the stream. Any SDK that claims to support both needs to handle both separately.

**Test against real SDK objects, not just mocks.** The `isinstance` detection and chunk structure only behave correctly against live SDK classes. Mock-based tests passed for the wrong reasons until I verified against an actual installed SDK.

## Links

- [PR #6 -- feat: track costs for streaming OpenAI and Anthropic responses](https://github.com/AgentBudget/agentbudget/pull/6)
- [AgentBudget on GitHub](https://github.com/AgentBudget/agentbudget)
- [PyPI](https://pypi.org/project/agentbudget/)
