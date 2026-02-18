# Codex Worktrees Adventure Post Design

Date: 2026-02-18
Topic: Practical guide rewrite for `content/posts/codex_worktrees_adventure.md`

## Goal

Turn the post into a practical runbook for parallel Codex execution with git worktrees, grounded in real PR evidence and concrete failure fixes.

## Chosen Approach

- Approach: Incident -> playbook (recommended)
- Voice: Practical guide first, minimal narrative

## Approved Structure

1. Why this exists
2. System model
3. Execution workflow
4. Failure modes and fixes
5. Verification checklist
6. Ralph loop integration

## Factual Anchors

- PRs #47-#51 opened on 2026-02-18 within ~55 seconds
- Commits: `d3be105` (pre-plan base), `55e9f9a` (plans/worktree script)
- Observed PR noise example: PR #50 included plan doc in diff
- Codex memory references include repeated worktree + PR operations and worktree-ignore confusion

## Content Constraints

- Prefer command blocks/checklists over long narrative
- Keep recommendations reproducible and repo-agnostic where possible
- Cite Ralph loop and git-worktree references

## Verification Plan

- Confirm markdown front matter renders correctly
- Confirm commands are syntactically valid shell snippets
- Confirm facts match local git/PR metadata captured during drafting
