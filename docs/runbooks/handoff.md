# Handoff or resume repository work

## Preconditions

Know the canonical checkout, active branch/worktree, task and target behavior. Existing
prompt and memory records are evidence; verify them against current source and Git.

## Actions

```bash
git status --short
git worktree list
git log -5 --oneline
```

Read `CLAUDE.md`, `prompts.md` and `memory.md`; then read the owning component's rules.
Check for an unfinished Git operation and any other active worktree before editing.
When Stele is configured, search the existing task before creating another and claim
before implementation. Preserve decisions, risks and unresolved gaps with source anchors.

Update the workflow record version and delta fields with what changed, exact validation,
remaining work and any live-state evidence. Commit only paths owned by the task. Do not
start a daemon, sweep, indexer or inference runtime just because a resume record lists it.

## Verification

A fresh session must be able to identify the next concrete step without the prior chat.
Task completion requires tests and delivery evidence, not a checkbox or process exit.

## Escalation

Leave a concrete blocker when credentials, an external outcome or an owner decision is
required. Preserve accepted checkpoints and unfinished work instead of guessing intent.
