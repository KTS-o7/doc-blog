+++
title = "From Manual Deploys to SHA-Tagged Containers: CI/CD for a K8s Platform"
date = 2026-02-17T00:00:00+00:00
draft = false
math = false
+++

Someone tagged an image `latest`, pushed it to ECR, and overwrote the image another service was using. Four hours of debugging later, we figured out we were running the wrong binary entirely. That was the week I decided to stop treating deployment as a manual process.

This post covers three CI/CD problems I solved with Docker Buildx, SHA-based image tagging, and dynamic workflow generation — and one thing I broke along the way.

## Why `latest` is a lie

Container registries store images by tag. Tags are mutable pointers. When you `docker push myapp:latest`, you're moving a pointer — the old image behind `latest` is now unreferenced. If two services share the tag `latest` or two people push to the same tag concurrently, you get a race condition on a mutable pointer. This is exactly the class of bug that version control systems solved decades ago.

The fundamental problem: **image tags have no inherent ordering, no history, and no integrity guarantee.** They're a name, not a version.

The solution is to use a content-addressable identifier you already have: the Git commit SHA.

## SHA-based image tagging

Every commit has a unique SHA-1 hash. Using it as the image tag creates an injective mapping from source code state → deployed artifact:

```
commit a1b2c3d → image registry/service:a1b2c3d → K8s pod spec
```

The implementation in GitHub Actions:

```yaml
- name: Derive image tag from commit
  run: |
    # Short SHA is sufficient — collision probability
    # across 2^28 commits is negligible for any single repo
    echo "IMAGE_TAG=${GITHUB_SHA::7}" >> $GITHUB_ENV
```

This gives you two things that `latest` never can:

1. **Bijective traceability.** Given a running pod, you can recover the exact source:

```bash
$ kubectl get pod $POD -o jsonpath='{.spec.containers[0].image}'
123456789.dkr.ecr.us-east-1.amazonaws.com/myservice:a1b2c3d

$ git show a1b2c3d --stat
```

2. **Immutable deployment records.** The tag `a1b2c3d` either exists or it doesn't. It can't silently change meaning.

### Propagating the tag to Kubernetes manifests

A tagged image is useless if the deployment spec still references `latest`. We close the loop by having CI update the manifest and commit the change:

```yaml
- name: Patch deployment manifest
  run: |
    sed -i "s|image: $REGISTRY/$SERVICE:.*|image: $REGISTRY/$SERVICE:${IMAGE_TAG}|" \
      k8s/$ENVIRONMENT/${SERVICE}-deployment.yaml

- name: Commit manifest update
  run: |
    git config user.name "ci-bot"
    git config user.email "ci-bot@noreply"
    git add k8s/
    git diff --cached --quiet || \
      git commit -m "deploy($ENVIRONMENT): $SERVICE → $IMAGE_TAG"
    git push
```

Now `git log k8s/staging/` is your deployment history. Every deployment is a commit. Every rollback is `git revert`. This is the minimal viable GitOps pattern — your Git repo is the single source of truth for cluster state.

