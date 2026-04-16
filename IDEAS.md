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

---

# Blog Ideas from GitHub Contributions -- April 2026

---

## Idea A: Building AgentBudget -- The ulimit for AI Agents

**Tagline:** How I built a hard-limit cost enforcement SDK for LLM agents, inspired by Unix ulimit.

**Origin:** AgentBudget (github.com/KTS-o7/agentbudget) -- published on PyPI, npm, and Go, multi-maintainer open source project.

**Core angle:**
AI agents can silently burn your entire API budget in a single runaway session. There was no standard primitive to prevent this -- so I built one. AgentBudget monkey-patches OpenAI and Anthropic SDKs at init time (same pattern as Sentry/Datadog) and raises a BudgetExhausted exception the moment a session crosses the dollar threshold.

**Pointers / sections to cover:**
- The problem: why AI agents overspend (unbounded loops, no built-in circuit breaker, streaming cost blindness)
- The ulimit analogy -- why thinking of it as a resource limit for processes is the right mental model
- Architecture: drop-in mode (2-line patch) vs manual mode (context manager), how session.wrap() intercepts responses
- The hard parts: tracking streaming costs (stream_options include_usage), thread safety, OpenRouter model name normalization
- finalization_reserve -- why you need to budget for the last step separately or agents get cut off mid-task
- Multi-language SDKs (Python, Go, TypeScript) -- design decisions for keeping them consistent
- Community PRs: what breaking changes the first contributors found (thread safety, off-by-one, exception handling)
- Metrics: PyPI + npm download counts as social proof

**Target audience:** Backend/ML engineers building or operating LLM agents in production.

**Estimated length:** 1500-2000 words

---

## Idea B: Graph-Based Root Cause Analysis -- A RAG + DAG Approach to Incident Triage

**Tagline:** How I combined causal DAG construction with retrieval-augmented generation to automate log triage.

**Origin:** graph-rca (github.com/KTS-o7/graph-rca) -- academic minor project that grew into a full-stack incident analysis system with evaluation framework.

**Core angle:**
When production breaks, engineers spend most of their time reading logs and correlating events across services. graph-rca takes a log dump, builds a causal Directed Acyclic Graph (DAG) of the incident chain using an LLM parser, then uses RAG against internal documentation to surface resolution steps -- not just what went wrong, but why and how to fix it.

**Pointers / sections to cover:**
- The problem with traditional log analysis: grep-and-pray, no causal structure, no knowledge linkage
- System architecture: log parser (LLM) -> graph_generator.py (DAG) -> context_builder.py (DAG traversal) -> rag.py (ChromaDB) -> resolution output
- Why a DAG beats a flat event list: causal chains surface root cause vs. symptoms, traversal order matters
- The RAG layer: why linking docs to graph nodes beats raw retrieval, what ChromaDB gave us
- Evaluation framework (exp01-exp08): how we built a test harness and real-world dataset to measure accuracy
- Lessons: LLM-based log parsing is surprisingly robust; hardest part is graph edge determination
- What I'd do differently: knowledge graph vs. flat vector store, streaming graph updates for live incidents

**Target audience:** Backend/DevOps/SRE engineers, ML engineers interested in applied RAG.

**Estimated length:** 1800-2200 words

---

## Idea C: From Schema to 50K QPS -- Building a BaaS on Top of MongoDB with Go

**Tagline:** How permission-mongo turns a MongoDB collection config into a fully typed, RBAC-protected REST API in minutes.

**Origin:** permission-mongo (github.com/KTS-o7/permission-mongo) -- Go BaaS with fine-grained RBAC, document versioning, hooks, and Prometheus observability.

**Core angle:**
Most teams rebuild the same CRUD + auth layer for every new MongoDB collection. permission-mongo is the config-driven escape hatch: define your schema in YAML, get a typed REST API with hierarchical role-based access, document versioning, pre/post webhook hooks, and full Prometheus/Grafana observability. Performance target: 50K QPS with <1ms p99 on a single node.

**Pointers / sections to cover:**
- The problem: every MongoDB project reinvents the same CRUD service, auth layer, and audit trail
- Architecture: config schema -> route generation, why fasthttp over net/http, MongoDB driver connection pooling
- RBAC design: hierarchical roles, permission inheritance, per-document-field level access control
- Document versioning: diff + restore implementation, storage trade-offs (append-only vs delta)
- Hooks system: pre/post triggers with HTTP webhook delivery, retry semantics, timeout handling
- Observability: slog structured logging, Prometheus metrics, Grafana dashboard
- Getting to 50K QPS: the perf branch -- fasthttp tuning, connection pool sizing, Redis optional caching
- What I'd add next: GraphQL layer, multi-tenancy, event streaming (CDC)

**Target audience:** Backend engineers using Go + MongoDB, platform engineers building internal tooling.

**Estimated length:** 1600-2000 words

---

## Quick-pick Matrix

| # | Title | Write effort | Audience fit | Uniqueness |
|---|-------|-------------|--------------|------------|
| A | AgentBudget -- ulimit for AI agents | Medium | High (AI/ML eng) | Very high -- novel concept + community traction |
| B | Graph-RCA -- RAG + DAG incident analysis | High | Medium (SRE/ML) | High -- academic + prod hybrid |
| C | permission-mongo -- Schema to 50K QPS BaaS | Medium | High (backend eng) | Medium -- well-trodden space, strong perf angle |

Recommendation: Start with Idea A (AgentBudget). Clear hook, real download metrics, timely AI topic.
Idea C is the easiest to write. Idea B is the most technically interesting.
