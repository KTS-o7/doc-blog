+++
title = "Many Small Tasks, One Deadline: Running Parallel AI Agents with Git Worktrees"
date = 2026-02-19T00:00:00+05:30
draft = false
math = false
+++

I thought this would be an easy day.

The tasks were small. The backlog was not. This is the worst possible combo for a normal workflow because the fixed overhead dominates: branch setup, dependency sync, commits, reviewable diffs, and PR management. Doing it serially feels safe, but it is slow in a way that doesn't show up in estimates.

So I tried the obvious cheat: run multiple AI agents in parallel.

It worked, but only after I tripped over three problems that are easy to reproduce if you try this without thinking through git state, shells, and sandbox boundaries.

## What the system looked like (so you don't think this is a demo problem)

I ended up writing a small orchestration script with three phases:

1. Create (or reuse) one worktree per task.
2. Install dependencies in parallel.
3. Run `codex exec` in batched parallel, then push branches and open draft PRs.

The key detail is that batching wasn't “run everything at once”. It was “parallel within a batch, sequential across batches”, grouped by expected file overlap.

Here is the redacted shape of the script (this is not pseudocode; it's a sanitized skeleton of what I ran):

```zsh
#!/usr/bin/env zsh
set -euo pipefail

WORKTREE_DIR=".worktrees"
BASE_BRANCH="<base-branch>"
LOG_DIR="${WORKTREE_DIR}/_logs"

mkdir -p "${WORKTREE_DIR}" "${LOG_DIR}"

# Phase 1: worktrees + deps (parallel installs)
hdr "Phase 1: Setting up worktrees"
git worktree add -b "<feature-branch>" "${WORKTREE_DIR}/<lane>" "${BASE_BRANCH}"
(cd "${WORKTREE_DIR}/<lane>/frontend" && bun install --frozen-lockfile) &
(cd "${WORKTREE_DIR}/<lane>/backend"  && uv sync) &
wait

# Phase 2: batched parallel codex exec (one log per lane)
hdr "Phase 2: Running Codex"
codex exec --dangerously-bypass-approvals-and-sandbox -C "${WORKTREE_DIR}/<lane>" -m "${CODEX_MODEL}" "<prompt>" > "${LOG_DIR}/<lane>.log" 2>&1 &
wait

# Phase 3: push + PRs
hdr "Phase 3: PRs to ${BASE_BRANCH}"
git -C "${WORKTREE_DIR}/<lane>" push -u origin "<feature-branch>"
gh pr create --base "${BASE_BRANCH}" --head "<feature-branch>" --draft --body "<templated body>"
```

Notice what this gives you immediately: one directory per lane, one log file per lane, and a clean boundary between “make changes” and “publish changes”.

Now for the parts that went wrong.

## Failure #1: The shell lied about what “Bash” means

The first failure happened before any parallelism even started. The orchestration was written with associative arrays, and the system shell rejected it with:

```text
declare: -A: invalid option
```

This is the kind of bug that looks embarrassing until you realize it is inevitable. macOS ships an older Bash; other environments may default to `sh`; CI runners may use different interpreters. If your control-plane script can't build the lane-to-branch mapping reliably, your entire run becomes a dice roll.

The fix was not “make it work on my machine”. The fix was pinning the interpreter and failing fast (`set -euo pipefail`). Once the script ran under the interpreter it was written for, this class of failure disappeared.

## Failure #2: The sandbox was fine until it touched `.git`

The second failure was more instructive: everything looked successful until commit/push time, and then git failed when trying to write worktree metadata:

```text
fatal: Unable to create '.git/worktrees/<lane>/index.lock': Operation not permitted
```

The important mental model is: “can edit files” is not equivalent to “can finish delivery”. Git history mutation needs to create locks and update metadata under `.git/`. Sandboxed agents often allow workspace file edits while denying `.git` writes by design.

The fix is to treat permissions as architecture. In my runbook now, implementation and version-control mutation are distinct phases. I keep guardrails on while generating and editing code, and only elevate privileges for `commit`, `rebase`, `push`, and PR creation. That sounds procedural, but it is the difference between parallelism and chaos.

## Failure #3: The PR diff was computed against the wrong reality

The third failure was the “ghost diff” class: the PR contained changes that “weren't part of the task” even though the worktree looked clean locally. This is not a GitHub bug. It is a merge-base bug.

PR diff is computed from:

```text
merge_base(feature, base) .. feature
```

If your base ref is stale when the feature branch is compared, `merge_base` resolves behind your intended base, and commits that should be “already in base” appear as if they were introduced by the feature.

The only reliable approach is to verify ancestry before review and rebase if needed:

```bash
git merge-base --is-ancestor origin/<base-branch> HEAD || echo REBASE_REQUIRED
git diff --name-only origin/<base-branch>...HEAD
```

This takes seconds and saves you from burning reviewer attention on diff noise.

## What changed once I actually read the Codex CLI docs

My first attempt treated Codex like a generic shell command that prints code. The docs made the control surface explicit, and that changed how I designed the run.

Approval and sandbox mode became part of the plan instead of an afterthought. Configuration precedence became something I could reason about when a lane behaved differently. Non-interactive `codex exec` became the default because it is scriptable and produces logs you can archive. And built-in review flows (like `/review`) became a lane-local quality gate before humans ever see the PR.

I also stopped mixing two different kinds of parallelism. Worktrees are for isolating tasks across lanes. Multi-agent mode is for decomposing one task inside a lane. When you treat them as separate tools, your system stays debuggable.

## The boring checklist

At this point the process is intentionally boring, which is exactly what you want near a deadline. My checklist is short:

- If the lane can't commit/push, it doesn't “count” as done. Fix the permission boundary first.
- If the PR diff scope isn't what you expect, stop and fix ancestry before asking for review.
- If a lane doesn't have a log file, assume it didn't run deterministically.

## Appendix: Redacted Script Skeleton

Below is a condensed, anonymized skeleton of the script I used. It preserves the mechanics (worktrees, batching, logs, PR creation) but removes identity details.

```zsh
#!/usr/bin/env zsh
set -euo pipefail

BASE_BRANCH="<base-branch>"
WORKTREE_DIR=".worktrees"
LOG_DIR="${WORKTREE_DIR}/_logs"

mkdir -p "${WORKTREE_DIR}" "${LOG_DIR}"

typeset -A TASK_BRANCH TASK_TITLE TASK_PLAN TASK_LABEL
TASK_BRANCH[001]="feature/lane-001"
TASK_TITLE[001]="Lane 001: <title>"
TASK_PLAN[001]="docs/plans/<plan>.md"
TASK_LABEL[001]="<label>"

BATCH_1=(001 002)
BATCH_2=(003)

setup_lane() {
  local id="$1"
  local branch="${TASK_BRANCH[$id]}"
  local worktree="${WORKTREE_DIR}/lane-${id}"

  if [[ -d "${worktree}" ]]; then
    echo "Reusing ${worktree}"
  else
    git worktree add -b "${branch}" "${worktree}" "${BASE_BRANCH}"
  fi

  (cd "${worktree}/frontend" && bun install --frozen-lockfile) &
  (cd "${worktree}/backend"  && uv sync) &
  wait
}

run_lane() {
  local id="$1"
  local worktree="${WORKTREE_DIR}/lane-${id}"
  local log="${LOG_DIR}/lane-${id}.log"
  local prompt="<redacted prompt built from plan + conventions>"

  codex exec --dangerously-bypass-approvals-and-sandbox -C "${worktree}" "${prompt}" > "${log}" 2>&1
}

create_pr() {
  local id="$1"
  local branch="${TASK_BRANCH[$id]}"
  local title="${TASK_TITLE[$id]}"
  local worktree="${WORKTREE_DIR}/lane-${id}"

  git -C "${worktree}" push -u origin "${branch}"
  gh pr create --base "${BASE_BRANCH}" --head "${branch}" --draft --title "${title}" --body "<templated body>"
}
```

## References

- Codex docs hub: https://developers.openai.com/codex
- Codex CLI overview: https://developers.openai.com/codex/cli
- Codex CLI features: https://developers.openai.com/codex/cli/features
- Codex multi-agent docs: https://developers.openai.com/codex/multi-agent
- Codex security/sandbox docs: https://developers.openai.com/codex/security
- Codex config basics: https://developers.openai.com/codex/config-basic
- Codex config reference: https://developers.openai.com/codex/config-reference
- Codex CLI GitHub README: https://github.com/openai/codex/blob/main/README.md
- Ralph loop agent (Vercel Labs): https://github.com/vercel-labs/ralph-loop-agent
- Ralph from first principles (Geoffrey Huntley): https://www.youtube.com/watch?v=4Nna09dG_c0
- Git worktree docs: https://git-scm.com/docs/git-worktree
