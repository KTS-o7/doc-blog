+++
title = "Fixing Parallel Tool Call Streaming in Bifrost: An OSS Bug Hunt"
date = 2026-03-02T00:00:00+00:00
draft = false
math = false
author = "Krishnatejaswi S"
description = "Debugging a parallel tool call streaming bug in Bifrost — how delta chunks from different tool calls interleave incorrectly and the fix that restores correct JSON assembly."
tags = ["open-source", "debugging", "oss-contribution", "llm"]
+++

An AI agent calls three tools in parallel. The LLM streams back interleaved deltas — a few bytes of `search_documents` arguments, then a few bytes of `get_user`, then more `search_documents`. On the other end, the gateway reassembles these fragments into complete tool calls.

Except it doesn't. It concatenates them all into one call: `search_documentsget_usersearch_documents`. The agent hallucinates, retries, and loops. I stared at the telemetry for twenty minutes before I realized the bug wasn't in the agent — it was in the gateway's streaming accumulator.

This is the story of how I found and fixed a parallel tool call merging bug in [Bifrost](https://github.com/maximhq/bifrost), a 2.6k-star open-source AI gateway.

## What is Bifrost?

Bifrost is a high-performance AI gateway written in Go. It sits between your application and LLM providers (OpenAI, Anthropic, Bedrock, Vertex, etc.), providing a unified OpenAI-compatible API with automatic failover, load balancing, semantic caching, and streaming support. Think of it as an intelligent reverse proxy for AI — one API, fifteen providers, ~11µs overhead at 5k RPS.

The relevant piece here is the **streaming accumulator**. When you make a streaming chat completion request, the LLM sends back a sequence of Server-Sent Events (SSE), each containing a small delta — a few tokens of text, or a fragment of a tool call's arguments. The accumulator's job is to reassemble these deltas into complete messages.

## The bug: recency-based routing

Here's the scenario. You ask Claude or GPT to call two tools in parallel:

```
User: "Search for compliance circulars about RBI and also get the user's profile"
```

The model decides to call both `search_circulars` and `get_user_profile` simultaneously. During streaming, the provider sends interleaved deltas:

```
Delta 1: tool_call[0] name="search" (index=0, id=call_abc)
Delta 2: tool_call[1] name="get_us" (index=1, id=call_xyz)
Delta 3: tool_call[0] args='{"query": "RBI'   (index=0)
Delta 4: tool_call[1] args='{"user_id": "u'   (index=1)
Delta 5: tool_call[0] args=' circulars"}'      (index=0)
Delta 6: tool_call[1] args='123"}'             (index=1)
```

Each delta carries an `index` (and optionally an `id`) that identifies which tool call it belongs to. The expected behavior: two distinct tool calls with their own names and arguments.

The actual behavior in Bifrost's accumulator before the fix:

```go
// Old logic (simplified)
if deltaToolCall.Function.Name != nil {
    // New tool call — create it
    existingToolCalls = append(existingToolCalls, newToolCall)
} else {
    // Argument delta — append to the LAST tool call
    toolCallToModify = &existingToolCalls[len(existingToolCalls)-1]
    toolCallToModify.Function.Arguments += deltaToolCall.Function.Arguments
}
```

The routing logic was based on **recency**: if a delta has a `Name`, it's a new tool call; otherwise, append arguments to the most recent one. This works perfectly when tool calls arrive sequentially. It breaks completely when they're interleaved.

With the deltas above:
- Delta 3 (index=0 args) arrives → appended to the **last** tool call, which is `get_user_profile` (index=1). Wrong target.
- Delta 5 (index=0 args) arrives → again appended to `get_user_profile`. Now `get_user_profile` has arguments from two different calls mashed together.

The result: concatenated tool names, merged arguments, and an agent stuck in a retry loop trying to invoke `search_circularsget_user_profile` — a tool that doesn't exist.

## Finding the bug

I hit this in production. Our compliance platform uses an AI agent that calls multiple tools in parallel — searching circulars, fetching regulatory data, looking up user context. The agent kept failing with tool resolution errors, and the telemetry showed impossible tool names:

```
search_circularsearch_circularsearch_circular
```

At first I suspected the agent's tool-calling logic. Then I looked at the raw SSE stream from the provider — the deltas were correct. Each one had the right `index` and `id`. The corruption was happening between the provider response and the final accumulated message.

I traced it to `accumulateToolCallsInMessage` in `framework/streaming/accumulator.go`. The function had no concept of tool call identity. It used the presence of a `Name` field as a heuristic for "new vs. continuation," which is fragile and incorrect when deltas arrive out of order.

## The fix

The fix is conceptually simple: **route deltas by identity, not by recency.**

Each tool call delta carries two potential identifiers:
1. `tool_call.id` — a string like `call_abc123` (set by OpenAI/Anthropic)
2. `tool_call.index` — an integer position (0, 1, 2, ...)

The new logic builds lookup maps on existing tool calls and uses them to route each incoming delta to the correct target:

```go
// Build lookup maps for identity-based routing
idToIndex := make(map[string]int, len(existingToolCalls))
indexToIndex := make(map[uint16]int, len(existingToolCalls))
for i, toolCall := range existingToolCalls {
    if toolCall.ID != nil && *toolCall.ID != "" {
        idToIndex[*toolCall.ID] = i
    }
    indexToIndex[toolCall.Index] = i
}
```

For each incoming delta, routing follows a priority chain:

```go
for _, deltaToolCall := range deltaToolCalls {
    index := -1

    // Priority 1: match by tool_call.id
    if deltaToolCall.ID != nil && *deltaToolCall.ID != "" {
        if existingIndex, ok := idToIndex[*deltaToolCall.ID]; ok {
            index = existingIndex
        }
    }

    // Priority 2: match by tool_call.index
    if index == -1 {
        if existingIndex, ok := indexToIndex[deltaToolCall.Index]; ok {
            index = existingIndex
        }
    }

    // Priority 3: no match → create new tool call (if name present)
    if index == -1 {
        if deltaToolCall.Function.Name == nil {
            // Can't create a tool call without a name
            continue
        }
        newToolCall := schemas.ChatAssistantMessageToolCall{
            Index:    deltaToolCall.Index,
            ID:       deltaToolCall.ID,
            Function: /* ... */,
        }
        existingToolCalls = append(existingToolCalls, newToolCall)
        // Update maps for future deltas
        indexToIndex[newToolCall.Index] = len(existingToolCalls) - 1
        if newToolCall.ID != nil {
            idToIndex[*newToolCall.ID] = len(existingToolCalls) - 1
        }
        continue
    }

    // Append arguments to the correct tool call
    existingToolCalls[index].Function.Arguments += deltaToolCall.Function.Arguments
}
```

The key insight is that the maps are updated as new tool calls are created, so subsequent deltas for the same call always find their target — even if they arrive many chunks later.

## The same bug, twice

During code review, a reviewer ([Pratham-Mishra04](https://github.com/Pratham-Mishra04)) pointed out that the same recency-based routing existed in a second code path: the **Responses API streaming** handler in `responses.go`.

The Responses API is OpenAI's newer streaming format (the `/v1/responses` endpoint). It uses `ItemID` instead of `tool_call.index`, but the accumulation logic had the same flaw — `FunctionCallArgumentsDelta` events were always appended to the last message:

```go
// Old responses.go logic
if resp.Delta != nil && len(messages) > 0 {
    // Always targets the last message — wrong for parallel calls
    a.appendFunctionArgumentsDeltaToResponsesMessage(
        &messages[len(messages)-1], *resp.Delta)
}
```

The fix follows the same pattern: search for a message matching `resp.ItemID`, and only fall back to the last message when no `ItemID` is present. If an `ItemID` exists but no message matches, create a stub message to hold the delta rather than merging it into the wrong call:

```go
if resp.Delta != nil && len(messages) > 0 {
    targetIdx := len(messages) - 1
    if resp.ItemID != nil {
        targetIdx = -1
        for i := len(messages) - 1; i >= 0; i-- {
            if messages[i].ID != nil && *messages[i].ID == *resp.ItemID {
                targetIdx = i
                break
            }
        }
        if targetIdx == -1 {
            // Create stub to avoid merging into wrong message
            id := *resp.ItemID
            messages = append(messages, schemas.ResponsesMessage{ID: &id})
            targetIdx = len(messages) - 1
        }
    }
    a.appendFunctionArgumentsDeltaToResponsesMessage(
        &messages[targetIdx], *resp.Delta)
}
```

## Testing parallel accumulation

The regression test simulates the exact interleaving pattern that triggers the bug:

```go
func TestAccumulateToolCallsInterleavedParallel(t *testing.T) {
    // ...
    toolCallID0 := "call_0"
    toolCallID1 := "call_1"
    toolNameAdd := "add"
    toolNameMultiply := "multiply"

    // Simulate interleaved deltas
    accumulate(makeDelta(0, &toolCallID0, &toolNameAdd, ""))       // create call 0
    accumulate(makeDelta(1, &toolCallID1, &toolNameMultiply, ""))  // create call 1
    accumulate(makeDelta(0, nil, nil, `{"a": 1`))                  // args for call 0
    accumulate(makeDelta(1, nil, nil, `{"a": 2`))                  // args for call 1
    accumulate(makeDelta(0, nil, nil, `, "b": 3}`))                // more args for call 0
    accumulate(makeDelta(1, nil, nil, `, "b": 4}`))                // more args for call 1

    // Assert: two distinct tool calls with correct arguments
    assert(addCall.Arguments == `{"a": 1, "b": 3}`)
    assert(multiplyCall.Arguments == `{"a": 2, "b": 4}`)
}
```

Without the fix, `add` would end up with `multiply`'s arguments concatenated in. With the fix, each call accumulates only its own deltas.

A second test covers the Responses API path with `ItemID`-based routing, using the same interleaving pattern but with `OutputItemAdded` + `FunctionCallArgumentsDelta` events.

## The PR lifecycle

I filed [Issue #1829](https://github.com/maximhq/bifrost/issues/1829) with reproduction details from production telemetry, then opened [PR #1830](https://github.com/maximhq/bifrost/pull/1830) with the fix and tests.

The review process was smooth:
1. First commit: fix the Chat Completions accumulator + regression test
2. Reviewer feedback: same bug exists in Responses API — please fix there too + add changelog entries
3. Second commit: fix Responses API routing + regression test + changelogs
4. Merged by [akshaydeo](https://github.com/akshaydeo) (Bifrost maintainer)

Total: 3 commits, ~280 lines of Go across 5 files. Same-day turnaround from issue to merge.

## What I learned

### 1. Recency is not identity

The original code used position (last element) as a proxy for identity. This is a common pattern in sequential streaming — and it works, until the stream isn't sequential. The fix is to use the actual identity field that the protocol already provides.

This is a general principle: **if the protocol gives you an ID field, use it.** Don't rely on ordering assumptions that hold today but break when concurrency enters.

### 2. The same bug pattern repeats across API surfaces

Bifrost supports two streaming formats: Chat Completions (the classic `tool_calls` array) and Responses API (the newer `ItemID`-based format). Both had the same routing flaw because the accumulation logic was duplicated rather than shared. The reviewer catching this in a different file was the most valuable part of the review.

### 3. OSS contributions are about context, not complexity

The fix itself is straightforward — build a map, use it for lookup. The hard part was:
- **Finding** the bug in a codebase I'd never seen before
- **Understanding** why the existing approach was wrong
- **Testing** with realistic interleaved deltas
- **Responding** to review feedback about a parallel code path I hadn't initially noticed

The code change was ~100 lines. The context-building was hours.

### 4. Production telemetry is the best bug report

The issue report included the exact malformed tool name from production: `search_circularsearch_circularsearch_circular`. That single string made the bug immediately reproducible and the fix trivially verifiable. If you're filing a bug, include the malformed output — it's worth more than a paragraph of description.

## Links

- **PR**: [fix: preserve parallel tool call deltas — #1830](https://github.com/maximhq/bifrost/pull/1830)
- **Issue**: [Streaming tool call deltas merge in parallel tool calling — #1829](https://github.com/maximhq/bifrost/issues/1829)
- **Project**: [Bifrost AI Gateway](https://github.com/maximhq/bifrost) — 2.6k ⭐, fastest enterprise AI gateway
