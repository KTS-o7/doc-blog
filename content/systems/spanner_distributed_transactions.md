+++
title = "How Spanner Does Distributed Transactions Without Classic 2PC"
date = 2026-05-03T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "Google Spanner achieves globally consistent distributed transactions using TrueTime — bounded clock uncertainty instead of classic 2PC, enabling external consistency at planetary scale."
tags = ["distributed-systems", "databases", "spanner", "transactions", "consistency"]
+++

Two-phase commit has a well-known problem: crash the coordinator between Phase 1 and Phase 2 and every participant is stuck holding locks, waiting, with no safe way to proceed. 2PC is a blocking protocol.

Google Spanner runs distributed transactions across a globally replicated database at scale. It can't afford to block on coordinator failure. Its solution is to not use a standalone coordinator at all -- it runs 2PC on top of Paxos groups, which means the coordinator itself is fault-tolerant.

## The Core Move: Paxos Groups as Participants

In classic 2PC, each participant is a single node. It votes, acquires locks, and waits. If it crashes, the transaction is stuck.

Spanner's participants are Paxos groups. Each shard of data is managed by a Paxos group -- typically 5 replicas spread across datacenters. The Paxos leader for each group acts as the 2PC participant. Lock acquisition and voting happen on the leader, and the decision is durably replicated to the group before the leader responds.

If the coordinator crashes, a new coordinator can be elected (it's also a Paxos group). If a participant leader crashes, a new leader in that group takes over -- the lock state and vote are already replicated, so the protocol can continue.

The blocking problem is solved not by changing the protocol but by making every node in the protocol fault-tolerant.

## TrueTime

Spanner adds something 2PC doesn't have: globally synchronized timestamps, accurate enough to use for transaction ordering.

Google runs GPS receivers and atomic clocks in each datacenter and exposes a `TrueTime` API that returns a time interval `[earliest, latest]` rather than a single timestamp. The interval accounts for clock uncertainty. The guarantee is that the real current time lies somewhere in that interval.

Spanner uses TrueTime to assign commit timestamps. The rule: a transaction's commit timestamp must be after the `latest` bound of TrueTime at the moment the coordinator decides to commit. This means Spanner waits for a brief period -- typically 1-7ms -- before declaring a transaction committed, to ensure that any other transaction starting after this one will see a strictly later timestamp.

This is the "commit wait." It's intentional latency, paid to guarantee that commit timestamps accurately reflect real-world ordering.

## External Consistency

The property this buys is external consistency: if transaction T1 commits before T2 starts (in real-world time), T2 will see T1's writes. This is stronger than serializability -- serializable transactions can be ordered in any way consistent with their conflicts, even if that reorders real-world causality. External consistency preserves real-world order.

In practical terms: if you commit a write and then tell a colleague "it's committed, go read it," their read will see your write. There's no window where a causally later transaction misses a causally earlier committed write.

Most distributed databases don't provide this. They provide serializability, which is strong, but allows committed writes to be temporarily invisible to transactions that started after the commit in real time. Spanner's external consistency closes that gap.

## What the 2PC Layer Actually Looks Like

A read-write transaction in Spanner:

1. Client reads data, buffers writes locally (no locks yet)
2. Client sends commit request to the coordinator Paxos group
3. Coordinator runs 2PC with each participant Paxos group:
   - Sends `PREPARE` to each participant leader
   - Each participant leader acquires locks, logs the prepare record to its Paxos group, replies `YES`
   - Coordinator picks a commit timestamp (TrueTime `latest` + epsilon), logs it to its group
   - Sends `COMMIT` with the timestamp to all participants
4. Coordinator waits out the commit wait interval
5. Participants apply the writes at the commit timestamp, release locks
6. Client sees commit confirmation

The 2PC messages are still there. The key difference is that every step that touches durable state goes through a Paxos replication round first. The coordinator can crash and be replaced. A participant leader can crash and its successor has the full prepare state. Nothing blocks permanently.

## The Cost

The commit wait adds latency. For single-region transactions it's small (sub-millisecond when clocks are well-synchronized). For multi-region transactions where the coordinator and participants are in different continents, round-trip latency dominates and the TrueTime uncertainty is larger -- you're looking at tens of milliseconds.

Spanner is designed for this tradeoff: strong global consistency in exchange for latency that scales with geographic distance. For financial systems, global inventory, or anything that requires real external consistency, that tradeoff is often correct. For low-latency local transactions, it's usually not.

Classic 2PC is blocking because the coordinator is a single node. Spanner's answer is not to fix 2PC -- it's to make every node in the 2PC protocol a replicated state machine.
