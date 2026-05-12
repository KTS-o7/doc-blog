+++
title = "Hunting OOMKilled in Kubernetes: Four Memory Leaks That Almost Took Down Our Platform"
date = 2026-02-16T00:00:00+00:00
draft = false
math = false
+++

A pod restarts at 3 AM. Then again at 3:14. By 3:30 it's in a `CrashLoopBackOff`. The dashboard shows memory climbing in a clean line - no spikes, no sudden jumps - just a slow, relentless climb until the OOM killer steps in.

This is the story of how I tracked down four distinct memory leaks across two Python services running on Kubernetes. Each one was a different flavor of "silent accumulation," and each one taught me something about how easy it is to bleed memory in async Python without any obvious errors.

No names. No product details. Just the bugs, the fixes, and the lessons.

## The setup

We had a multi-service platform running on Kubernetes. Two services are relevant here:

- **Service A**: A document management service. It handled CRUD operations, search indexing, audit logging, and authorization precomputation. Built with FastAPI and async Python, backed by MongoDB and a vector store.

- **Service B**: A PDF processing service. It parsed documents, extracted text via OCR, and broke content into structured clauses. Heavy on PyMuPDF (fitz) for PDF rendering and Tesseract for OCR.

Both services ran as single-container pods with resource limits. Service A had a 2Gi memory limit. Service B had 4Gi.

Both were getting OOMKilled. Regularly.

## The symptoms

Service A's memory graph looked like this:

```
Memory (MB)
2048 |                                              ╱ OOMKilled
     |                                           ╱
1536 |                                        ╱
     |                                     ╱
1024 |                                  ╱
     |                               ╱
 512 |                            ╱
     |                         ╱
   0 |________________________╱
     0h        6h        12h        18h        24h
```

A steady climb at roughly 200MB per hour. No spikes. No correlation with traffic. Just a ramp.

Service B was different - it'd spike during document processing batches and never come back down:

```
Memory (MB)
4096 |          ╱╲        ╱╲
     |        ╱   ╲     ╱   ╲    ╱ OOMKilled
3072 |      ╱      ╲  ╱      ╲ ╱
     |    ╱         ╲╱        ╱
2048 |  ╱                   ╱
     |╱                   ╱
1024 |                  ╱
     |               ╱
   0 |______________╱
     0h     2h     4h     6h     8h     10h
```

Every batch pushed memory up. It came down a little, but never to baseline. Classic leak with GC partially reclaiming some objects but not the real offender.

## Leak #1: The coroutines that never ran

This was the most insidious one. It looked like perfectly normal Python code:

```python
class BaseDoc:
    def _write_audit_log(self, action, old_data, new_data):
        enqueue_audit_create(self, action, old_data, new_data)

    async def save(self, *args, **kwargs):
        old = await self.get(self.id)
        result = await super().save(*args, **kwargs)
        self._write_audit_log("update", old, result)
        await create_snapshots(self.id)
        await insert_versions_docs(self.id)
        return result
```

Spot the bug?

`_write_audit_log` calls `enqueue_audit_create()`, which is an **async function**. But `_write_audit_log` is not async, and it doesn't `await` the call. It just calls it.

When you call an async function without `await`, Python creates a coroutine object but never schedules it. The coroutine sits in memory, holding references to all its arguments - in this case, entire document objects with `old_data` and `new_data`.

```text
Coroutine Object (0x7f...)
  ├── State: CREATED (never scheduled)
  └── Frame Object
       ├── Arg: self (BaseDoc instance, 2KB)
       ├── Arg: old_data (Dict, 5MB)  <-- LEAKED
       └── Arg: new_data (Dict, 5MB)  <-- LEAKED
       └── Local Vars: (captured closure scope)
```

Python will eventually warn you about this (`RuntimeWarning: coroutine was never awaited`), but only if you have warnings enabled and you're looking at the right log. In a noisy production service running dozens of requests per second, these warnings get buried.

The same pattern appeared elsewhere:

```python
# In the CRUD endpoints
async def create_document(request):
    doc = await Document.create(request.data)
    enqueue_audit_create(doc)       # ← async, not awaited
    qdrant_upserts(doc)             # ← async, not awaited
    return doc

async def update_document(request):
    doc = await Document.update(request.data)
    enqueue_audit_update(doc)       # ← async, not awaited
    qdrant_upserts(doc)             # ← async, not awaited
    return doc
```

