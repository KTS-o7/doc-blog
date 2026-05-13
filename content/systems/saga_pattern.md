+++
title = "The Saga Pattern: Distributed Transactions Without the Lock"
date = 2026-05-02T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "The Saga pattern manages distributed transactions across microservices without 2PC — a sequence of local transactions with compensating actions for rollback when a step fails."
tags = ["distributed-systems", "patterns", "saga", "microservices"]
+++

Two-phase commit gives you distributed atomicity. It also gives you a coordinator that can stall your entire system if it crashes at the wrong moment, and locks held across multiple services for however long the transaction takes. For short, internal transactions that's manageable. For a trip booking flow that touches a flight service, a hotel service, and a payment service -- each owned by a different team, each potentially slow -- it's not.

The Saga pattern is the alternative. You give up true atomicity in exchange for availability, scalability, and no cross-service locks.

## How It Works

Break one big distributed transaction into a sequence of local transactions, each owned by a single service. Each step publishes an event or sends a message when it completes. If any step fails, run compensating transactions in reverse to undo the completed steps.

The classic example is a trip booking:

```
Step 1: Reserve flight    → local tx in Flight Service
Step 2: Reserve hotel     → local tx in Hotel Service
Step 3: Charge card       → local tx in Payment Service
```

If step 3 fails:

```
FORWARD:   [Flight ✓] → [Hotel ✓] → [Payment ✗]
ROLLBACK:              ← [Cancel Hotel] ← [Cancel Flight]
```

No global rollback. No coordinator holding locks across all three services. Each service knows how to undo its own step.

## Two Flavors

**Choreography** -- each service listens for events and decides what to do next based on what it hears. No central coordinator. Fully decoupled. Easy to start, and a debugging nightmare once you have more than a handful of services. Tracing a failed saga means reconstructing a sequence of events scattered across multiple event streams.

**Orchestration** -- a central saga orchestrator drives the sequence. It tells each service what to do, collects results, and issues compensating calls on failure. Full visibility into saga state. Easier to reason about and monitor. The orchestrator becomes a coordination hub -- not quite a single point of failure if you make it durable, but a complexity center. Most teams end up here in production.

## The Tradeoff You Can't Avoid

Sagas trade the "I" in ACID (isolation) for availability. While a saga is in-flight, intermediate state is visible to other parts of the system. A hotel room might be reserved even though the flight hasn't been confirmed yet. Other services can observe that state.

You have to design for this explicitly:

- **Eventual consistency** -- the system converges to a correct final state, but not atomically
- **Idempotent compensating transactions** -- if your "cancel flight" call gets retried twice due to a network hiccup, it must be safe to run twice. Compensation that isn't idempotent will make your failure recovery worse than the original failure.

| Property | 2PC | Saga |
|---|---|---|
| Atomicity | Global | Per-step only |
| Isolation | Full | Intermediate state visible |
| Availability | Blocks on coordinator failure | Always makes progress |
| Scalability | Locks across services | No cross-service locks |

## Where It Shows Up

Basically every large-scale order or booking flow:

- **Uber** -- ride booking, driver assignment, payment charge, all as separate service transactions
- **Amazon** -- order placement, inventory reservation, fulfillment, shipping
- **Netflix** -- subscription management, content licensing flows

These systems can't afford to hold cross-service locks for the duration of a user-facing transaction. They accept that intermediate states exist and design their compensating logic carefully.

The saga pattern doesn't make distributed transactions easy. It makes the tradeoffs explicit and gives you a way to build systems that stay available even when individual steps fail.
