+++
title = "Raft Log Compaction: Keeping the Log from Growing Forever"
date = 2026-05-03T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "Raft logs grow forever if left unchecked. Log compaction via snapshots lets nodes discard old entries, transfer state to slow followers, and recover quickly after a restart."
tags = ["distributed-systems", "consensus", "raft", "replication"]
+++

Raft's correctness relies on the log. Every state change is appended to it, replicated to a majority, and then applied to the state machine. This works perfectly until you've been running for a few months and the log has millions of entries. Replaying the full log on every restart is slow. A new node joining the cluster would have to receive and apply every entry since the beginning of time.

Log compaction is how you fix this. The idea is simple: once a prefix of the log has been applied to the state machine, you don't need the individual entries anymore -- just a snapshot of the state at that point.

## Snapshots

A snapshot captures the complete state machine state at a given log index. Once the snapshot is written, all log entries up to and including that index can be discarded.

```
Before compaction:
  Log: [1: set x=1] [2: set y=2] [3: set x=3] [4: del y] [5: set z=1]
  Applied through index 4
  State machine: {x: 3, z: 1}

After compaction:
  Snapshot at index 4: {x: 3}  (z not in snapshot -- set z=1 not yet applied)
  Remaining log: [5: set z=1]
```

Wait -- index 5 is retained because it hasn't been applied yet when the snapshot is taken. The snapshot covers only committed, applied entries.

The snapshot metadata includes the last included index and last included term. These replace the log prefix. When AppendEntries includes a consistency check against the entry before the new one, the leader uses the snapshot's last index and term as the baseline when the follower's log has been compacted past that point.

## When to Snapshot

Most implementations trigger a snapshot when the log grows past a size threshold -- say 64MB or 256MB. The Raft paper leaves this as an implementation detail. etcd uses 100MB by default. Smaller thresholds mean more frequent snapshots and less log replay on restart, but snapshot creation has a cost.

Taking a snapshot of a large state machine can be expensive. If you're snapshotting a database with gigabytes of data, the snapshot itself might take seconds. During that time the state machine is typically paused or copy-on-write semantics are used to take a consistent point-in-time snapshot without stopping serving. Most production implementations use copy-on-write (fork on Linux makes this cheap for process-based state machines).

## InstallSnapshot RPC

Snapshots matter most for a new node joining the cluster or a node that has been down for a long time and fallen significantly behind.

If a follower is so far behind that the leader has already compacted the log entries it needs, AppendEntries won't work -- those entries are gone. Instead the leader sends the snapshot directly with InstallSnapshot RPC.

The follower receives the snapshot, writes it to stable storage, discards its entire existing log, and resets its state machine to the snapshot state. After that it can receive normal AppendEntries for the remaining log entries.

InstallSnapshot is also used when a brand new node joins the cluster. Rather than replaying potentially years of log history, the leader sends the current snapshot and the follower catches up from there.

## etcd in Practice

etcd runs a snapshot at 100MB by default (configurable with `--snapshot-count`, which actually counts committed entries, not bytes -- the default is 10,000 entries). After snapshotting, etcd retains the last 5 snapshots and the WAL (write-ahead log) segments needed to replay from the oldest retained snapshot. This gives you a window of history for debugging without storing the full log.

etcd also exposes the snapshot mechanism for operator use. `etcdctl snapshot save` takes a snapshot of the current state to a file. This is the recommended backup mechanism for etcd clusters -- you back up the snapshot, not the raw data directory.

## Leader Leases and Linearizable Reads

One related problem: reads in a basic Raft cluster go through the leader, which needs to confirm it's still the leader before responding. The way to confirm is to send a heartbeat round to a majority before responding to a read -- which is an extra round-trip per read, expensive under load.

Leader leases are the optimization. When a leader wins an election and sends its first heartbeats, it records the time and grants itself a lease for a fixed duration (typically the election timeout). During that window, it's guaranteed to still be the leader -- any new leader would need a full election timeout to emerge. So it can serve reads locally without a heartbeat round.

The caveat: lease-based reads depend on the leader's clock being accurate relative to other nodes. If a leader's clock runs fast and its lease hasn't actually expired on other nodes' clocks while it thinks it has, you can serve stale reads. etcd uses clock bounds and makes the lease duration conservative to avoid this. In practice, lease reads are the default in most etcd deployments because the latency benefit outweighs the theoretical risk on well-synchronized hardware clocks.

Raft's log compaction is not exciting to implement but it's essential for production deployments. A cluster without snapshot support will eventually fall over under its own log weight -- or force every new node to replay history from the beginning, which is equally untenable.
