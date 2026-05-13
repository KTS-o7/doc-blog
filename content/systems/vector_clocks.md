+++
title = "Vector Clocks: Causality Without a Shared Clock"
date = 2026-05-02T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "Vector clocks track causality in distributed systems — each event carries a logical timestamp that tells you whether two events are causally related or concurrent."
tags = ["distributed-systems", "algorithms", "vector-clocks", "causality"]
+++

In a distributed system there's no shared clock. Two nodes can't agree on what time it is -- network latency is variable, clocks drift, and NTP only gets you so far. So you can't use timestamps to order events across nodes in any meaningful way.

The question is: can you still tell whether one event caused another?

Vector clocks answer that question. They don't give you wall-clock time. They give you something more useful: a precise definition of "happened before."

## How They Work

Each node maintains a vector of counters, one slot per node in the system. Call them `[A, B, C]` for a three-node cluster.

Three rules:

1. **Local event** -- increment your own counter
2. **Send a message** -- attach the current vector to the message
3. **Receive a message** -- merge by taking the element-wise max of your vector and the received vector, then increment your own counter

A concrete trace:

```
Node A starts:  [A:0, B:0, C:0]
Node A event:   [A:1, B:0, C:0]
Node A sends to B, attaches [A:1, B:0, C:0]

Node B receives, merges: max([A:0,B:0,C:0], [A:1,B:0,C:0]) = [A:1,B:0,C:0]
Node B increments own:   [A:1, B:1, C:0]
Node B event:            [A:1, B:2, C:0]
```

## What You Can Determine

Given two events with vectors `V1` and `V2`, exactly one of three things is true:

| Result | Condition |
|---|---|
| V1 happened-before V2 | V1[i] <= V2[i] for every i, and strict for at least one |
| V2 happened-before V1 | V2[i] <= V1[i] for every i, and strict for at least one |
| **Concurrent** | Neither vector dominates |

The concurrent case is the important one. When neither vector dominates, the events genuinely have no causal relationship -- they happened independently on different nodes without either one knowing about the other. No ordering can be inferred because no ordering exists.

## Why This Matters

The alternative is last-write-wins: when two writes conflict, pick the one with the later timestamp and discard the other. This is simple to implement and silently destroys data. If two users edit the same document concurrently, you lose one of their changes without telling anyone.

Vector clocks let you detect that conflict honestly. DynamoDB and Riak use them (or variants) to surface conflicting writes to the application rather than silently resolving them. The application -- or the user -- can then merge the two versions intelligently.

"Happened-before" is a relationship you earn through the causal structure of the system, not one you assume from timestamps.

## The Tradeoff

Vector size grows O(N) with the number of nodes. In a cluster with hundreds of nodes, attaching a full vector to every message gets expensive.

**Dotted version vectors** are a modern fix: they compress the vector by pruning entries that are causally dominated. Same core semantics, better space efficiency for large clusters.

Lamport clocks are the scalar predecessor -- a single counter instead of a vector. They give you a consistent ordering (if A happened-before B, A's timestamp is lower), but they don't detect concurrency. Two events with different Lamport timestamps might still be concurrent. Vector clocks are strictly more informative.
