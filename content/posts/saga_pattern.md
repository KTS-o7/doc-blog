+++
title = "The Saga Pattern"
date = 2026-04-26T00:00:00+05:30
draft = false
math = false
+++

Two-Phase Commit gives you distributed atomicity. The cost is a coordinator that can crash and leave every participant locked indefinitely. For short transactions inside a single system, that's acceptable. For a multi-step flow that touches five separate microservices over several seconds, it isn't.

The Saga pattern is the practical answer: break the distributed transaction into a sequence of local transactions, and define a compensation for each step. If something fails halfway through, run the compensations in reverse. No global lock. No blocking coordinator. Just a cleanup plan.

## The Basic Mechanics

A saga is a sequence of steps, each executed by a single service as a local transaction:

```
Step 1: Reserve flight    → local tx in Flight Service
Step 2: Reserve hotel     → local tx in Hotel Service
Step 3: Charge card       → local tx in Payment Service
```

Each step succeeds or fails independently. If Step 3 fails after Steps 1 and 2 have already committed:

```
FORWARD:  [Flight ✓] → [Hotel ✓] → [Payment ✗]
ROLLBACK:             ← [Cancel Hotel] ← [Cancel Flight]
```

The compensation for "reserve flight" is "cancel flight". The compensation for "reserve hotel" is "cancel hotel". Each service is responsible for knowing how to undo itself.

This is fundamentally different from a database rollback. There's no global transaction log. The compensations are domain-level operations that must be designed and implemented explicitly.

## Two Coordination Models

### Choreography

Each service listens for events on a message bus and decides what to do next based on what it hears. No central coordinator. The saga emerges from the interaction of independent services.

```
Payment Service emits "payment_failed"
→ Hotel Service hears it, cancels reservation, emits "hotel_cancelled"
→ Flight Service hears it, cancels reservation, emits "flight_cancelled"
→ Done
```

Works well at small scale. At large scale the flow becomes hard to trace -- debugging a failure means correlating events across N services, each with its own logs, each with its own notion of what happened.

### Orchestration

A dedicated saga orchestrator drives the sequence. It tells each service what to do, collects the result, and issues compensating calls on failure.

```
Orchestrator → "reserve flight" → Flight Service → ✓
Orchestrator → "reserve hotel"  → Hotel Service  → ✓
Orchestrator → "charge card"    → Payment Service → ✗
Orchestrator → "cancel hotel"   → Hotel Service  → ✓
Orchestrator → "cancel flight"  → Flight Service  → ✓
```

The orchestrator has a complete view of the saga's state at every point. Debugging is straightforward -- query the orchestrator. The tradeoff is that the orchestrator becomes a coordination hub. It doesn't become a single point of failure (it can be replicated), but it becomes a complexity center that needs its own testing, monitoring, and failure handling.

Most teams end up at orchestration. The debugging clarity is worth the overhead.

## The Isolation Problem

Sagas trade isolation for availability. This is the most important tradeoff to understand, and the one that bites teams who treat sagas as a drop-in replacement for 2PC.

While a saga is in flight, intermediate state is visible. After Step 1 and Step 2 succeed but before Step 3, there is a committed hotel reservation and a committed flight reservation with no corresponding payment. Other services can see that state. If another saga is running concurrently, it might observe that hotel room as unavailable.

This is the "lost isolation" in ACID. You're operating under eventual consistency -- the system will eventually reach a correct state (either fully committed or fully compensated), but it doesn't happen atomically.

The implications:

- **Compensating transactions must be idempotent.** A "cancel hotel" that gets called twice due to a retry must not double-cancel or throw an error. Design them to be safe to execute multiple times.
- **Compensating transactions must be commutative where possible.** The order of compensations shouldn't matter.
- **Read-your-writes guarantees go away across service boundaries.** A user might see a confirmed booking briefly, then see it cancelled. Design your UX accordingly.

## Compared to 2PC

| Property | 2PC | Saga |
|---|---|---|
| Atomicity | Global | Per-step only |
| Isolation | Full | Intermediate state visible |
| Availability | Blocks on coordinator failure | Always makes progress |
| Scalability | Locks across services | No cross-service locks |
| Failure model | Coordinator SPOF | Each step can fail independently |

There's no correct choice that applies everywhere. 2PC is right when you need strict atomicity and the transaction is short-lived. Sagas are right when you need availability and the steps are long-lived or span service boundaries.

## What Production Looks Like

The saga pattern shows up in basically every large-scale order/booking/fulfillment system:

- **Uber** -- a ride request touches driver matching, pricing, payment authorization, and notification services. Each is a local transaction. Driver matching failures trigger compensation in pricing, and so on.
- **Amazon** -- order placement reserves inventory, authorizes payment, and initiates fulfillment. Each step can fail and be compensated independently.
- **Netflix** -- subscription management spans billing, entitlement, and content licensing. Saga orchestration drives the transitions.

The implementation details vary, but the pattern is the same: local transactions, explicit compensations, an orchestrator or event bus to drive the flow.

## The Part Nobody Tells You

Designing the happy path of a saga is easy. Designing the compensation path is where it gets hard.

Compensation failures are the edge case that most teams underspecify. What happens when the "cancel hotel" compensation call itself fails? You need a retry strategy, a dead-letter queue, and a manual intervention path for cases that can't self-heal. The saga state machine needs to persist its progress durably -- if the orchestrator crashes mid-saga and restarts, it must be able to resume from where it left off without re-running already-completed steps.

The outbox pattern is the standard solution for durability: instead of calling the next service directly, the orchestrator writes the next command to a local database table in the same transaction that records the current step's result. A separate process reads the outbox and delivers the command. This guarantees at-least-once delivery without distributed transaction semantics.

A saga without durable state and idempotent compensations is a saga that will eventually corrupt data in production.
