+++
title = "Circuit Breakers: The Pattern That Stops Cascading Failures"
date = 2026-05-02T00:00:00+05:30
draft = false
math = false
+++

The payment service starts timing out. The fraud detection API it depends on is slow. Your retry logic kicks in -- which makes sense, retries are good -- but now every incoming request is spawning 3x the load on a service that was already struggling. The fraud service falls over completely. Now the entire checkout flow is dead.

This is a cascading failure. One slow dependency turned into a full outage because the upstream service kept hammering it instead of stopping.

## The Pattern

Circuit breakers fix this by failing fast. The name comes from electrical circuit breakers: when the current exceeds a threshold, the breaker trips and cuts power before anything burns. Same idea here.

The circuit has three states:

**Closed** -- normal operation. Requests go through, failures are counted. When failures cross a configured threshold within a time window, the circuit trips.

**Open** -- the circuit has tripped. Requests immediately return an error without calling the downstream service at all. No network round-trips, no timeouts, no extra load on a service that's already struggling. After a cooldown period, the circuit moves to half-open.

**Half-open** -- one test request is allowed through. If it succeeds, the circuit closes and normal operation resumes. If it fails, the circuit trips back to open and the cooldown resets.

The key insight is that sometimes the most useful thing you can do is stop trying. Retrying a failing service doesn't help it recover. Backing off does.

## Where You'll Find It

Netflix Hystrix made this pattern famous, but it's now table stakes in most infrastructure:

- Istio has it built into the service mesh at the sidecar level -- no application code needed
- Resilience4j for Java
- Polly for .NET
- Most Redis clients ship with circuit breaking on connection failures

The mesh-level implementations are interesting because they work across languages and don't require every service team to implement the pattern themselves. You configure thresholds in the mesh and it handles the state machine.

## The Gotcha: Timeout Ordering

There's one configuration mistake that makes circuit breakers useless: setting your request timeout longer than your circuit breaker's failure window.

If your timeout is 30 seconds but your circuit breaker trips after 5 failures within 10 seconds -- and each failure takes 25 seconds to time out -- you'll accumulate only one or two failures in any 10-second window. The circuit never trips because failures arrive too slowly to hit the threshold, even while the system is drowning in slow requests.

The rule: timeouts must be shorter than the failure window. If your breaker watches a 10-second window and trips at 5 failures, your per-request timeout needs to be well under 2 seconds. Otherwise the breaker is just decorative.
