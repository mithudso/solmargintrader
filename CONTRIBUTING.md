# Contributing

Read `CLAUDE.md`, then `docs/DEVELOPMENT.md` and the owning component's README before
editing. The extension and liquidity manager can move money; the backtester remains
simulation-only. Liquidity also has its own `liquidity/CLAUDE.md`.

Keep changes focused and preserve unrelated worktrees, staged files and research artifacts.
Save the request in `prompts.md` and a versioned work/verification/remaining-step record
in `memory.md`. Workflow record versions are separate from component versions.

## Verification

Use the commands in `docs/TESTING.md`. Run the owning suite, relevant integration gate,
and documentation/index drift checks. Signal or fill-timing changes need a test that
would catch lookahead. A new registered strategy needs its strategy card. Do not report
installed or live acceptance merely because source tests passed.

## Pull requests

Explain the concrete behavior change, why it is needed, verification results, material
risks and rollback. Stage only owned files. Never commit credentials, keys or captured
customer data. Report security issues using `.github/SECURITY.md`.