The `git diff --cached --quiet` guard prevents empty commits when nothing actually changed (e.g., the service wasn't rebuilt).

## Docker Buildx: layer caching in CI

The default `docker build` in CI has no cache. Every run downloads the base image, reinstalls all dependencies, copies all source files. For a Python service with 200+ packages, this is 8–12 minutes of work repeated identically on every push.

Docker Buildx provides two things that fix this: **persistent builder instances** and **pluggable cache backends**.

### How Docker layer caching works

Docker images are a stack of layers. Each Dockerfile instruction creates a layer. Docker caches layers by their input hash — if the instruction and all preceding layers are identical, the cached layer is reused.

```
Layer 4: COPY . .                    ← changes every commit
Layer 3: RUN pip install -r req.txt  ← changes weekly
Layer 2: RUN apt-get install gcc     ← changes monthly
Layer 1: FROM python:3.11-slim       ← changes rarely
```

Cache invalidation is **top-down**: if Layer 2 changes, Layers 3 and 4 are invalidated too, even if `requirements.txt` hasn't changed. This means **Dockerfile instruction ordering directly determines cache efficiency.**

The optimal ordering principle: **sort instructions by change frequency, ascending.** System deps → language deps → application source.

```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app

# Layer 1: System dependencies (changes ~monthly)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Layer 2: Python dependencies (changes ~weekly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Layer 3: Application source (changes every commit)
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### GitHub Actions cache backend

The key Buildx configuration:

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Build and push
  uses: docker/build-push-action@v5
  with:
    context: services/${{ matrix.service }}
    push: true
    tags: |
      ${{ env.REGISTRY }}/${{ matrix.service }}:${{ env.IMAGE_TAG }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

`type=gha` uses GitHub Actions' built-in cache as the layer storage backend. This is important because CI runners are ephemeral — without an external cache backend, every run starts cold.

`mode=max` is critical and often missed. By default, Buildx only exports layers from the final stage. `mode=max` exports **all intermediate layers**, including those from multi-stage build stages. Without it, your `pip install` layer from a builder stage won't be cached.

Under the hood, Buildx serializes each layer as a content-addressed blob and stores it via the GitHub Actions cache API. On subsequent runs, it checks the cache by layer digest before executing the instruction.

### Cache efficiency in practice

The difference is dramatic:

| Scenario | Without cache | With Buildx + GHA cache |
|----------|:---:|:---:|
| Full build (cold cache) | 10 min | 10 min |
| Source-only change | 10 min | 45 sec |
| Dependency change | 10 min | 4 min |
| No change (skip with change detection) | 10 min | 0 sec |

The dominant cost axis shifts from build time to cache lookup time. For a source-only change, the only layer that rebuilds is `COPY . .`, which takes seconds.

### Multi-stage builds and image size

If your final image includes build tools (`gcc`, `python3-dev`, header files), you're shipping dead weight. Multi-stage builds separate the build environment from the runtime environment:

```dockerfile
# Stage 1: Build (includes compilers, headers)
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y gcc libffi-dev
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime (minimal)
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

The `--prefix=/install` flag tells pip to install into a separate directory tree, which we then `COPY --from=builder` into the clean runtime image. The final image has no `gcc`, no header files, no pip cache.

Impact: image sizes dropped from 1.2GB to ~450MB. This matters for pull times during rollouts — a 450MB image pulls in ~15 seconds vs ~45 seconds for 1.2GB. During a rolling update across 6 replicas, that's 3 minutes saved per deployment.

## Dynamic service discovery in CI

Hardcoding a service list in your workflow is a maintenance hazard:

```yaml
# ❌ This will drift
strategy:
  matrix:
    service: [auth, api, worker, processor]
```

When someone deletes `processor/` and forgets to update the workflow, CI breaks. When someone adds a new service and forgets to add it, it never gets built. Both happen eventually.

### Filesystem-driven matrix generation

Instead of declaring services, discover them:

```yaml
jobs:
  discover:
    runs-on: ubuntu-latest
    outputs:
      services: ${{ steps.find.outputs.services }}
    steps:
      - uses: actions/checkout@v4
      - id: find
        run: |
          services=$(find services/ -name Dockerfile -maxdepth 2 \
            | xargs -I{} dirname {} \
            | xargs -I{} basename {} \
            | jq -R -s -c 'split("\n") | map(select(length > 0))')
          echo "services=$services" >> $GITHUB_OUTPUT

  build:
    needs: discover
    strategy:
      matrix:
        service: ${{ fromJson(needs.discover.outputs.services) }}
```

The contract becomes: a directory under `services/` with a `Dockerfile` is a deployable service. No other registration needed. Add a service → add a directory with a Dockerfile. Remove a service → remove the directory.

### Change detection: only build what's affected

Even with caching, there's no reason to build 8 services when 1 file changed. The `git diff` between the previous and current commit tells you what changed:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Required for accurate git diff

- id: changes
  run: |
    changed=$(git diff --name-only ${{ github.event.before }} ${{ github.sha }})
    if echo "$changed" | grep -q "^services/${{ matrix.service }}/"; then
      echo "build=true" >> $GITHUB_OUTPUT
    elif echo "$changed" | grep -q "^libs/shared/"; then
      echo "build=true" >> $GITHUB_OUTPUT
    else
      echo "build=false" >> $GITHUB_OUTPUT
    fi

- name: Build and push
  if: steps.changes.outputs.build == 'true'
  uses: docker/build-push-action@v5
  # ...
```

The `fetch-depth: 0` is essential. GitHub Actions performs a shallow clone by default (`fetch-depth: 1`), which means `git diff` doesn't have enough history and will treat everything as "new." We discovered this when our changelogs started showing every file in the repo as changed.

The `libs/shared/` check handles transitive dependencies — if a shared library changes, all services that could depend on it get rebuilt.

## Edge cases that will bite you

### ECR lifecycle policies

SHA tags accumulate. At 5 pushes/day × 8 services × ~800MB average image size, that's 32GB/day of new images. Without cleanup, you'll hit storage budget limits within weeks.

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 20 tagged images",
      "selection": {
        "tagStatus": "tagged",
        "countType": "imageCountMoreThan",
        "countNumber": 20
      },
      "action": { "type": "expire" }
    },
    {
      "rulePriority": 2,
      "description": "Expire untagged images after 24h",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 1
      },
      "action": { "type": "expire" }
    }
  ]
}
```

20 tagged images gives you ~4 days of rollback runway at 5 pushes/day, which is plenty. Untagged images (intermediate layers from multi-stage builds) expire after 24 hours.

### Concurrent manifest commits

If two workflow runs try to commit manifest changes simultaneously, the second `git push` fails. A retry loop with rebase handles this:

```yaml
- name: Push manifest update
  run: |
    for attempt in 1 2 3; do
      git pull --rebase origin main
      git add k8s/
      git diff --cached --quiet && exit 0
      git commit -m "deploy: $SERVICE → $IMAGE_TAG"
      git push && exit 0
      echo "Push failed (attempt $attempt), retrying..."
      sleep $((attempt * 2))
    done
    echo "::error::Manifest push failed after 3 attempts"
    exit 1
```

The exponential backoff (`sleep $((attempt * 2))`) avoids thundering herd on concurrent pushes. In practice, this retries successfully on the first attempt 99% of the time.

### Build context bloat

Docker sends the entire build context directory to the daemon before building. In a monorepo, that context can be enormous if you're not careful. Each service needs a `.dockerignore`:

```
**/__pycache__
*.pyc
.git
.env
tests/
docs/
*.md
node_modules/
```

Without this, we were sending ~500MB of context for services that only needed ~20MB of source. The context upload alone added 2 minutes to every build.

### Silent auth failures

ECR login can silently succeed without actually authenticating (e.g., when secrets aren't available in fork PRs). The build proceeds, spends 10 minutes compiling, and only fails at `docker push`.

Add an explicit access check early:

```yaml
- name: Verify registry access
  run: |
    aws ecr describe-repositories \
      --repository-names "${{ matrix.service }}" > /dev/null 2>&1 \
    || { echo "::error::ECR access failed for ${{ matrix.service }}"; exit 1; }
```

Fail at second 5, not minute 12.

## The pipeline end-to-end

```
git push origin main
        │
        ▼
┌──────────────┐
│   Discover   │  find services/ -name Dockerfile
│   Services   │  → ["auth", "api", "worker"]
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Per-service matrix job (parallel)              │
│                                                 │
│  1. Checkout (fetch-depth: 0)                   │
│  2. git diff → should this service build?       │
│     └── no → skip remaining steps               │
│  3. Verify ECR access                           │
│  4. Set up Buildx                               │
│  5. Build + push (SHA tag, GHA layer cache)     │
│  6. sed manifest with new SHA                   │
│  7. git commit + push manifest (retry loop)     │
└──────┬──────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│  GitOps sync │  ArgoCD / Flux / kubectl apply
│  picks up    │  detects manifest diff → rolling update
└──────────────┘
```

Typical wall-clock time for a single-service source change: **~90 seconds** from push to new pod running.

## Key metrics

| Metric | Manual process | Automated pipeline |
|--------|:-:|:-:|
| Deploy time | ~15 min | ~90 sec |
| Builds per push | All services | Only changed |
| Image traceability | None (`latest`) | Commit SHA |
| Rollback mechanism | "Redeploy the old one" | `git revert` + sync |
| CI minutes/week | ~400 | ~90 |
| Wrong-image incidents | ~1/month | 0 |

## Checklist

- [ ] **Tag with commit SHA, not `latest`.** Mutable tags are mutable bugs.
- [ ] **Order Dockerfile by change frequency.** System deps → language deps → source. Cache invalidation is top-down.
- [ ] **Use `cache-from: type=gha` with `mode=max`.** Without `mode=max`, intermediate stage layers aren't cached.
- [ ] **`fetch-depth: 0` on checkout.** Shallow clones break `git diff` and changelog generation.
- [ ] **Discover services from the filesystem.** Hardcoded lists drift. Dockerfiles are the contract.
- [ ] **Skip unchanged services.** `git diff` + path matching. Don't forget shared library paths as rebuild triggers.
- [ ] **Set ECR lifecycle policies.** 20 tagged images + 24h untagged expiry is a reasonable starting point.
- [ ] **`.dockerignore` per service.** Build context size ∝ upload time. Ship source, not tests.
- [ ] **Verify registry auth early.** Don't spend 10 minutes building an image you can't push.
- [ ] **Retry manifest pushes.** Concurrent CI runs will race on `git push`. Rebase + retry handles it.
