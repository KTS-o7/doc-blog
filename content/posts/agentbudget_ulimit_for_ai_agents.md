+++
title = "AgentBudget: The ulimit for AI Agents"
date = 2026-04-16T00:00:00+05:30
draft = false
math = false
+++

An AI agent runs a research loop. It calls a search API, summarizes results, decides it needs more context, calls the API again, and again. The model is uncertain so it hedges -- more calls, longer prompts, bigger context windows. By the time the loop terminates, $47 has left the account. No warning. No circuit breaker. Just a bill.

This is not a hypothetical. It is the default behavior of every LLM agent framework in existence. There is no standard primitive that says "stop spending after this amount." So I built one.

## The Unix analogy that made this obvious

Unix has `ulimit`. It is a hard ceiling on what a single process can consume -- file descriptors, stack size, CPU time, virtual memory. When the process hits the limit, it gets a signal. The system does not let one misbehaving process eat everything.

AI agent sessions have no equivalent. A single runaway loop can exhaust a budget in seconds. The infrastructure around the agent (LangGraph, AutoGen, plain Python) has no concept of a dollar ceiling. The LLM provider will happily keep serving requests until your credit card says no.

AgentBudget is that missing primitive. You set a dollar limit. Any session that crosses it raises `BudgetExhausted`. No silent overruns.

## What it actually does

The core idea is monkey-patching at the SDK level, the same pattern used by Sentry and Datadog. When you call `agentbudget.init("$5.00")`, it wraps the `create` methods on the OpenAI and Anthropic clients. Every call goes through the wrapper, which:

1. Looks up the cost of the model being called using a bundled pricing table
2. Adds the cost to the running session total
3. Raises `BudgetExhausted` if the total would exceed the limit

The application code does not change. No refactoring. No new client objects. Two lines:

```python
import agentbudget
agentbudget.init("$5.00")

# Everything below is unchanged
client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Research this topic in depth"}]
)
```

When the session ends:

```python
print(agentbudget.spent())      # 0.0423
print(agentbudget.remaining())  # 4.9577
print(agentbudget.report())     # Full breakdown by model and call count
agentbudget.teardown()          # Restore original SDK methods
```

For cases where you want explicit per-client tracking without global patching, there is a manual mode using context managers:

```python
from agentbudget import AgentBudget

budget = AgentBudget(max_spend="$5.00")

with budget.session() as session:
    response = session.wrap(client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Analyze this dataset"}]
    ))

    # Track external API calls with known costs
    result = session.track(call_search_api(query="market data"), cost=0.01)

    # Pre-flight check before an expensive call
    if not session.would_exceed(0.50):
        big_response = session.wrap(client.chat.completions.create(...))
```

## The hard parts

### Streaming costs

Streaming is where naive implementations fall apart. When you use `stream=True`, the API does not return a single response object with token counts -- it sends a sequence of deltas. The total cost is only known once the stream is exhausted.

For OpenAI streaming, you need `stream_options={"include_usage": True}` in the request to get token counts in the final chunk. Without it, there is nothing to price. AgentBudget injects this option automatically when patching the client, so streaming calls are tracked transparently without any change to the call site.

For async streaming, the same wrapper applies to `AsyncOpenAI` and `AsyncAnthropic`.

### Thread safety

The first community PR exposed a race condition. When multiple threads call the patched `create` method concurrently -- common in multi-agent setups -- the running total gets updated by multiple writers simultaneously. The fix is a lock around the accumulator. The lock is held only for the increment, not for the actual API call, so contention is minimal.

### OpenRouter model names

OpenRouter uses namespaced model names like `openai/gpt-4o` and `anthropic/claude-3-5-sonnet`. The pricing table keys on bare model names. Early versions silently treated OpenRouter calls as free. The fix is a normalization step that strips the provider prefix before lookup.

### The finalization reserve

There is a subtle failure mode specific to agentic loops: the agent runs out of budget mid-task and raises `BudgetExhausted` before producing any final output. The user gets an exception instead of a partial result.

The `finalization_reserve` parameter addresses this. You reserve a fraction of the budget for the final response step:

```python
agentbudget.init("$5.00", finalization_reserve=0.10)
```

This means `BudgetExhausted` is raised when 90% of the budget is consumed, not 100%. The agent's exception handler can then trigger a summarization call using the remaining 10% to produce a graceful final response rather than a crash.

## Multi-language SDKs

Python was the obvious starting point, but production AI systems are not always Python. The Go and TypeScript SDKs follow the same API surface -- `init`, `session`, `wrap`, `track`, `report` -- so the mental model transfers across languages.

The Go SDK has no external dependencies and is imported directly from GitHub. The TypeScript SDK is on npm. The Python SDK is on PyPI. All three are maintained under the same organization.

Go does not have monkey-patching, so the Go SDK uses an explicit wrapper pattern rather than global init. TypeScript uses the same approach as Python. The trade-off is explicitness over convenience -- in Go, you always know exactly what is being tracked.

## What the community found

The first external contributors surfaced four bugs that only appear under real workloads:

- Thread safety on the accumulator under concurrent agent calls
- Off-by-one on budget comparison (`>` instead of `>=`, allowing sessions to reach exactly the limit without raising)
- Silent crash when the pricing table has no entry for a model (should warn and continue)
- Negative costs accepted silently on manual `track()` calls

None of these are visible in single-threaded demos. They all appear in production at scale. Getting external contributors to find them early was the most valuable outcome of publishing the SDK quickly.

## The missing primitive

The ecosystem treats cost as a billing concern, not an engineering concern. Billing happens outside your code -- on a dashboard, in a monthly report. But cost is a runtime property of every LLM call, and it should be observable and controllable from inside your code.

`ulimit` exists because the OS learned, the hard way, that processes without resource limits create operational problems. AI agents are learning the same lesson. The tooling will catch up. Until it does, a two-line drop-in is enough to stop the bleeding.

## Links

- [AgentBudget on GitHub](https://github.com/AgentBudget/agentbudget)
- [PyPI](https://pypi.org/project/agentbudget/)
- [npm](https://www.npmjs.com/package/@agentbudget/agentbudget)
- [Go SDK](https://pkg.go.dev/github.com/AgentBudget/agentbudget/sdks/go)
