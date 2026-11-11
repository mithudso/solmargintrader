# Rollback a code change

## Preconditions

Identify the offending commit and the component it changes. Preserve unrelated dirty
work. If the behavior can move funds, use `docs/runbooks/incident.md` first and record
venue/chain state. Rolling back source cannot reverse a mined transaction or venue order.

## Actions

Use a normal revert on a dedicated branch, with the exact offending commit supplied:

```bash
git status --short
git log -5 --oneline
git revert <offending-commit-sha>
```

Do not reset a dirty checkout, rewrite the shared branch, clear the journal, or replace
the liquidity ledger. Rebuild the offline retrieval indexes after the intended files
are staged, as `docs/caching-and-optimization.md` describes.

## Verification

Run the owning tests, the offline extension integration gate where relevant, and the
repository documentation/index checks in `docs/TESTING.md`. Reloading an installed
extension, app bundle or daemon is a separate acceptance step with its own state checks.

## Escalation

If the old revision cannot interpret current persisted state or any outcome is unknown,
keep execution stopped and record the conflict before choosing a recovery. Never retry
an ambiguous order solely because the code was reverted.
