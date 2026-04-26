+++
title = "Raft Consensus"
date = 2026-04-26T00:00:00+05:30
draft = false
math = false
+++

Distributed consensus -- getting a cluster of nodes to agree on a sequence of values, even when some nodes crash -- is a solved problem. The canonical solution is Paxos. The problem with Paxos is that it's famously hard to understand and even harder to implement correctly.

Raft was designed in 2013 specifically to be understandable. Same safety guarantees. Radically different presentation. The paper's introduction literally says: "we had several goals: Raft must be complete and practical... but most importantly, it must be understandable by a large audience."

That goal shapes every design decision in the protocol.

## The Decomposition

Paxos describes consensus as a single unified mechanism with invariants distributed throughout. Raft explicitly breaks it into three independent subproblems and solves each one in isolation:

1. **Leader election** -- at any time, exactly one node is the authority for new log entries
2. **Log replication** -- the leader accepts client writes and drives them to a majority
3. **Safety** -- a node can only become leader if it has all committed entries; committed entries are never lost

This decomposition is the insight. Once you have a stable leader, log replication is almost trivially simple. Once you have log replication, safety falls out of the election constraint. The hard part is the election itself -- and Raft handles it with a clean mechanism rather than leaving it informal.

## Terms and Roles

Raft uses **terms** as its logical clock -- a monotonically increasing integer. Each election starts a new term. Every RPC includes the sender's term. If a node receives a message with a higher term than its own, it immediately updates its term and steps down to follower. Stale leaders don't survive contact with the rest of the cluster.

Every node is in one of three states:

| Role | Responsibility |
|---|---|
| **Follower** | Passive -- responds to leader and candidate RPCs |
| **Candidate** | Temporarily, during an election |
| **Leader** | Accepts client requests, replicates entries, sends heartbeats |

All nodes start as followers. A node becomes a candidate only when it stops hearing from the leader. There is at most one leader per term.

## Leader Election

Followers expect a regular heartbeat from the leader -- an `AppendEntries` RPC with no entries, sent to keep followers from timing out. If a heartbeat doesn't arrive within the **election timeout** (randomized between 150-300ms typically), the follower converts to candidate:

1. Increments its term
2. Votes for itself
3. Sends `RequestVote(term, lastLogIndex, lastLogTerm)` to all other nodes

A node grants a vote if:
- It hasn't voted in this term yet
- The candidate's log is **at least as up-to-date** as its own (more on this below)

The first candidate to collect a majority becomes leader and immediately starts sending heartbeats to suppress any other elections.

**Why randomized timeouts?** If all nodes had the same election timeout, they'd all become candidates simultaneously on every leader failure, split votes, and never elect a leader. The random timeout means one node almost always times out first, starts an election, and collects votes before anyone else has even woken up. Split votes still happen occasionally; both candidates pick new random timeouts and retry with a higher term, so they resolve quickly.

```
All followers, leader goes silent
Node A's timeout fires first (it drew the shortest timeout)
A → Candidate, term=6, votes for self
A → RequestVote(term=6) → B, C, D, E
B: hasn't voted in term 6, A's log is current → grant
C: hasn't voted in term 6, A's log is current → grant
A has 3/5 votes → Leader(term=6) → heartbeats begin
D and E timers never fire
```

## Log Replication

Once a leader exists, writes are straightforward:

1. Client sends a command to the leader
2. Leader appends the entry to its local log (status: **uncommitted**)
3. Leader sends `AppendEntries(prevLogIndex, prevLogTerm, entries[], leaderCommit)` to all followers in parallel
4. Once a **majority** of nodes have written the entry to their logs → leader marks it **committed**
5. Leader applies the entry to its state machine and responds to the client
6. On the next heartbeat, followers learn the new commit index and apply pending entries

```
Client → write x=5 → Leader
Leader → AppendEntries → Follower A ✓ (writes to log)
Leader → AppendEntries → Follower B ✓ (writes to log)
Leader → AppendEntries → Follower C  ✗ (unreachable)
Majority = Leader + A + B → mark committed → apply x=5 → reply to client
Follower C recovers later, leader resends missing entries, C catches up
```

