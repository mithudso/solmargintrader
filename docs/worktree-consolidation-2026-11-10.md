# Worktree consolidation — 2026-11-10

Version: 1.0.0
Delta: Preserve every requested input before removing duplicate working copies.

The fifteen owner-named sibling folders have been consolidated into `/Users/mitch/dev/solmargintrader`. Accepted changes already present on `origin/master` were not replayed over newer source. One stranded catalog coverage test and the missing README optimizer request were integrated. The older quickstart addition and the experimental executor decoder remain recoverable as historical edits.

## Private recovery

The canonical entry is `/Users/mitch/dev/solmargintrader/.worktree-recovery`. It points to `/Users/mitch/.local/state/solmargintrader/consolidation-01a1c44a/recovery-v2`. The private SQLite database stores unique non-Git content once. The independent mirror at `/Users/mitch/.local/state/solmargintrader/consolidation-01a1c44a/rebuilt.git` retains all inventoried historical heads. Both repositories pin those heads under `refs/consolidation/20261110-01a1c44a/`. Do not delete the mirror while snapshots reference its blobs.

Fourteen surviving inputs contained 73,153 regular files and 2,289,709,056 bytes before deduplication. The database was 217,292,800 bytes before late Finder metadata was added. The original completed plan worktree had already been removed by its owner after PR191 merged. Its Git head and initial inventory remain retained.

Every snapshot content object was read and SHA-256 checked against the independent mirror or compressed private storage. Every source path, file hash, permission, symlink and Git status matched immediately before cleanup. Full restoration and independent rehashing passed for the 6,446-file standalone comparison and the 3,963-file strategy-poc worktree. The latter also reproduced the current snapshot's staged and unstaged state. Finder changed a few metadata files during removal; the residual snapshot preserves those additional bytes. `cleanup-receipt.json` records the exact late paths.

List or verify without restoring files:

```sh
python3 /Users/mitch/dev/solmargintrader/.worktree-recovery/recover.py list
python3 /Users/mitch/dev/solmargintrader/.worktree-recovery/recover.py verify
```

Restore a named snapshot to a new destination:

```sh
python3 /Users/mitch/dev/solmargintrader/.worktree-recovery/recover.py restore solmargintrader-wt-01a1c189-editing /Users/mitch/dev/solmargintrader-m4-restored --worktree
```

The destination must not exist. Restoration never changes the canonical source. A restored worktree belongs to the independent recovery repository. Its installer environments, caches and old absolute script paths are historical evidence; restoring files is not runtime qualification.

## Input dispositions

| Original absolute path | Disposition |
| --- | --- |
| `/Users/mitch/dev/solmargintrader-wt-ui-tables-01a1bee5` | Removed after snapshot; committed head is already an ancestor of accepted master. Dirty historical edits remain in recovery. |
| `/Users/mitch/dev/solmargintrader-wt-ui-resume-01a1bee5` | Removed after snapshot; committed head is already an ancestor of accepted master. Dirty historical edits remain in recovery. |
| `/Users/mitch/dev/solmargintrader-wt-strategy-poc` | Removed after private snapshot. Unfinished draft PR182 and branch retained; no unfinished feature activated. |
| `/Users/mitch/dev/solmargintrader-wt-referral` | Removed after snapshot; committed head is already an ancestor of accepted master. Dirty historical edits remain in recovery. |
| `/Users/mitch/dev/solmargintrader-wt-guides` | Removed after snapshot and merged PR101 receipt. Stranded test/workflow edits preserved or integrated. |
| `/Users/mitch/dev/solmargintrader-wt-01a1c228` | Removed after snapshot; committed head is already an ancestor of accepted master. Dirty historical edits remain in recovery. |
| `/Users/mitch/dev/solmargintrader-wt-01a1c189-remaining-plan` | Owner removed after PR191 merged; historical head and initial inventory retained. |
| `/Users/mitch/dev/solmargintrader-wt-01a1c189-editing` | Removed after private snapshot. Unfinished draft PR192 and branch retained; no unfinished feature activated. |
| `/Users/mitch/dev/solmargintrader-wt-01a1c189` | Removed after snapshot; committed head is already an ancestor of accepted master. Dirty historical edits remain in recovery. |
| `/Users/mitch/dev/solmargintrader-wt-01a1c1b1` | Removed after snapshot; committed head is already an ancestor of accepted master. Dirty historical edits remain in recovery. |
| `/Users/mitch/dev/solmargintrader-wt-01a1c1a0` | Removed after snapshot and merged PR173 receipt. Stranded test/workflow edits preserved or integrated. |
| `/Users/mitch/dev/solmargintrader-wt-01a1bf0e` | Removed after snapshot; committed head is already an ancestor of accepted master. Dirty historical edits remain in recovery. |
| `/Users/mitch/dev/solmargintrader-wt-01a1bee5` | Removed after snapshot and merged PR156 receipt. Stranded test/workflow edits preserved or integrated. |
| `/Users/mitch/dev/solmargintrader-wt-01a1bec1` | Removed after snapshot and merged PR154 receipt. Stranded test/workflow edits preserved or integrated. |
| `/Users/mitch/dev/solmargintrader-strategy-comparison-20261109` | Removed after full snapshot and restore proof. Canonical original/candidate source copies match all 3,645 non-cache experiment files. |

## Concurrent-copy incident and limitations

A second copy process replaced the canonical `.git` directory with the integration worktree's `.git` pointer. This invalidated all worktrees and removed the first verified recovery database. Cleanup stopped before deleting a source folder. The owner confirmed the copy and then confirmed it had stopped.

Git metadata was rebuilt from a separate remote mirror. Every inventoried source head and the active nested SolTUI head was recovered. The working files were retained. Original staging distinctions, reflogs, and any uninventoried local-only metadata could not be recovered. The replacement indexes represent each recorded HEAD; the second snapshot preserves the working edits and their reconstructed status. The independent mirror and second archive now live outside `.git`.

The copy had also placed obsolete M4 documentation and thirteen new untracked files/directories into the canonical checkout. Each was hash-checked against the post-copy snapshot and the unfinished M4 source before reconciliation. The six affected tracked files were restored to accepted master; the twelve draft Python files and the duplicated OpenCode directory were removed after preservation. Existing unrelated untracked files, production datasets, services and the locked nested SolTUI worktree were retained.

The unfinished feature checkpoints remain drafts:

https://github.com/mithudso/solmargintrader/pull/182

https://github.com/mithudso/solmargintrader/pull/192

## Verification and delivery

The card/catalog regression run executed 49 tests successfully, with one expected skip because the external TradingView catalog is absent. Documentation, wiki and offline retrieval-index checks are required before publication. Final PR, CI, merge and canonical synchronization receipts belong to the consolidation task TASK-1223 and its delivery stage TASK-1227. This report is not a claim that either unfinished draft feature works or that an installed service was changed.
