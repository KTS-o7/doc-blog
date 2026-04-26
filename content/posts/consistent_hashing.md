+++
title = "Consistent Hashing"
date = 2026-04-26T00:00:00+05:30
draft = false
math = false
+++

The simplest way to distribute keys across N cache nodes is `hash(key) % N`. It works until you add or remove a node.

The moment N changes to N+1 or N-1, almost every key remaps to a different node. You get a thundering herd of cache misses across the entire dataset. The naive approach is fine for static clusters. Real clusters aren't static -- nodes fail, capacity scales up and down, and a single rehash event can saturate every upstream database behind the cache simultaneously.

## The Hash Ring

Consistent hashing fixes this by changing the assignment model entirely.

Instead of modding by N, you arrange all possible hash values on a ring -- 0 to 2^32, wrapping around. Each node gets a position on the ring by hashing its own name or ID. To find which node owns a key: hash the key, then walk clockwise until you hit a node.

```
ring: [0 -------- Node A -------- Node B -------- Node C -------- 2^32]

key hashes to X:   →→→→→→→→→→→ lands on Node B
```

Now add Node D between A and B. Only the keys that land between A and D move -- from B to D. Everything else stays put. You go from ~100% rehash to ~1/N keys moving. Same math applies to removal: only the keys owned by the removed node need to be reassigned to its clockwise successor.

The assignment is stable by construction. You don't need a global coordinator to tell every client about the new mapping -- any client with the same hash function and the same node list will independently arrive at the same answer.

## Virtual Nodes

There's a problem with the basic ring: node positions are determined by hashing node IDs, which produces an uneven distribution. One node might cover a large arc of the ring; another might cover a tiny one. That means uneven load -- and when a lightly-covered node fails, its small slice of keys moves to a neighbor that's already under load.

The fix is virtual nodes. Each physical node gets multiple positions on the ring by hashing it multiple times -- `node1-0`, `node1-1`, `node1-2`, etc. The load spreads more evenly. When a node fails, its load distributes across many different successors rather than piling onto one.

The tradeoff is more ring entries to maintain. In practice this is cheap. Most production systems use 100-200 virtual nodes per physical node. Cassandra lets you tune `num_tokens` (their term for virtual nodes) at the cluster level; the default is 256 per node since Cassandra 4.0.

## What Happens During a Rebalance

Consistent hashing solves *where* a key belongs. It doesn't solve *what happens during the transition*.

When you add a node and ~1/N keys need to move, there's a window where:
- The new node is assigned those keys on the ring
- The data hasn't actually been copied yet
- Reads to the new node miss and fall through to the old owner

Systems handle this differently. Cassandra uses streaming -- new node contacts existing nodes and pulls data for its token ranges before announcing itself ready. DynamoDB uses background rebalancing with handoff acknowledgement. Memcached clients (using ketama) just accept stale misses during the migration window and let the cache warm back up naturally.

The point is that the ring tells you the target state. Getting there without a traffic spike is an operational concern separate from the algorithm.

## Load Hotspots

Consistent hashing assumes uniform key distribution. If your keys aren't uniform -- or if you have genuinely hot keys that receive far more traffic than the average -- the ring doesn't help.

Virtual nodes reduce variance across the normal range of keys. They don't help when 10% of your traffic goes to 0.1% of your keys. That's a different problem: explicit shard splitting, caching at a higher layer, or application-level fan-out.

DynamoDB has adaptive capacity that detects hot partitions and splits them. Cassandra has had issues with hot token ranges for years and the solution is usually application-level key design -- composite keys, write sharding -- rather than a fix at the ring layer.

## Where It Shows Up

Consistent hashing is the routing primitive in almost every large-scale distributed storage system:

- **Amazon DynamoDB** -- keys mapped to vnodes on a ring, each vnode owned by a replica group. Rebalancing happens automatically as the cluster scales.
- **Apache Cassandra** -- the token ring is consistent hashing. Vnodes are on by default since 1.2; Cassandra 4.0 moved to 256 tokens per node as default.
- **Memcached** -- ketama is the consistent hashing client library that standardized this approach for caching. Most client libraries implement it.
- **Redis Cluster** -- uses a variant called hash slots (16384 fixed slots, nodes own ranges of slots). Conceptually the same idea, implemented as a fixed-size ring.

The algorithm itself is from a 1997 paper by Karger et al., written to solve exactly this problem for web caching. The core idea hasn't changed. The production details -- vnode count, rebalancing triggers, hotspot detection, replica placement -- are where the real engineering lives.
