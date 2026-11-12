# Codex hook repair, 2026-11-12

Version: 1.0.0

The running Codex 0.167.2 daemon reproduced three `plugin contents changed;
hook approval required` failures per ordinary tool command. The five Windows-only
Architect hooks were already disabled. The reported `hook exited with code 126`
was not reproduced. Do not describe the historical exit-126 source as established.

Current native fingerprints matched the reviewed AI Plugins, Postman and Remember
bundles exactly. Tracked commits and all non-Git bundle files were unchanged.
A native version-checked configuration write replaced exactly eight
`trusted_content_hash` fields. A parsed before/after comparison verified that no
other configuration field changed. Disabled hooks and command approvals stayed
unchanged. The active daemon was not restarted.

After repair, actual tool activity produced 52 matching native hook starts and
completions. All 52 completed with zero error entries. This verifies the observed
pre/post tool failures; it does not prove every lifecycle hook executed. No
Remember capture or flush was forced for testing.

Codex 0.167.2 includes `.git` metadata in plugin content fingerprints. An ordinary
Git index refresh inside an installed plugin can therefore invalidate its content
approval even when tracked source is unchanged. Use `GIT_OPTIONAL_LOCKS=0` for
read-only Git inspection of installed plugin bundles. Review and bind fresh native
fingerprints before any later approval; never blindly copy this receipt's state.

Private evidence and the mode-0600 configuration preimage are stored under
`/Users/mitch/.local/state/oraclebot-hook-approval-20261112/`. The concise receipt is
`/Users/mitch/.local/state/oraclebot-hook-approval-20261112/verified-repair-summary.json`.
Raw inventories and configuration backups stay outside Git. The graph lesson is
KNOW-1929, linked to the ongoing Oraclebot audit task TASK-1540.

The full repository audit remains in progress. This hook repair is an independently
verified portion of that work, not a completion or deployment receipt for the site.
