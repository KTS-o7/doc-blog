+++
title = "Consistent Hashing: Scaling a Cluster Without Reshuffling the World"
date = 2026-05-02T00:00:00+05:30
draft = false
math = false
+++

The naive approach to distributing keys across N cache nodes is `hash(key) % N`. It works fine until you add or remove a node.

When N changes to N+1 or N-1, nearly every key remaps to a different node. You go from a warm cache to a cold one in an instant -- a thundering herd of cache misses hitting your database all at once. For a large cluster, that's enough to take down a service.

Consistent hashing fixes this. Add or remove a node, and only the keys that were assigned to that node need to move. Everything else stays put.

## The Hash Ring

Instead of `hash(key) % N`, arrange all possible hash values on a ring from 0 to 2^32. Each node gets a position on the ring by hashing its name or ID. To find which node owns a key: hash the key, then walk clockwise around the ring until you hit a node.

```
          0
         / \
    Node C   Node A
       |         |
    Node B --- Node D
```

Key K hashes to a point on the ring. The first node clockwise from that point owns K.

Now add a new node between B and C. Only the keys that were between B and the new node's position need to move -- from C to the new node. Everything else is unaffected. In an N-node cluster, adding one node moves roughly 1/N of the keys instead of nearly all of them.

## Virtual Nodes

Raw consistent hashing has a load distribution problem. With a small number of physical nodes, the gaps between them on the ring are uneven -- one node might own 30% of the keyspace, another 10%. Remove a node and all its load lands on a single neighbor.

Virtual nodes fix this: each physical node gets multiple positions on the ring, typically by hashing it with different suffixes (`node1-0`, `node1-1`, `node1-2`, ...). With enough virtual nodes per physical node, the load distributes evenly across the ring. Removing one node scatters its keys across many neighbors rather than dumping them all on one.

This is the production configuration in every serious deployment.

## Where It's Used

- **Amazon DynamoDB** -- consistent hashing across storage nodes, virtual nodes for even distribution
- **Apache Cassandra** -- the token ring is consistent hashing; each node owns a range of tokens
- **Memcached** -- the ketama client implements consistent hashing for cache node assignment
- Basically every distributed cache or storage system that needs to scale nodes without full reshuffling

The pattern generalizes beyond caching. Any system that needs to assign work or data to nodes -- and occasionally add or remove nodes -- runs into the same problem. Consistent hashing is the standard solution.
