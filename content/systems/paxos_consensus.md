+++
title = "Paxos: How Distributed Systems Agree on Anything"
date = 2026-05-02T00:00:00+05:30
draft = false
math = false
+++

Every replicated database, every distributed lock, every leader election comes down to the same underlying problem: how do multiple nodes in an unreliable network agree on a single value, even when some of them crash or messages get delayed?

This is the consensus problem. Paxos is the foundational answer. It's also notoriously difficult to implement correctly -- which is exactly why Raft exists. But you can't really understand Raft without understanding what Paxos is doing and why.

## The Constraint

Two-phase commit solves distributed atomicity but requires the coordinator to stay up. If the coordinator crashes after phase 1, participants are stuck holding locks, unable to proceed. That's not consensus -- that's a single point of failure with extra steps.

Paxos removes that constraint. It guarantees agreement as long as a majority of nodes are up, regardless of which specific nodes fail. Any node can propose a value. No permanent coordinator required.

## Roles

In Paxos, nodes play three roles -- and in practice, any node can play any of them:

- **Proposer** -- initiates a round, tries to get a value accepted
- **Acceptor** -- votes on proposals, must follow the protocol strictly
- **Learner** -- learns the final chosen value once consensus is reached

## The Protocol

Paxos runs in two phases.

### Phase 1 -- Prepare / Promise

The proposer picks a proposal number `n` -- unique, higher than any it has seen before -- and sends `PREPARE(n)` to a quorum of acceptors (any majority).

Each acceptor that receives this:
- Promises to ignore any future `PREPARE` with a lower number
- If it has already accepted a value in a prior round, includes that `(old_n, old_value)` in its reply

### Phase 2 -- Accept / Accepted

If the proposer receives promises from a quorum:
- If any promise included a prior accepted value, the proposer **must use the highest one** -- it cannot choose freely
- Otherwise it can propose any value it wants

It sends `ACCEPT(n, value)` to the quorum. Acceptors that haven't made a conflicting promise write the value and reply `ACCEPTED`. Once a quorum accepts, the value is chosen.

```
Proposer       Acceptor A    Acceptor B    Acceptor C
   |-- PREPARE(5) -->|             |             |
   |-- PREPARE(5) ---|------------>|             |
   |<-- PROMISE(5) --|             |             |
   |<-- PROMISE(5) --|-------------|             |
   |-- ACCEPT(5,v) ->|             |             |
   |-- ACCEPT(5,v) --|------------>|             |
   |<-- ACCEPTED ----|             |             |
   |<-- ACCEPTED ----|-------------|             |
      [value v is now chosen]
```

## Why It's Correct

The safety guarantee -- that no two values are ever chosen -- comes from the quorum overlap. Any two majorities in an N-node cluster share at least one node. That shared node is the bridge: if a value was accepted in round `n`, a new proposer in round `n+1` will hear about it from the shared node and be forced to continue it rather than propose something different.

The constraint that proposers must adopt the highest prior accepted value is what makes this work. A new round can never silently override an old one.

## The Gotchas

**Livelock.** Two competing proposers can keep preempting each other with higher proposal numbers indefinitely -- neither ever reaching phase 2. The fix is to elect a single distinguished proposer (a leader) and have everyone else defer to it. This is what Multi-Paxos does.

**Single-value vs. Multi-Paxos.** Basic Paxos agrees on one value. Real systems need a log of values -- a sequence of commands. Multi-Paxos runs Paxos repeatedly for each log slot with a stable leader, amortizing the phase 1 cost across many entries. Once a leader is established, phase 1 only needs to run once per leader lifetime.

**Implementation gap.** The original paper was intentionally abstract. "Paxos Made Simple" is cleaner but still leaves enormous implementation latitude -- enough that teams have shipped subtly broken versions. The gap between the protocol description and a correct, production-safe implementation is one of the main reasons Raft was designed as an explicit replacement.

## Where It Runs

- **Google Chubby** -- distributed lock service, underpins Bigtable and GFS coordination
- **Apache ZooKeeper** -- uses Zab (ZooKeeper Atomic Broadcast), a Paxos variant
- **Google Spanner** -- Paxos per shard for replication across datacenters

Paxos is the theory. If you're building something new, you'll probably implement Raft instead -- same guarantees, actually debuggable. But the mental model of quorum-based two-phase consensus is worth having regardless of which one you reach for.
