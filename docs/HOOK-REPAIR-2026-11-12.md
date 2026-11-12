# Codex hook repair, 2026-11-12

Version: 1.2.0
Delta: v1.1.0 to v1.2.0; repair metadata-only recurrence, restore Stripe declarations and record independent natural acceptance.
Delta: v1.0.0 to v1.1.0; add independent loaded-daemon acceptance.

## Latest accepted state

The owner reported another three approval failures after the initial repair.
Runtime source bytes and approved detached commits were unchanged. Plugin Git
metadata changed at 19:06:37–19:07:16 UTC, invalidating the saved content
fingerprints. The initiating cache writer is unproven. A controlled probe did
not show read-only `rev-parse` or `diff` with `GIT_OPTIONAL_LOCKS=0` refreshing
the index; do not attribute this recurrence to those commands without evidence.

At 20:33:19 UTC, a fresh native version-checked write changed exactly eight
`trusted_content_hash` fields. Handler approvals, enablement, Stripe fields and
unrelated concurrent settings were preserved. All eight load trusted in the
Oraclebot checkout, audit worktree and MoreLube context.

A separate coordinated repair restored Stripe's canonical command declarations:
the supported scoped migration inlined seven argument arrays. Bare `node`
commands must not be approved when their separate arguments would be ignored.
An empty-edits native reload then recognized the already approved declarations.
This step made no approval or user-configuration edits. The five Architect
hooks and two Stripe post hooks remain disabled.

Independent acceptance at 20:41 UTC checked the same running daemon, PID 53949:
111 hooks loaded, no enabled untrusted hook, 55 reviewed files matching, and 65
natural completions with zero failures, including ten AI Plugins and five
Remember completions. Configuration stayed byte-identical. An earlier separate
post-repair window recorded 117 completions, including 18 AI Plugins and nine
Remember completions, with no errors. These are separate observation windows,
not a claimed deduplicated total.

Both enabled Stripe commands also exited zero with synthetic hook input. Native
Stripe SessionStart/UserPromptSubmit events were not forced and remain
unobserved. The daemon was not restarted and no new model turn was started for
the independent acceptance.

Private receipts:

- `/Users/mitch/.local/state/oraclebot-hook-approval-20261112/recurrence-20261112-1409/recurrence-repair-receipt.json`
- `/Users/mitch/dev/morelube/.private/hook-repair-20261112/native-reload-receipt.json`
- `/Users/mitch/dev/morelube/.private/hook-repair-20261112/stripe-migration-receipt.json`
- `/Users/mitch/dev/morelube/.private/hook-repair-20261112/independent-acceptance-summary.json`

The historical exit-126 cause remains unproven. The accepted state above repairs
the observed current content-approval and Stripe declaration failures.

## Initial diagnosis and acceptance

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

An independent live-acceptance verifier subsequently confirmed the exact eight
parsed configuration changes, preserved enabled flags and three matching bundle
fingerprints on the existing daemon, PID 53949. A fresh observation captured six
more matching natural hook completions with zero errors. Configuration and hook
files remained unchanged during verification. Its private receipt is
`/Users/mitch/.local/state/oraclebot-hook-approval-20261112/independent-final-acceptance.json`.

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
