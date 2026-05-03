+++
title = "Multi-Paxos: From Single Decree to a Replicated Log"
date = 2026-05-03T00:00:00+05:30
draft = false
math = false
+++

Basic Paxos agrees on a single value. That's useful for electing a leader or picking a configuration, but a database needs to agree on a sequence of values -- every write in order, forever. Running one full round of Paxos per log slot would work but it's expensive: two network round-trips per slot, and Phase 1 has to complete before Phase 2 can start.

Multi-Paxos is the optimization that makes Paxos practical as a replicated log. The insight is that Phase 1 can be amortized across many slots once you have a stable leader.

## What Phase 1 Actually Does

Recall basic Paxos. Phase 1 (Prepare/Promise) establishes that a proposer has the highest ballot number any acceptor will respond to. The acceptors promise to ignore any lower-numbered proposer. This is the "take control" phase -- after it completes, the proposer has permission to drive proposals through Phase 2.

Phase 1 doesn't say anything about which value gets proposed. It just establishes leadership over the acceptors for a given ballot number.

## The Amortization

If the same leader runs Phase 1 once with a high ballot number, it doesn't need to run Phase 1 again for subsequent log slots -- as long as no other proposer challenges it with a higher ballot.

The leader runs Phase 1 once, gets promises from a majority, and then drives Phase 2 directly for slot 1, slot 2, slot 3, and so on. Each slot is just one round-trip (Accept/Accepted) instead of two. Throughput roughly doubles for steady-state operation under a stable leader.

```
Phase 1 (once):   Leader → Prepare(ballot=5) → Majority
                  Majority → Promise(ballot=5, ...) → Leader

Phase 2 (per slot):
  Slot 1:  Leader → Accept(ballot=5, slot=1, value=A) → Majority
           Majority → Accepted → Leader → Committed
  Slot 2:  Leader → Accept(ballot=5, slot=2, value=B) → Majority
           Majority → Accepted → Leader → Committed
  ...
```

This is Multi-Paxos. The Phase 1 cost is paid once per leader term, not once per log entry.

## Leader Election

Basic Paxos has no notion of a leader -- any node can propose at any time, which is why it's correct but chaotic in practice. Multi-Paxos adds an informal leader election layer: one node is designated the distinguished proposer and the others voluntarily defer to it.

"Voluntarily" is the key word. If followers suspect the leader is dead (no heartbeats for a timeout period), any of them can run Phase 1 with a higher ballot to take over. The old leader doesn't get a veto -- it just gets its Accept messages rejected because the acceptors have now promised a higher ballot.

This is where Multi-Paxos implementations diverge significantly. The Paxos paper doesn't specify how leader election works, what timeouts to use, or how to detect a live leader that's just partitioned. Every real implementation makes different choices here, which is part of why Multi-Paxos implementations are hard to compare.

## Log Holes

One complication basic Paxos avoids: with multiple slots running in parallel, you can get holes. The leader accepts slot 1 and slot 3 but slot 2 hasn't been filled yet because a client request was lost. Followers can't apply slot 3 to the state machine without knowing slot 2.

Multi-Paxos implementations handle this with a no-op: when a new leader wins an election, it runs Phase 1 for all uncommitted slots and fills any gaps with a no-op entry. This is what "leader reconciliation" looks like in practice -- the new leader has to figure out what was committed before it took over and resolve any ambiguity.

Raft avoids holes entirely by requiring that the leader always send entries in order, with no gaps. This simplifies the implementation at the cost of some throughput (you can't pipeline out-of-order).

## Zab vs. Multi-Paxos

ZooKeeper uses Zab (ZooKeeper Atomic Broadcast), which is often described as "Paxos-like" but is actually closer to Multi-Paxos with some explicit differences.

The main one: Zab is designed around a primary-backup model where the primary sends updates in a strict FIFO order. The recovery protocol (Phase 1 equivalent in Zab) is designed to ensure the new primary has a superset of all committed entries before it starts serving. Zab also has an explicit synchronization phase where followers sync their logs to the new primary before it starts accepting writes.

Both tolerate the same number of failures and provide the same safety guarantees. The practical difference is that Zab is tuned for ZooKeeper's specific write pattern (broadcast to all followers, wait for majority ack, apply in order) while Multi-Paxos is a more general framework.

## Multi-Paxos vs. Raft

| | Multi-Paxos | Raft |
|---|---|---|
| Leader election | Ad hoc, not specified in paper | Built into protocol with explicit terms |
| Log holes | Possible, requires no-op fill on leader change | Not possible, entries sent in order |
| Pipelining | Supported natively | Requires extensions |
| Understandability | Requires significant paper-reading and inference | Designed to be implementable from the paper alone |
| Real implementations | Chubby (Google), custom variants | etcd, CockroachDB, TiKV, Consul |

Multi-Paxos and Raft have the same fault tolerance and safety properties. The difference is that Raft specifies the things Multi-Paxos leaves up to the implementer -- which is why Raft implementations tend to be more consistent across codebases.

Google's Chubby uses a Paxos variant internally. Google Spanner uses a Paxos variant per shard. In both cases Google built their own leader election and recovery logic on top of the basic protocol -- which is exactly the work Raft was designed to eliminate.
