+++
title = "Two-Phase Commit: Distributed Atomicity and Its Fatal Flaw"
date = 2026-05-02T00:00:00+05:30
draft = false
math = false
+++

The problem is simple to state: you have a transaction that touches multiple nodes. You want all of them to commit, or none of them to. No partial states, no one node committing while another aborts.

Two-phase commit (2PC) solves this. It's been in production databases for decades. It also has a flaw that makes it unusable for anything long-running, which is why most modern large-scale systems don't use it directly.

## The Protocol

There's a coordinator and a set of participants. The coordinator drives the protocol.

**Phase 1 -- Prepare**

The coordinator sends `PREPARE` to every participant. Each participant:
- Writes the transaction to a durable log
- Acquires the necessary locks
- Replies `YES` (ready to commit) or `NO` (something failed)

**Phase 2 -- Commit or Abort**

- If all participants said YES: coordinator sends `COMMIT` to everyone
- If anyone said NO: coordinator sends `ABORT`

Participants execute the decision and release their locks.

```
Coordinator         Node A        Node B
    |--- PREPARE ------->|             |
    |--- PREPARE ---------|----------->|
    |<-- YES ------------|             |
    |<-- YES ------------|-------------|
    |--- COMMIT -------->|             |
    |--- COMMIT ----------|----------->|
```

Clean path works fine. Every node ends up in the same state. Locks are held only for the duration of the protocol.

## The Fatal Flaw

Crash the coordinator after phase 1 but before phase 2.

Participants are now stuck. They voted YES and locked their resources. They don't know whether the coordinator decided to commit or abort. They can't safely proceed in either direction -- committing might be wrong if another participant said NO, aborting might be wrong if the coordinator was about to send COMMIT.

They wait. The locks stay held. The system is in limbo until the coordinator recovers.

This is the **blocking problem**. 2PC is a blocking protocol under failure. A single coordinator crash can stall the entire transaction indefinitely.

## The Attempted Fix: 3PC

Three-phase commit inserts a pre-commit phase between prepare and commit:

`PREPARE → PRE-COMMIT → COMMIT`

Pre-commit lets participants infer the coordinator's intent even if it crashes: if you received a pre-commit, the coordinator had seen all YES votes and was going to commit. You can safely commit yourself if the coordinator disappears after that point.

3PC eliminates most blocking scenarios. It costs one extra round of messages and still has edge cases under network partitions. It's not widely used in practice -- the complexity tradeoff isn't worth it for most systems.

## What Systems Actually Do

| Approach | Mechanism | Tradeoff |
|---|---|---|
| Saga pattern | Compensating transactions | No locks, but no true atomicity |
| Paxos / Raft | Consensus algorithm | Strong guarantees, higher complexity |
| Optimistic concurrency | Detect conflicts at commit time | Works well for low-contention workloads |

Most large-scale systems avoid 2PC for anything user-facing. Short, internal database transactions -- a single service committing to one database -- are fine. Cross-service transactions that could run for seconds or involve user interaction are not.

2PC is worth understanding because it makes the tradeoff concrete: you can have distributed atomicity, but you're paying for it with availability under coordinator failure. Everything else in distributed transactions is a different point on that curve.