Each unawaited call created a coroutine holding the full document. For a service processing hundreds of documents per hour, that's hundreds of document-sized objects pinned in memory with no way to be garbage collected.

### The fix

Straightforward once you see it:

```python
class BaseDoc:
    async def _write_audit_log(self, action, old_data, new_data):
        await enqueue_audit_create(self, action, old_data, new_data)

    async def save(self, *args, **kwargs):
        old = await self.get(self.id)
        result = await super().save(*args, **kwargs)
        await self._write_audit_log("update", old, result)
        await create_snapshots(self.id)
        await insert_versions_docs(self.id)
        return result
```

And in the CRUD endpoints:

```python
async def create_document(request):
    doc = await Document.create(request.data)
    await enqueue_audit_create(doc)
    await qdrant_upserts(doc)
    return doc
```

### The lesson

**Unawaited coroutines are silent memory leaks.** They don't crash. They don't raise. They just accumulate. And because they hold references to their arguments, they can keep large objects alive long after the request that created them is done.

If you're running async Python, add this to your linting:

```python
# In your pytest conftest.py or startup
import warnings
warnings.filterwarnings("error", category=RuntimeWarning, message="coroutine.*was never awaited")
```

This turns the warning into an exception, which makes it impossible to miss.

## Leak #2: Creating a new MongoClient on every authorization check

The authorization layer needed to precompute user access contexts. To do this, it queried MongoDB directly (not through the async ODM) using PyMongo's synchronous `MongoClient`.

The code looked like this:

```python
class AuthorizationPrecompute:
    def get_user_permissions(self, user_id):
        client = MongoClient(MONGO_URI)
        db = client["main_db"]
        permissions = list(db.permissions.find({"user": user_id}))
        client.close()
        return permissions

    def get_role_policies(self, role_id):
        client = MongoClient(MONGO_URI)
        db = client["main_db"]
        policies = list(db.policies.find({"role": role_id}))
        client.close()
        return policies

    def get_org_settings(self, org_id):
        client = MongoClient(MONGO_URI)
        db = client["main_db"]
        settings = db.settings.find_one({"org": org_id})
        client.close()
        return settings

    # ... 10 more methods, each creating its own MongoClient
```

Thirteen methods. Thirteen `MongoClient()` instantiations per authorization check.

Each `MongoClient` creates a connection pool, background SDAM monitoring threads, and internal caches. Even with `client.close()`, the cleanup isn't instant - Python's garbage collector has to reclaim the thread stacks, socket buffers, and internal data structures.

And if an exception happens between `MongoClient()` and `client.close()`, the client never gets closed at all. The connection pool lives on, holding threads and sockets until the GC eventually (maybe) collects them.

At 50 requests/second, each triggering an auth check, we were creating **650 MongoClient instances per second**. Most were closed, but the transient memory pressure and leaked exceptions meant we were always carrying a few hundred orphaned connection pools.

### The fix

One shared client with a connection pool:

```python
class AuthorizationPrecompute:
    _client = None

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            cls._client = MongoClient(
                MONGO_URI,
                maxPoolSize=20,
                serverSelectionTimeoutMS=5000
            )
        return cls._client

    def get_user_permissions(self, user_id):
        db = self._get_client()["main_db"]
        return list(db.permissions.find({"user": user_id}))

    def get_role_policies(self, role_id):
        db = self._get_client()["main_db"]
        return list(db.policies.find({"role": role_id}))
```

Connection overhead went from ~50ms per call (TCP handshake + auth each time) to ~5ms (reused connection from pool).

### The lesson

**Each `MongoClient` is an entire connection pool, not a single connection.** Creating one per function call is like starting a new database server for every query. Always share a single client instance (or at most one per thread/worker). And if you can't guarantee `close()` will be called (i.e., exceptions exist), you definitely need a shared instance.

## Leak #3: Cache entries that never expire

The authorization layer also had an in-memory cache for user access contexts:

