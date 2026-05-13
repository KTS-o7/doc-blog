+++
title = "The Saga Outbox Pattern: Reliable Event Delivery Without Two-Phase Commit"
date = 2026-05-03T00:00:00+05:30
draft = false
math = false
author = "Krishnatejaswi S"
description = "The outbox pattern solves the dual-write problem in event-driven systems: persist events to a local outbox table in the same transaction as your domain change, then relay them reliably."
tags = ["distributed-systems", "patterns", "saga", "event-driven", "databases"]
+++

The Saga pattern gives you distributed transactions without cross-service locks. Each step publishes an event when it completes, triggering the next step. But there's a gap in the naive implementation: publishing an event and updating your local database are two separate operations. If your service crashes between them, you get a committed database write with no event published, or an event published with no matching database write. The saga is now in an inconsistent state.

The outbox pattern closes that gap.

## The Dual-Write Problem

Say the flight reservation step succeeds. You update your database to mark the reservation as confirmed and then publish a `FlightReserved` event to your message broker. These are two operations against two different systems. There's no way to make them atomic without 2PC -- which is exactly what sagas are trying to avoid.

If you write to the database first and then crash before publishing, the event is never delivered. The hotel reservation step never starts. The saga stalls. Depending on your monitoring, this might sit undetected for a while.

If you publish first and then crash before writing to the database, you've told the hotel step to proceed even though the flight reservation isn't durably recorded. The flight service comes back up with no record of the reservation. You've introduced a phantom.

## The Outbox

The fix: write the event to an outbox table in the same database, in the same local transaction as your state update. Then have a separate process relay events from the outbox to the message broker.

```
BEGIN TRANSACTION
  UPDATE flights SET status = 'reserved' WHERE id = ?
  INSERT INTO outbox (event_type, payload, created_at)
    VALUES ('FlightReserved', '{"booking_id": 123, ...}', NOW())
COMMIT
```

The state change and the event are now atomic with respect to the database. Either both are committed or neither is. The outbox row is durable.

A separate relay process -- sometimes called the outbox processor or message relay -- polls the outbox table, publishes each event to the message broker, and marks the row as processed once delivery is confirmed.

```
Relay process:
  SELECT * FROM outbox WHERE processed_at IS NULL ORDER BY created_at LIMIT 100
  FOR EACH row:
    publish to message broker
    UPDATE outbox SET processed_at = NOW() WHERE id = row.id
```

## At-Least-Once Delivery

The relay delivers at-least-once. If the relay crashes after publishing but before marking the row as processed, it will publish the same event again on restart. Downstream consumers have to be idempotent -- processing the same event twice should produce the same result as processing it once.

This is a real design constraint. Your hotel reservation step needs to check whether it already processed a given `FlightReserved` event before creating a new reservation. Deduplication is typically done with a unique constraint on the event ID or booking ID in the receiving service's database.

At-least-once with idempotent consumers is the standard contract in event-driven systems. Exactly-once is theoretically possible with additional coordination but practically rare -- most systems accept at-least-once and invest in idempotency instead.

## Change Data Capture as an Alternative Relay

Polling the outbox table works but adds load to the database. An alternative is Change Data Capture (CDC): instead of a polling process, you read directly from the database replication log.

Tools like Debezium connect to PostgreSQL's logical replication stream or MySQL's binlog and emit a change event for every row insert. Point Debezium at the outbox table and it publishes events automatically, with no polling query needed.

CDC-based relay has lower overhead and lower latency. The tradeoff: it's another piece of infrastructure to run and operate. For smaller deployments, polling is simpler. For high-throughput systems where polling lag or database load is a concern, CDC is worth it.

## Saga State Persistence

Related to the outbox is the question of where saga state itself lives.

The orchestrator driving the saga needs to know the current step, which steps have completed, and what the compensating actions are if something fails. Two common approaches:

**Dedicated saga store**: the orchestrator writes saga state to its own database table after each step. Simple, queryable, easy to inspect when debugging a stuck saga. The outbox pattern applies here too -- saga state update and event publish happen in the same transaction.

**Event sourcing**: saga state is derived from the event log itself. There's no explicit state table -- you reconstruct the saga's current position by replaying events. More complex to implement but gives you a full audit trail of everything that happened and an easy path to replaying failed sagas.

Most teams start with a dedicated saga store and move to event sourcing only if they need the audit trail or replay capability.

## What Fails in Compensation

One more gap worth naming: compensating transactions can fail too.

You cancel the hotel reservation as part of rolling back a failed booking. The cancel call times out. Now your saga is stuck in a partially compensated state -- the flight is cancelled but the hotel reservation is still live.

The standard answer is retry with backoff. Compensating transactions need to be idempotent for the same reason forward steps do. The outbox pattern helps here too -- compensation requests go through the same outbox mechanism, so they're durably enqueued even if the downstream service is temporarily unavailable.

If compensation keeps failing after retries, the saga is in a "saga failure" state that requires human intervention or a dead-letter queue. Building an operator UI for stuck sagas is not glamorous work, but it's necessary in any production saga implementation.

The outbox pattern doesn't make sagas simple. It removes the dual-write problem and gives you reliable event delivery -- which turns a fundamentally broken approach into one that's merely complex.
