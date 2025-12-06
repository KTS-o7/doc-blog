# Study & Writing Ideas - Non-Mainstream Topics 🚀

> 10 deep, less-commonly-covered topics that will make you a better engineer

---

## 1. **CRDTs (Conflict-Free Replicated Data Types)**
Why eventual consistency doesn't have to mean conflicts. How collaborative editors (like Google Docs), distributed databases, and real-time systems use CRDTs to merge changes without conflicts. Deep dive into operation-based vs state-based CRDTs, vector clocks, and practical implementations.

---

## 2. **Database Write-Ahead Log (WAL) Internals**
How databases guarantee durability and enable crash recovery. The mechanics of WAL, checkpointing, log replay, and how this enables features like point-in-time recovery. Compare implementations across PostgreSQL, MySQL, and MongoDB.

---

## 3. **Idempotency Keys in Distributed Systems**
Beyond "just use UUIDs" - how payment systems, APIs, and distributed services guarantee exactly-once semantics. Idempotency key strategies, storage patterns, expiration policies, and real-world failure scenarios.

---

## 4. **Python's Descriptor Protocol**
The magic behind `@property`, `@staticmethod`, and ORM field definitions. How descriptors enable elegant APIs, lazy evaluation, and data validation. Build a mini-ORM using descriptors.

---

## 5. **Bloom Filters: When Approximate is Better**
Why sometimes "maybe" is faster than "definitely". How databases use bloom filters for index lookups, how CDNs use them for cache optimization, and when approximate data structures outperform exact ones.

---

## 6. **Split-Brain Scenarios in Distributed Systems**
What happens when network partitions create multiple "leaders"? How systems detect and resolve split-brain, the trade-offs between availability and consistency, and real-world examples of split-brain failures.

---

## 7. **Event Sourcing: Storing Events, Not State**
Building systems that store what happened, not what is. How event sourcing enables audit trails, time travel debugging, and complex business logic. Trade-offs, snapshot strategies, and when to use it vs traditional CRUD.

---

## 8. **Database Connection Pool Exhaustion**
Why "just increase the pool size" doesn't work. Understanding connection lifecycle, pool sizing strategies, connection leaks, and how to diagnose and fix pool exhaustion in production.

---

## 9. **The Actor Model: Concurrency Without Locks**
How Erlang/Elixir achieve fault tolerance through message passing. Actor model principles, supervision trees, "let it crash" philosophy, and when actor-based systems outperform traditional threading models.

---

## 10. **Read-After-Write Consistency in Distributed Systems**
Why reading your own writes isn't guaranteed in distributed databases. Strategies like sticky sessions, timeline consistency, and causal consistency. How major systems (DynamoDB, MongoDB) handle this challenge.

---

*Each topic should be explored deeply enough that someone else can learn from your writing.* ʕ •ᴥ•ʔ
