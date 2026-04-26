+++
title = "Two-Phase Commit"
date = 2026-04-26T00:00:00+05:30
draft = false
math = false
+++

Suppose you have a transaction that touches three separate databases -- a flight reservation, a hotel booking, and a payment charge. You want either all three to commit or none of them to. One service can't commit and another abort. How do you coordinate that?

The answer most people reach for is Two-Phase Commit (2PC). It works in the happy path. The failure path has a flaw that's been known since the algorithm was described in 1978, and every distributed systems engineer should understand it before deciding whether to use 2PC.

## The Protocol

A single **coordinator** node drives two rounds of messages to all **participants** (the nodes doing the actual work).

**Phase 1 -- Prepare:**
The coordinator broadcasts "can you commit?" to all participants. Each participant:
- Writes the transaction to a durable log (so it can replay after a crash)
- Acquires all necessary locks
- Replies YES or NO

**Phase 2 -- Commit or Abort:**
- If all participants voted YES → coordinator sends COMMIT to everyone
- If any participant voted NO (or timed out) → coordinator sends ABORT to everyone
- Participants execute the decision and release their locks

```
Coordinator          Node A        Node B
    |--- PREPARE ------->|             |
    |--- PREPARE ---------|----------->|
    |<-- YES ------------|             |
    |<-- YES ------------|-------------|
    |--- COMMIT -------->|             |
    |--- COMMIT ----------|----------->|
    [all nodes commit, locks released]
```

The protocol guarantees atomicity: either every participant commits or every participant aborts. From the outside, the transaction appears to happen all at once or not at all.

## The Fatal Flaw -- Blocking Under Failure

The coordinator crashes after receiving all YES votes but before sending Phase 2.

Now every participant is stuck. They voted YES and locked their resources. They don't know whether the coordinator decided to commit or abort before it crashed. They can't safely do either:
- If they commit, they might contradict an abort decision the coordinator had already sent to other nodes they can't see
- If they abort, they might contradict a commit decision the coordinator had already sent

So they wait. Resources stay locked. The system can't make progress until the coordinator recovers.

This is the **blocking problem**. 2PC is a blocking protocol -- a coordinator failure at exactly the wrong moment halts the entire transaction indefinitely. In a high-availability system, "wait for coordinator recovery" is not an acceptable answer to a failure.

The window of vulnerability is specific: after all participants have voted YES but before the coordinator has durably recorded and sent Phase 2. This is exactly the moment when locking is at maximum and the decision hasn't propagated yet.

## Why Can't Participants Just Decide Among Themselves?

When the coordinator goes silent, why can't participants just contact each other and figure out what to do?

If all participants voted YES, they still can't commit safely -- there might be a participant they can't reach that voted NO. If even one participant voted NO, the correct answer is abort, but the participants that voted YES don't know that. Without the coordinator, they don't have enough information to make a safe decision.

The only safe action is to wait. This is why 2PC is called a **blocking protocol**: a coordinator failure forces participants into an indefinite blocked state.

## 3PC: The Theoretical Fix

Three-Phase Commit adds a `PRE-COMMIT` phase between Prepare and Commit:

`PREPARE → PRE-COMMIT → COMMIT`

The intuition: after all participants acknowledge PRE-COMMIT, every participant knows that every other participant voted YES. If the coordinator fails now, any participant can take over and safely drive the protocol to COMMIT -- they know no one voted NO.

This eliminates blocking for **crash failures**. It doesn't help under **network partition** -- if the coordinator is unreachable due to a partition, a partitioned participant still can't distinguish "coordinator crashed" from "coordinator is alive but I can't reach it." Attempting to make progress risks committing on one side of the partition and aborting on the other.

3PC is theoretically cleaner and not used in practice. The partition problem means it doesn't actually deliver on the "no blocking" promise in real deployments. The extra round-trip cost isn't worth it for partial relief.

## The CAP Angle

2PC is a CA protocol in CAP terms: it provides consistency and availability in the absence of network partitions, but it doesn't tolerate partitions. When the coordinator becomes unreachable (a partition), participants block -- availability is sacrificed to preserve consistency.

This is a fundamental constraint, not an implementation bug. Any protocol that guarantees atomicity across multiple nodes must give up availability under some failure scenario. The question is which failure scenarios you're willing to be unavailable for, and how long.

## What Modern Systems Do Instead

| Approach | Mechanism | What You Give Up |
|---|---|---|
| **Saga pattern** | Compensating transactions | Isolation -- intermediate state is visible |
| **Paxos / Raft underneath** | Coordinator is itself replicated | Complexity; still blocking but coordinator failure is rare |
| **Optimistic concurrency** | Detect conflicts at commit time | Retry cost under contention |
| **Single-node transactions** | Design away distributed txns | Flexibility in data model |

The most common outcome for microservices is the Saga pattern -- break the distributed transaction into local steps with explicit compensations. You lose strict atomicity but gain availability and no cross-service locks.

2PC still shows up inside single databases for coordinating writes across shards. CockroachDB and Spanner both use variants of 2PC internally, but the coordinator is backed by Raft -- a replicated state machine. The coordinator can't go down permanently; it fails over. The blocking window still exists but the recovery time is seconds, not "until an engineer restarts the process."

## The Implementation Detail That Matters Most

Good 2PC implementations persist the coordinator's decision to durable storage before sending a single Phase 2 message. The sequence is:

1. Collect all YES votes
2. **Write "COMMIT" to durable log** (fsync)
3. Send COMMIT to all participants

If the coordinator crashes between steps 2 and 3, recovery reads the log and replays Phase 2. If it crashes before step 2, participants time out and abort -- a safe outcome.

The dangerous case is a buggy implementation that reverses steps 2 and 3 or doesn't fsync. The coordinator sends some COMMITs, crashes, and restarts without knowing it already sent Phase 2 to some participants. Now you have partial commits with no recovery path.

The blocking problem is inherent to the protocol. The partial-commit problem is an implementation failure. Both look the same from the outside: a transaction in an unknown state with locked resources. The difference matters for diagnosis and recovery -- and for understanding why so many production systems have quietly moved away from 2PC for anything that matters.
