+++
title = "SSE in FastAPI: The Tab Closed and My “Done” Code Never Ran"
date = 2026-01-23T00:00:00+00:00
draft = false
math = false
+++

I hit this bug the annoying way.

A coworker said: “I ran task generation, closed the tab, and the status never moved.”

My first reaction was “no way.” The backend is doing the work, not the browser.

Turns out… yeah. It was right. And once you see why, you stop trusting “code after the stream” forever.

This post is about a very specific trap:

- you stream progress with SSE from a FastAPI endpoint
- you put important side effects *after* the streaming loop (DB status updates, poller kickoff, Slack notifications)
- a client disconnect cancels the stream
- your “after the loop” code never runs

It doesn’t always fail. It fails just enough to make you doubt your own system.

## What the system looked like (so you don’t think this is a demo problem)

We had a step-based pipeline. Each step was triggered by an HTTP call from the frontend and did a few things:

1. Receive a request like `POST /process-timeline-done` (or similar)
2. Start a long-ish worker (in our case an AI agent, but it could be anything)
3. Stream progress back to the UI via **Server‑Sent Events**
4. Update state in MongoDB (advance a status field)
5. Submit an external job
6. Start a long poller to watch that job (hours sometimes)
7. Send a Slack notification

Only (3) needs a live HTTP connection. The rest should be able to finish even if the user refreshes or closes the tab.

We had code split into things like:

| Component | What it does | Should it depend on HTTP? |
|---|---|---|
| `CircularProcessorService` | Orchestrates the step | Only for streaming |
| `JobPollingService` | Poll external job completion | No |
| `ComplianceOSClient` | DB/API writes | No |
| `SlackAlerts` | Notify humans | No |

The bug was that our implementation accidentally made a bunch of “No” things depend on HTTP anyway.

## The bug (the exact pattern)

This is the shape of the broken code:

```python
# ❌ Broken: critical work is after streaming.
async def process_step():
    async for update in agent():
        yield sse(update)  # disconnect can cancel/raise here

    # If the client disconnects, this may never run.
    await db.update_status("tasks_done")
    asyncio.create_task(start_polling(job_id))
    await slack.notify("done")
```

It feels reasonable because it matches how we think:

“Stream updates while running… then when the loop ends, do the completion stuff.”

But in a streaming response, *the loop ending is not guaranteed*. The client can just leave.

## What actually happens when the client disconnects

Let’s make it concrete with a timeline.

Normal happy path:

```
Browser                  FastAPI/Starlette           MongoDB / External
   |                           |                          |
   | POST /process-step        |                          |
   |-------------------------->|                          |
   | 200 OK (SSE stream)       |                          |
   |<--------------------------|                          |
   | data: update #1           |                          |
   |<--------------------------|                          |
   | data: update #2           |                          |
   |<--------------------------|                          |
   | ...                       |                          |
   | data: final               |                          |
   |<--------------------------|                          |
   | stream ends               |                          |
   |                           | update status            |
   |                           |------------------------->|
   |                           | start poller             |
   |                           |------------------------->|
   |                           | Slack notify             |
   |                           |------------------------->|
```

Disconnect path:

```
Browser                  FastAPI/Starlette           MongoDB / External
   |                           |                          |
   | POST /process-step        |                          |
   |-------------------------->|                          |
   | 200 OK (SSE stream)       |                          |
   |<--------------------------|                          |
   | data: update #1           |                          |
   |<--------------------------|                          |
   | data: update #2           |                          |
   |<--------------------------|                          |
   | [tab closed]              |                          |
   X                           |                          |
                               | stream task canceled     |
                               | (right on a yield/send)  |
                               |                          |
                               | ❌ status update skipped  |
                               | ❌ poller never started   |
                               | ❌ Slack never sent       |
```

The punchline is simple: **SSE streaming is not “just a loop.” It’s a loop being consumed by a response writer that is allowed to stop at any time.**

## Under the hood (why Starlette cancels your generator)

This is not the exact Starlette source code, but it matches the design.

Streaming responses typically run two things concurrently:

- a task that iterates your generator and sends chunks (`http.response.body`)
- a task that listens for `http.disconnect`

When the disconnect happens, the server cancels the streaming task. That cancellation can hit while the framework is trying to send your last chunk… which was produced by your generator… which means your generator gets torn down mid-flight.

Two practical details that matter a lot:

1. Cancellation shows up as `asyncio.CancelledError` (or sometimes as “write failed” type errors depending on stack).
2. In modern Python, `asyncio.CancelledError` is a `BaseException`, not an `Exception`. So `except Exception:` won’t catch it.

That second one is why “but I wrapped it in try/except” doesn’t save you.

## A minimal repro you can run in two minutes

Here’s a tiny app that demonstrates the exact failure mode. The `print()` after the loop is your “update MongoDB status” in disguise.