The `prevLogIndex` and `prevLogTerm` fields in AppendEntries are the consistency check. A follower rejects the append if the previous entry in its own log doesn't match. The leader backs up by one and retries. This process finds the last point where the follower's log matches the leader's, and the leader resends everything from there. The leader's log always wins.

## Safety: The Election Constraint

The critical invariant: a node can only win an election if its log is **at least as up-to-date** as a majority of nodes.

"Up-to-date" is a precise comparison:
- Compare the term of the last log entry. Higher term wins.
- If terms are equal, longer log wins.

This guarantees that a newly elected leader always has all committed entries. Here's why: a committed entry was written by a majority. Any election winner collected votes from a majority. Those two majorities must overlap by at least one node. That overlapping node voted for the winner, which means the winner's log was at least as current as that node's -- which means it has the committed entry.

No repair step needed. No "figure out what was committed before my election." The safety guarantee is structural, not procedural.

## Handling Log Divergence

When a leader fails and a new one is elected, some followers may have entries the new leader doesn't have, and vice versa. The resolution: the new leader's log is authoritative. Diverged follower entries are overwritten.

This is safe because of the election constraint -- the new leader has all committed entries. Any entries only on diverged followers were never committed (the old leader hadn't yet received majority acknowledgement), so discarding them is safe.

The AppendEntries consistency check drives the catchup automatically. No explicit repair protocol needed.

## Raft vs. Paxos

| | Paxos (Multi-Paxos) | Raft |
|---|---|---|
| **Design goal** | Correctness | Correctness + understandability |
| **Leader** | Distinguished proposer (informal) | Explicit, enforced by protocol |
| **Log gaps** | Allowed -- slots can be filled out of order | Not allowed -- entries are sequential |
| **Config changes** | Ad hoc, not specified | Joint consensus built into the protocol |
| **Understandability** | Notoriously hard | Designed to be teachable |
| **Key implementations** | Chubby, Zab (variant) | etcd, CockroachDB, TiKV, Consul |

Same fault tolerance: both tolerate up to `⌊(N-1)/2⌋` failures. 3 nodes tolerates 1 failure. 5 nodes tolerates 2. You need a majority of nodes alive to make progress.

## What Raft Doesn't Cover (and Matters for Production)

**Log compaction:** The log grows forever. Snapshots periodically capture the full state machine state and truncate the log prefix. A follower that falls too far behind receives a snapshot instead of individual entries. The Raft paper covers this in the extended version; most implementations handle it, but the details (snapshot transfer, concurrent snapshotting while serving reads) are non-trivial.

**Cluster membership changes:** Adding or removing nodes changes what constitutes a majority. Done naively, this creates a window where two disjoint majorities can exist simultaneously -- a split-brain scenario. Raft's answer is joint consensus: during the transition, a commit requires majority from both the old and new configuration. Implemented in etcd; often the trickiest part of a real Raft implementation.

**Read scaling:** Every read going through the leader is a bottleneck. Follower reads are tempting but require care -- a follower might be behind. Lease-based reads (leader holds a time-bounded lease guaranteeing no other leader exists) allow serving reads without a full round-trip. etcd implements this. The consistency tradeoff is: reads are linearizable only if the lease is valid; clock skew can violate this.

## Where It's Used

- **etcd** -- the backing store for all Kubernetes cluster state. One Raft cluster per etcd deployment; the entire control plane depends on it.
- **CockroachDB** -- Raft per range (shard). Each range is a 3-5 node Raft group. Thousands of Raft groups per cluster.
- **TiKV** (TiDB's storage layer) -- Raft groups per region, same pattern as CockroachDB.
- **Consul** -- service discovery and distributed KV. Single Raft cluster per datacenter.

The algorithm is young -- the paper is from 2013 -- but it has already become the default answer to the question "how does this cluster stay consistent?"