```python
class UserAccessContextCache:
    def __init__(self, ttl_seconds=300):
        self._cache = {}
        self._ttl = ttl_seconds

    def get(self, key):
        entry = self._cache.get(key)
        if entry and time.time() - entry["created"] < self._ttl:
            return entry["value"]
        return None

    def set(self, key, value):
        self._cache[key] = {
            "value": value,
            "created": time.time()
        }
```

See the problem?

When `get()` finds an expired entry, it just returns `None`. It doesn't delete the entry. The stale data sits in the dict forever.

And `set()` only adds entries. Nothing ever removes them.

Over time, this cache grows without bound. Every unique user who hits the service gets a cache entry that is never cleaned up. The access context objects themselves can be large - they contain permission trees, role hierarchies, and org settings.

With 200MB of stale cache entries after a day of operation, this was a significant contributor to the memory ramp.

### The fix

Add proactive cleanup:

```python
class UserAccessContextCache:
    def __init__(self, ttl_seconds=300, cleanup_interval=60):
        self._cache = {}
        self._ttl = ttl_seconds
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

    def _cleanup_expired(self):
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        expired_keys = [
            k for k, v in self._cache.items()
            if now - v["created"] >= self._ttl
        ]
        for k in expired_keys:
            del self._cache[k]

    def get(self, key):
        self._cleanup_expired()
        entry = self._cache.get(key)
        if entry and time.time() - entry["created"] < self._ttl:
            return entry["value"]
        # Delete on read if expired
        if key in self._cache:
            del self._cache[key]
        return None

    def set(self, key, value):
        self._cleanup_expired()
        self._cache[key] = {
            "value": value,
            "created": time.time()
        }
```

Cleanup runs at most once per minute and removes all entries older than TTL.

### The lesson

**Every in-memory cache needs an eviction strategy.** If there's no mechanism to remove old entries, you have a memory leak with extra steps. "TTL on read" is not enough - if users stop requesting a key, that entry stays forever.

Use `cachetools.TTLCache` or similar if you don't want to roll your own. Better yet, if the cache is big enough to matter, put it in Redis where you can set `EXPIRE` and forget about it.

## Leak #4: PyMuPDF documents that never closed

Service B was the PDF processing service. It used PyMuPDF (`fitz`) to render pages and extract text. The endpoints looked like this:

```python
@app.post("/parse_pdf")
async def parse_pdf(file: UploadFile):
    content = await file.read()
    doc = fitz.open(stream=content, filetype="pdf")

    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        pix = page.get_pixmap(dpi=300)
        image = pix.tobytes("png")
        pages.append({"text": text, "image": image})

    return {"pages": pages}
```

No `doc.close()`. No context manager. No `try/finally`.

PyMuPDF is a C library wrapper. When you call `fitz.open()`, it allocates memory in C-land for the document structure, page data, fonts, images, and rendering buffers. Python's garbage collector can eventually reclaim the Python wrapper object, but the C-side memory is only freed when `doc.close()` is explicitly called.

While the wrapper theoretically has a `__del__` method, relying on it in a high-throughput async loop is dangerous. Python's GC is lazy and may not run fast enough to keep up with the rate of C-memory allocation, leading to OOMs before the GC even realizes it needs to clean up.

For a 50-page PDF at 300 DPI, the pixmap rendering alone can consume 200–500MB of memory. If an exception occurs mid-processing (corrupt page, unsupported font), the doc handle leaks entirely.

### The fix

Two changes: proper resource cleanup, and parallel OCR with controlled concurrency.

```python
@app.post("/parse_pdf")
async def parse_pdf(file: UploadFile):
    content = await file.read()
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            pix = page.get_pixmap(dpi=300)
            image = pix.tobytes("png")
            # Explicitly free the pixmap
            pix = None
            pages.append({"text": text, "image": image})
        return {"pages": pages}
    finally:
        doc.close()
```

This was applied to all four endpoints in the service: `/parse_pdf`, `/process_clauses`, `/process_clauses_sync`, and `/extract_links`.

We also added parallel strip processing for OCR (controlled by feature flags):

