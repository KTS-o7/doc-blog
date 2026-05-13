+++
title = "Raft: Consensus for the Rest of Us"
date = 2026-05-02T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "Raft is a consensus algorithm designed for understandability — leader election, log replication, and safety properties explained, with a comparison to Paxos."
tags = ["distributed-systems", "consensus", "raft", "replication"]
+++

Paxos is the algorithm everyone cites and almost nobody implements correctly. The gap between the paper and a working, production-safe implementation is wide enough that teams have shipped subtly broken versions without knowing it for months.

Raft was built as a direct response to that. Same safety guarantees, designed from scratch for understandability -- the explicit goal was that a student should be able to implement it correctly from the paper alone.

It works. etcd runs on it. Kubernetes' entire cluster state lives in etcd. CockroachDB uses a Raft group per range. TiKV, Consul -- Raft is everywhere Paxos was supposed to be.

## The Decomposition

Raft's core move is breaking consensus into three subproblems that can be understood and implemented independently:

1. Leader election -- pick one node as leader at any time
2. Log replication -- leader accepts entries, replicates to followers
3. Safety -- no two nodes ever commit conflicting entries

Everything flows through a single leader. There's no "any node can propose" ambiguity like in basic Paxos. The leader is the sole source of truth for what enters the log. That constraint makes the rest of the protocol tractable.

## Terms and Roles

Raft uses a logical clock called a **term** -- a monotonically increasing integer. Each election starts a new term. If a node sees a message from a higher term than its own, it immediately updates and steps down if it was leader. Terms are how stale leaders get detected and evicted.

Every node is one of three things at any moment:

- **Leader** -- accepts client requests, replicates entries, sends heartbeats to prevent new elections
- **Follower** -- passive, responds to RPCs from leaders and candidates
- **Candidate** -- transitional state during an election

Every node starts as a follower.

## Leader Election

Followers expect periodic heartbeats from the leader via AppendEntries RPCs (sent even when there are no entries to replicate). If an election timeout fires without a heartbeat, the follower converts to a candidate:

1. Increment current term, vote for self
2. Send RequestVote to all peers
3. A peer grants its vote if it hasn't voted this term and the candidate's log is at least as up-to-date as its own
4. First candidate to collect a majority wins, becomes leader, starts sending heartbeats immediately

Split votes happen when two candidates start elections simultaneously and each gets half the cluster. Neither reaches majority. Both time out and retry with a new term. Raft handles this with randomized election timeouts (typically 150--300ms) -- making simultaneous timeouts unlikely without coordination overhead.

## Log Replication

Once a leader is elected:

1. Client sends a command to the leader
2. Leader appends the entry to its local log (not yet committed)
3. Leader sends AppendEntries to all followers in parallel
4. Once a majority have written the entry, the leader marks it committed
5. Leader applies the entry to its state machine, replies to client
6. On the next heartbeat, followers learn the commit index and apply the entry too

```
Client → [write x=5] → Leader
Leader  → AppendEntries(x=5) → Follower A  ✓
Leader  → AppendEntries(x=5) → Follower B  ✓
Leader  → AppendEntries(x=5) → Follower C  (unreachable)
[Majority = Leader + A + B → COMMIT] → apply x=5
```

Follower C is behind but not a problem. When it reconnects, the leader sends it the missing entries.

## Safety: Log Matching

Raft's key safety property: if two logs contain an entry with the same index and term, all preceding entries are identical.

This is enforced by the AppendEntries consistency check. When the leader sends an entry, it includes the index and term of the entry immediately before it. A follower rejects the append if that preceding entry doesn't match its own log. The leader then backs up and resends from an earlier point until it finds a common prefix, then overwrites the diverged entries.

The vote restriction reinforces this: a node won't vote for a candidate whose log is less up-to-date than its own. This guarantees the new leader always has all committed entries -- it never needs to fetch missing entries from other nodes after winning an election.

## Leader Failure

If the leader crashes, the election timeout fires on one of the followers and a new election starts. The vote restriction ensures the winner has the most complete log among the majority. No repair phase, no querying all nodes -- safety comes from the constraint, not from post-election cleanup.

## Raft vs. Paxos

| | Multi-Paxos | Raft |
|---|---|---|
| Design goal | Correctness | Correctness + understandability |
| Leader | Distinguished proposer (informal) | Explicit, enforced by protocol |
| Log holes | Can have gaps, complex to fill | No gaps, entries apply in order |
| Config changes | Ad hoc | Joint consensus built in |
| Implementations | Chubby, Zab (variants) | etcd, CockroachDB, TiKV, Consul |

Both tolerate up to (N-1)/2 failures in an N-node cluster. The fault tolerance is identical. The difference is that Raft implementations are actually correct in practice because the protocol is debuggable.

## Where It Runs

- **etcd** -- Kubernetes' backing store; the entire cluster state (pods, services, configs) is a Raft log
- **CockroachDB** -- Raft per range; each 512MB range is an independent 3--5 node Raft group
- **TiKV** -- Raft groups per region, underpins TiDB
- **Consul** -- service discovery and distributed KV

If you're building anything that needs replicated state and strong consistency, Raft is the default answer. The paper is readable in an afternoon. The TLA+ spec exists if you want to verify your implementation. Start there.
