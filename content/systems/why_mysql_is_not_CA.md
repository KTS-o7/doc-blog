+++
title = 'Why MySQL is not CA'
date = 2025-09-05T07:07:07+01:00
draft = false
math = true
+++

---
## motivation

I was recently discussing with my CTO about databases. There was one point where we were thinking about the `CAP` theorem.
Then he randomly mentioned that MySQL is not CA. I was surprised because I always thought that MySQL is a CA database at its core.

Now I had to search and understand why MySQL is not CA.

---
## CAP theorem

![CAP theorem](https://substackcdn.com/image/fetch/$s_!cOsx!,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F869db2d6-6133-411e-96ad-cc1c52611778_800x472.png)

We have always been taught in Engineering that CAP is one of the most important theorems in distributed systems and databases. We just accepted it. Time to question and learn ┏ʕ •ᴥ•ʔ┛

Here is what it actually means.

Imagine a bank server, when you check your account balance it should not randomly change it based on the server you are hitting and it should be consistent across all nodes. But in a distributed system, network failures (partitions) can occur. The CAP theorem states that you can only guarantee 2 out of 3 properties:

- **Consistency (C)**: All nodes see the same data at the same time
- **Availability (A)**: Every request receives a response, even if it's not the most recent data  
- **Partition Tolerance (P)**: The system continues to operate despite network partitions

Here are practical examples of each combination:

### CA Systems (Consistent + Available, but not Partition Tolerant)
`Example: Traditional Relational Databases (like PostgresSQL in single-node setups)`

Imagine a single PostgresSQL database server in a bank. When you check your balance:
- **Consistency**: Every time you query your balance, you get the exact same amount ($100.00)
- **Availability**: The system always responds to your requests
- **Partition Tolerance**: If the network connection to the database fails, you can't access your account

This works perfectly in non-distributed environments, but fails when you need to scale across multiple data centers.

### CP Systems (Consistent + Partition Tolerant, but sacrifices Availability)
`Example: Apache ZooKeeper or etcd`

Imagine a distributed configuration management system like ZooKeeper:
-  **Consistency**: All nodes agree on configuration values (like which server is the leader)
-  **Partition Tolerance**: If some nodes lose network connectivity, the remaining nodes continue operating
-  **Availability**: During a network partition, some requests might be blocked to maintain consistency

In a ZooKeeper cluster, if a majority of nodes become unreachable, the system stops accepting writes to prevent inconsistent states.

### AP Systems (Available + Partition Tolerant, but sacrifices Consistency)
`Example: Amazon DynamoDB or Cassandra`

Imagine a social media platform's like counter system:
-  **Availability**: The system always responds to requests, even during network failures
-  **Partition Tolerance**: The system continues operating across multiple data centers despite network issues
-  **Consistency**: During partitions, you might see different like counts on different servers

You might see a post with 100 likes on one page refresh, then 102 likes on the next refresh, as the systems reconcile the differences asynchronously.

--- 

### Why MySQL is not CA

While MySQL can achieve CA in single-node deployments, it cannot be truly CA in distributed scenarios. When you add MySQL replicas or clustering solutions like MySQL Group Replication:

- During network partitions, MySQL must choose between consistency (rejecting writes) or availability (allowing potentially conflicting writes)
- MySQL's synchronous replication can become unavailable during partitions if strict consistency is enforced
- Traditional asynchronous replication trades consistency for availability (so it becomes AP, not CA).
Even with semi-sync replication, MySQL typically prioritizes availability over strict consistency—clients may see stale reads.

It doesn’t enforce strong ACID guarantees across replicas the way PostgreSQL doe

### Why PostgreSQL is considered CA

Postgres in standalone mode: Definitely CA (strong ACID, always responds if node is up).

In replication setups:

PostgreSQL replication (especially with synchronous replication) prioritizes consistency first.
A commit can be acknowledged only after replicas confirm the write (if you configure synchronous replication).

This means if replicas aren’t reachable, Postgres will prefer not to serve stale data (sacrificing availability to preserve consistency).

So Postgres is effectively CA (or CP in distributed setups).

This is why distributed databases like CockroachDB or TiDB are often preferred for truly distributed, partition-tolerant systems. 

---
ʕ ● ᴥ ●ʔ