```python
import asyncio
from fastapi import FastAPI
from starlette.responses import StreamingResponse

app = FastAPI()

async def gen():
    for i in range(1000):
        yield f"data: {i}\n\n".encode()
        await asyncio.sleep(0.2)
    print("stream ended; now do side effects")

@app.get("/sse")
async def sse():
    return StreamingResponse(gen(), media_type="text/event-stream")
```

Run it, then:

```bash
curl -N http://localhost:8000/sse
```

Wait for a few numbers, hit `ctrl+c` in the `curl` terminal.

You will not see the “now do side effects” line.

That’s the bug.

## The real fix: stop making your job depend on the HTTP stream

Once you accept “the client can vanish at any time”, the design gets boring (in a good way):

- The job runs to completion in a background task.
- Streaming is just a best-effort view of progress.

I like to think in terms of ownership:

- The worker owns side effects (DB writes, poller, Slack).
- The request handler owns only streaming bytes to the client.

### What I tried first (and why it didn’t help): `BackgroundTasks`

FastAPI has `BackgroundTasks`. It’s useful, but it’s not a magic “disconnect-proof” button.

The catch is simple: background tasks are executed *after* the response is done.

For a normal JSON response, “response is done” means “we returned a body, the server wrote it, done.”

For an SSE response, “response is done” means “the stream ended.”

Which is… exactly the thing we can’t rely on.

If the client disconnects and the streaming response gets canceled, your “run this after the response” work is still hanging off the same lifecycle. It’s not the separation you actually want.

### “Can’t I just move the status update into `finally`?”

This is another tempting fix:

```python
async def gen():
    try:
        async for update in agent():
            yield sse(update)
    finally:
        await db.update_status("tasks_done")
```

Sometimes it works. Sometimes it doesn’t. It depends on where cancellation lands.

Cancellation can interrupt awaits inside `finally` too. So you end up with a fun situation where you *thought* you made it reliable, but you just changed the probability of it failing.

If you really want to run cleanup under cancellation, you need to start thinking about shielding and cancel scopes. At that point you’re already halfway to the “worker owns completion” design anyway, so I’d rather just do it properly.

### The queue pattern (with one important correction)

The common implementation is “worker pushes updates into a queue, streamer drains it.”

That’s fine, but there’s a nasty gotcha:

If the client disconnects and the streamer stops draining, **a bounded queue can block your worker forever**.

So don’t do this in your worker:

```python
await queue.put(update)  # ❌ can hang if consumer is gone
```

If you do, you just recreated the original bug: completion is again tied to streaming, just indirectly.

What I do instead:

- Keep the queue bounded (to protect memory)
- Put updates in a non-blocking way and drop when full
- Stop queueing progress once the client is gone

Here’s a practical sketch:

```python
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

def sse(data: dict) -> bytes:
    return f"data: {json.dumps(data)}\n\n".encode("utf-8")

def try_put(queue: asyncio.Queue, item) -> None:
    try:
        queue.put_nowait(item)
    except asyncio.QueueFull:
        # progress is optional; completion isn't
        pass

def log_task_result(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("background worker crashed")

async def run_to_completion(queue: asyncio.Queue, client_gone: asyncio.Event):
    job_id = None
    try:
        async for update in agent():
            job_id = job_id or update.get("job_id")
            if not client_gone.is_set():
                try_put(queue, update)

        # ✅ These must run even if client disconnects.
        await db.update_status("tasks_done")
        asyncio.create_task(start_polling(job_id))
        await slack.notify("done")
    except Exception as e:
        if not client_gone.is_set():
            try_put(queue, {"final": True, "success": False, "error": str(e)})
        raise
    finally:
        if not client_gone.is_set():
            try_put(queue, None)  # sentinel for streamer

async def stream(queue: asyncio.Queue, client_gone: asyncio.Event):
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield sse(item)
    except asyncio.CancelledError:
        # disconnected: stop streaming, signal worker to stop enqueueing
        client_gone.set()
        raise
    finally:
        client_gone.set()

async def handler():
    queue = asyncio.Queue(maxsize=200)
    client_gone = asyncio.Event()

    task = asyncio.create_task(run_to_completion(queue, client_gone))
    task.add_done_callback(log_task_result)

    return StreamingResponse(stream(queue, client_gone), media_type="text/event-stream")
```

Is it perfect? No. But it has the right shape:

- worker can finish without a consumer
- progress streaming is best-effort
- failures are logged instead of silently disappearing

If you want something more durable (client reconnects and can replay progress), you need to store progress somewhere real (Redis/pubsub, DB, etc.). In-memory queues won’t do that. But that’s a different problem.

## The architecture I like better (when this gets serious)

The queue pattern is fine when:

- you mostly care about “don’t lose completion when the client disconnects”
- you don’t care about reconnecting and replaying a progress history