```python
import os
from concurrent.futures import ThreadPoolExecutor

ENABLE_PARALLEL_OCR = os.getenv("ENABLE_PARALLEL_OCR", "false").lower() == "true"
STRIP_OCR_WORKERS = int(os.getenv("STRIP_OCR_WORKERS", "8"))

def process_page_strips(page, strips):
    if not ENABLE_PARALLEL_OCR:
        return [ocr_strip(page, s) for s in strips]

    with ThreadPoolExecutor(max_workers=STRIP_OCR_WORKERS) as pool:
        futures = [pool.submit(ocr_strip, page, s) for s in strips]
        return [f.result() for f in futures]
```

### The deployment

We didn't flip everything on at once:

1. Deploy with `ENABLE_PARALLEL_OCR=false` - just the `doc.close()` fixes
2. Monitor memory for 24 hours to confirm the leak is fixed
3. Bump resource limits from `4Gi` to `6Gi` to accommodate parallel processing headroom
4. Enable parallel OCR: `ENABLE_PARALLEL_OCR=true`

Memory dropped from a steady 4GB to a stable 1.8GB. That's a 55% reduction from just closing document handles properly.

### The lesson

**C extension libraries manage their own memory.** Python's GC has no visibility into `fitz`, `numpy`, `Pillow`, or any other C-backed library. If the library provides a `close()`, use it. If it supports context managers, use `with`. And always wrap C-heavy processing in `try/finally`.

## The combined impact

Here's the before and after across both services:

| Issue | Before | After |
|-------|--------|-------|
| Unawaited coroutines | ~200MB/hour leak | 0 |
| MongoClient per call | 5–15 new connections per request | 1 pooled |
| Stale cache entries | Up to 200MB unbounded | Cleaned every 60s |
| PyMuPDF documents | 4GB+ with no release | Stable at 1.8GB |
| Embedding API calls | 2× per document save | 1× (cached concat) |

Service A went from daily OOMKills to zero restarts. Service B went from crashing every 8–10 hours to running for weeks without a restart.

## How I found them

No fancy tooling. Here's the actual process:

1. **Look at the memory graph.** Linear growth = accumulation leak. Sawtooth that doesn't return to baseline = handle/resource leak.

2. **Read the code.** Seriously. I read every function in the hot paths and asked "what gets allocated here that doesn't get freed?"

3. **`grep` for patterns.** Once I found one unawaited coroutine, I searched for the pattern across the entire codebase:

```bash
# Find async functions called without await
rg "^\s+[a-z_]+\(" --type py | grep -v "await " | grep -v "def " | grep -v "#"
```

Not perfect, but it flagged the 13 MongoClient instantiations immediately.

4. **Check warnings.** Enabled `RuntimeWarning` filtering and got 6 unawaited coroutine warnings within the first minute of startup.

5. **Kubernetes events.** `kubectl describe pod` shows OOMKilled with the exact memory at death. Compare that to your resource limits and you know how fast it's growing.

```bash
kubectl get events --field-selector reason=OOMKilling \
  --sort-by='.lastTimestamp' -n your-namespace
```

## A checklist for your services

If you're running Python services on Kubernetes and seeing memory growth, check these in order:

- [ ] **Unawaited coroutines.** Search for `RuntimeWarning: coroutine.*was never awaited` in your logs. Better yet, make it an error.
- [ ] **MongoClient instantiation.** `grep -rn "MongoClient(" your_code/` - if it appears in more than one place (especially inside functions, not module level), you probably have a leak.
- [ ] **In-memory caches without eviction.** Any `dict` that grows with usage and has no `del` or size cap is a leak. `TTLCache`, `LRU`, or `maxsize` - pick one.
- [ ] **C extension resources.** PyMuPDF, Pillow, lxml, pdfplumber - anything that wraps C needs explicit `close()` or `with` statements.
- [ ] **Large objects in exception handlers.** If your `except` block captures the full traceback and logs the local variables, those locals (which may include entire documents) are pinned until the log entry is flushed.
- [ ] **Background tasks holding request data.** If `asyncio.create_task()` captures a closure over request objects, those objects live until the task completes.

## Final thought

None of these bugs produced an error. No stack trace. No warning (well, one did, but it was buried). The services ran *fine* - they just got slower and slower until Kubernetes killed them, then they restarted and the cycle began again.

Memory leaks in garbage-collected languages are not the "forgot to call `free()`" kind. They're the "I'm holding a reference I didn't know about" kind. The GC is doing its job perfectly - it's keeping alive exactly what you told it to.

You just told it wrong.
