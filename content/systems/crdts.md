+++
title = "CRDTs: Conflict-Free Replicated Data Types"
date = 2026-05-03T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "CRDTs eliminate merge conflicts by design — commutative, associative, idempotent data structures that converge to the same state regardless of operation order. G-Counters, OR-Sets, and LWW registers explained."
tags = ["distributed-systems", "crdt", "consistency", "algorithms"]
+++

Vector clocks tell you when two writes conflict. They don't tell you what to do about it. That's still your problem.

CRDTs take a different position: design the data structure so that conflicts can never happen. Not "detect and resolve" -- just structurally eliminate the problem.

## The Core Idea

A CRDT is a data structure with a merge function that is commutative, associative, and idempotent. Those three properties together mean you can apply updates in any order, any number of times, from any subset of nodes, and always converge to the same state.

- **Commutative**: merge(A, B) = merge(B, A) -- order doesn't matter
- **Associative**: merge(A, merge(B, C)) = merge(merge(A, B), C) -- grouping doesn't matter
- **Idempotent**: merge(A, A) = A -- applying the same update twice is harmless

If your data structure satisfies these, you can replicate it across nodes with no coordination. Each node applies updates locally and gossips state to peers. Eventually everyone has the same state.

## The Simplest CRDT: G-Counter

A grow-only counter. Each node maintains a vector of counts, one slot per node. To increment, a node adds to its own slot. To read the total, sum all slots. To merge two replicas, take the element-wise max.

```
Node A: [3, 1, 0]   Node B: [2, 2, 0]
Merge:  [3, 2, 0]   -- take max per slot
Total:  5
```

Node A can never decrement B's slot and Node B can never decrement A's slot. Merges always move counters up, never down. Convergence is guaranteed.

## Adding Decrements: PN-Counter

A grow-only counter can't go down. If you need decrements, use two G-Counters -- one for increments (P), one for decrements (N). The value is P - N.

Each node increments its P slot to add and its N slot to subtract. Merges take the element-wise max of both vectors. The final value is the sum of all P slots minus the sum of all N slots.

## Sets: The Interesting Case

Sets are where CRDTs get non-obvious. The naive approach breaks immediately: if Node A removes an element at the same time Node B adds it, what's the right answer?

**G-Set** (grow-only set) sidesteps this: elements can only be added, never removed. Merge is union. Works perfectly but is obviously limited.

**2P-Set** (two-phase set) adds a remove set R alongside the add set A. An element is in the set if it's in A but not R. Once removed, it can never be re-added. Merge is union on both sets.

**LWW-Element-Set** (last-write-wins) attaches a timestamp to each add and remove. On conflict, the higher timestamp wins. Simple, but you're back to trusting clocks.

**OR-Set** (observed-remove set) is the one that gets this right. Each add operation generates a unique tag. Remove only removes the specific tags that were observed at remove time. If Node A adds element X (tag: t1) and Node B concurrently adds X again (tag: t2), then Node A removing X (removing tag t1) leaves Node B's addition (tag t2) intact. The element stays in the set.

This matches user intuition: you removed the copy you knew about, not the one that was being added concurrently somewhere else.

## State-based vs. Operation-based

There are two families of CRDTs.

**State-based (CvRDTs)**: nodes gossip their full state. Merge is applied on receipt. The merge function must be a join on a join-semilattice -- a partial order where every pair of elements has a least upper bound. Simple to reason about, but shipping full state can be expensive for large structures.

**Operation-based (CmRDTs)**: nodes broadcast operations instead of state. No merge function needed on state -- instead, the transport layer must guarantee exactly-once delivery and causal ordering. More efficient, but the delivery guarantee is a real constraint.

In practice, libraries like Automerge and Yjs use operation-based CRDTs with a hybrid approach: operations for real-time sync, periodic state snapshots for catch-up after disconnection.

## Where They're Used

**Collaborative editing** is the obvious one. Google Docs uses OT (operational transformation), an older approach with similar goals. Figma uses CRDTs. Notion, Linear, and most newer collaborative tools have moved toward CRDTs because the math is cleaner and they handle offline edits naturally.

**Distributed databases**: Riak's eventual consistency model was built around CRDTs. Redis has CRDT support in Redis Enterprise for multi-region deployments. Azure Cosmos DB uses them internally for its multi-master replication.

**Shopping carts**: Amazon's Dynamo paper mentions the shopping cart as a canonical use case. Adds and removes to a cart from multiple devices or regions converge without a coordinator.

## The Tradeoff

CRDTs don't work for everything. The merge semantics have to match what your application actually means.

A bank account is not a PN-Counter. If your account shows $500 and you withdraw $200 concurrently from two ATMs, merging the two PN-Counters would show $100 -- which is correct math but incorrect banking. The constraint "balance must not go negative" requires coordination. You can't avoid that with a CRDT.

The rule: CRDTs work when the merge semantics match application intent and when the application can tolerate the conflict-free resolution behavior. They're not a universal replacement for coordination -- they're a way to avoid coordination in cases where the math lines up.

Vector clocks give you the diagnosis. CRDTs give you a structural guarantee that the diagnosis is never needed.
