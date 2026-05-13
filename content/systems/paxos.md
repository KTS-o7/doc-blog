+++
title = "Paxos"
date = 2026-04-26T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "Paxos is a consensus protocol for getting a distributed system to agree on a single value despite node failures and message delays — the foundation of most replicated state machines."
tags = ["distributed-systems", "consensus", "paxos"]
+++

Before Raft, there was Paxos. For about two decades it was the foundational answer to distributed consensus -- and it was notoriously hard to implement correctly. Lamport published the original paper in 1989, but it was so difficult to parse that he rewrote it as "Paxos Made Simple" in 2001. The simpler version is still genuinely hard.

Understanding Paxos is worth doing. It's not just historical -- Chubby, ZooKeeper, and Spanner are built on it or close variants, and many distributed systems interviews probe it. More importantly, every simplification Raft makes is a direct response to a specific pain point in Paxos. Understanding what Paxos gets wrong explains why Raft looks the way it does.

## The Problem

Multiple nodes need to agree on a single value. The network is unreliable: messages can be dropped, reordered, or delayed arbitrarily. Nodes can crash at any time. There is no shared clock.

A minority of nodes can fail; the protocol must still make progress. The protocol must also be safe: once a value is chosen, no future round can choose a different value.

This is the consensus problem. Two-Phase Commit solves it only when the coordinator doesn't fail. Paxos solves it even when any minority of nodes can fail, including the "coordinator."

## Roles

Any node can play any role (often all three simultaneously in practice):

- **Proposer** -- initiates a round, trying to get a value agreed upon
- **Acceptor** -- votes on proposals; the safety machinery lives here
- **Learner** -- learns what value was finally chosen, acts on it

## The Protocol -- Two Phases

### Phase 1: Prepare / Promise

1. The proposer picks a **proposal number** `n`. It must be unique across all proposers and higher than any proposal number the proposer has seen before. (Usually implemented with `(timestamp, node_id)` tuples or a monotonic counter stored durably.)

2. Sends `PREPARE(n)` to a quorum of acceptors (any majority).

3. Each acceptor that receives `PREPARE(n)`:
   - If `n` is higher than any PREPARE it has responded to: replies `PROMISE(n)`, committing to **reject any future PREPARE or ACCEPT with a lower proposal number**
   - If `n` is not higher: ignores or rejects the request
   - If it has already accepted a value in a prior round, it includes that `(accepted_n, accepted_value)` in the promise

### Phase 2: Accept / Accepted

1. If the proposer receives PROMISE from a quorum:
   - If any promise included an `(accepted_n, accepted_value)`, the proposer **must use the value with the highest `accepted_n`** -- it cannot freely choose its own value
   - If no promise included an accepted value, the proposer can propose any value it wants
2. Sends `ACCEPT(n, value)` to the quorum
3. Each acceptor that receives `ACCEPT(n, value)`:
   - If it hasn't promised to ignore `n`: writes the value and replies `ACCEPTED(n, value)`
   - If it has made a promise with a higher number: ignores or rejects
4. Once a quorum of acceptors reply `ACCEPTED` with the same `n` → the value is **chosen**

```
Proposer          Acceptor A    Acceptor B    Acceptor C
   |-- PREPARE(5) -->|             |             |
   |-- PREPARE(5) ---|------------>|             |
   |<-- PROMISE(5) --|             |             |
   |<-- PROMISE(5) --|-------------|             |
   |-- ACCEPT(5,v) ->|             |             |
   |-- ACCEPT(5,v) --|------------>|             |
   |<-- ACCEPTED ---|              |             |
   |<-- ACCEPTED ---|--------------|             |
      [value v is chosen, Acceptor C was unreachable but quorum achieved]
```

## Why It's Correct

**Safety (no two values can be chosen):** Suppose value `v` was chosen at proposal `n` -- meaning a quorum Q1 accepted it. Any later proposer `n' > n` that runs Phase 1 will receive promises from a quorum Q2. Q1 and Q2 must overlap (both are majorities). The overlapping acceptor already accepted `v` and includes `(n, v)` in its promise. The Phase 2 rule forces the new proposer to use `v` (since it's the highest accepted value). So no different value can ever be chosen.

**Liveness (the protocol makes progress):** As long as a majority of nodes are reachable and a single stable proposer drives the protocol, a value will eventually be chosen. The protocol doesn't guarantee progress if proposers keep competing -- see the livelock problem below.

## The Gotchas

### Livelock with Competing Proposers

Two proposers P1 and P2 can keep preempting each other indefinitely:

```
P1 sends PREPARE(5), gets promises from quorum
P2 sends PREPARE(6) before P1 can reach ACCEPT -- quorum promises ignore n=5
P1's ACCEPT(5, v) is rejected -- quorum promised to ignore anything < 6
P1 increments to PREPARE(7), gets new promises
P2's ACCEPT(6, v) is now rejected
... loops forever
```

The fix is a **distinguished proposer** (leader): only one node proposes at a time. This is what Multi-Paxos formalizes -- elect a stable leader, suppress all other proposers, and the livelock disappears. It's not part of basic Paxos; it's an add-on that every production implementation requires.

### Single-Value vs. Log: Multi-Paxos

Basic Paxos agrees on one value. Real systems need to agree on a sequence of commands -- a log. Multi-Paxos runs Paxos for each log slot, but with an optimization: once a stable leader exists, you can skip Phase 1 for subsequent slots. You pay the two-round-trip cost once per leader election, then only Phase 2 for every log entry.

The problem: Multi-Paxos is not a formal protocol. It's described as an optimization on basic Paxos, and different implementations fill in the details differently. Log gaps are allowed -- a slot can be accepted out of order. Cluster membership changes are not specified. Leader election is not specified. This leaves a large surface area for subtle bugs.

### It's Hard to Implement Correctly

"Paxos Made Simple" describes the algorithm clearly. Getting from there to a correct implementation in a production system requires handling: durability of acceptor state across crashes (promise/accept must be persisted before responding), leader election, log gap handling, log compaction, cluster membership changes, client request routing, and linearizable reads. None of these are in the paper.

Chubby's authors wrote that their Paxos implementation took years to get right and required multiple rewrites. This is why Raft was created.

## Paxos vs. Raft

The safety properties are equivalent. The differences are implementation surface:

| | Paxos (Multi-Paxos) | Raft |
|---|---|---|
| **Log gaps** | Allowed | Not allowed -- sequential only |
| **Leader** | Distinguished proposer, informally defined | Formal, enforced by protocol |
| **Config changes** | Not specified | Joint consensus built in |
| **Understandability** | Notoriously hard | Designed to be teachable |
| **Implementations** | Chubby, Zab (ZooKeeper), Spanner | etcd, CockroachDB, TiKV, Consul |

Same fault tolerance: both tolerate `⌊(N-1)/2⌋` node failures.

## Where Paxos Is Still Used

- **Google Chubby** -- distributed lock service. Underpins Bigtable and GFS for leader election and metadata coordination.
- **Apache ZooKeeper** -- uses Zab (ZooKeeper Atomic Broadcast), which is a Paxos variant with primary-order delivery guarantees added. Powers Kafka, HBase, and Hadoop ecosystem coordination.
- **Google Spanner** -- Paxos per shard for cross-replica replication. Combined with TrueTime for external consistency.

New systems almost universally choose Raft. The guarantees are equivalent and the implementation surface is much smaller. Paxos matters because it's what everything was built on, and because understanding what it leaves unspecified is the clearest way to understand why the distributed systems field spent a decade building on top of it before someone sat down and wrote a protocol that was complete enough to implement from scratch.