But once you ship this to real users, you’ll hit two common problems:

1. Browsers reconnect SSE automatically (especially `EventSource`), and you don’t want a reconnect to re-run the job.
2. People refresh and expect to see progress again (or at least not lose the final result).

So the more robust shape is:

1. `POST /steps/{step}/start` → returns a `run_id`
2. Worker runs independent of any SSE connection and persists state (status + maybe progress)
3. `GET /runs/{run_id}/events` → SSE stream that is purely “subscribe”, not “start”

Now reconnecting is safe. You might lose some live updates, but you can always read the current status from MongoDB, and you can keep polling running even if nobody is watching.

If you want a really clean UX, you can also persist event ids and support `Last-Event-ID`, but that’s optional. The big win is separating “start work” from “watch work.”

## SSE details that are boring but matter

SSE is “simple” in the same way DNS is “simple.”

It works great until you put it behind real infrastructure.

### Event formatting is strict

Each event ends with a blank line. If you forget the blank line, the browser buffers and you’ll think streaming is broken.

Simplest possible event:

```text
data: {"message":"hi"}

```

(Yes, that extra newline is part of it.)

### Keepalives

If your worker can go quiet for a while, send a comment every ~15–30 seconds so proxies don’t decide the connection is “idle”:

```python
yield b": keep-alive\n\n"
```

### Nginx buffering

If your stream arrives in one big chunk at the end, it’s usually Nginx buffering.

You don’t fix buffering with Python. You fix it with config.

At minimum, you want buffering off for the SSE location and timeouts that won’t murder long streams.

Something like this (not gospel, but you get the idea):

```nginx
location /runs/ {
  proxy_http_version 1.1;
  proxy_set_header Connection "";
  proxy_buffering off;
  proxy_cache off;
  proxy_read_timeout 3600s;
  add_header X-Accel-Buffering no;
}
```

## The other gotchas (the stuff that actually bites later)

### Don’t use request-scoped dependencies in your background worker

If you have `Depends(get_db)` where `get_db` is a `yield` dependency, it gets cleaned up when the request is done.

If your worker is still running, it may now be holding a dead session/client.

Solution: the worker should acquire its own long-lived clients (Mongo, HTTP client, etc.) that are not tied to the request lifecycle.

### Treat status updates like a state machine

If you do `timeline_done` → `tasks_done` → `final_done`, don’t just write `tasks_done` unconditionally.

Do “only update if current status is timeline_done” (compare-and-set). Otherwise retries and races will eventually mess up your state.

### Don’t confuse “survives client disconnect” with “durable”

This pattern survives a client disconnect. It does not survive:

- the process dying
- the pod being evicted
- a deploy that SIGTERMs the worker mid-step

If the job truly must finish no matter what, use a real job system. SSE should subscribe to a job id, not be the job.

### Decide if disconnect should cancel the job (explicitly)

Some people will ask for “closing the tab cancels the job.”

That’s a separate feature. Don’t accidentally implement it via “oops, the client disconnected so the worker got canceled.”

If you want cancellation, do it explicitly:

- create a job id
- store cancel intent
- have the worker check it and stop cleanly

Client disconnect is not a reliable cancel signal. It’s just the network being the network.

## A boring checklist (the stuff I verify before I trust the fix)

- Start a step, then close the tab mid-stream → status still advances later
- Start a step, refresh rapidly → no duplicate runs / no broken state transitions
- Simulate a proxy timeout → completion still happens
- Kill the SSE client (`curl -N ...` then `ctrl+c`) → completion still happens
- Worker crashes mid-way → status reflects failure, and it doesn’t get stuck “in progress” forever

## Performance notes (because someone will ask)

The queue approach is usually cheap, but it’s not free.

- Memory: `queue_size * avg_event_size` per in-flight stream. Keep event payloads small.
- CPU: queue ops are basically noise; the expensive bits are your DB/network calls.
- DB load: if you add read-after-write verification (I sometimes do), it’s extra reads. Worth it if your system lies to you otherwise.

The bigger risk isn’t CPU. It’s “we launched 500 background tasks because 500 people clicked the button.” Put a cap somewhere.

## Deployment strategy (how I roll it out without getting yelled at)

1. Staging: disconnect tests, refresh tests, and “kill the client” tests.
2. Canary: small percentage of traffic. Watch for stuck statuses.
3. Full rollout: watch completion rate for a day. If it drops, roll back fast.

## How I tested it (and how I’d recommend you test it)

Nothing fancy. I just did the thing that used to break it:

- start the step
- wait for a couple SSE updates
- close the tab / refresh / kill the connection
- watch MongoDB and server logs

What I wanted to see is boring:

- status advances anyway
- poller starts anyway
- Slack fires anyway

Once you watch the system finish without a client attached, you stop trusting “after the stream” code forever.

And honestly you should. It’s a trap.
