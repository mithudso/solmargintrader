# Oracle feed controls and scoped UI review

Version: 2.0.0
Delta: complete current-source no-edit sweep after the PR303 preview-layout repair.

Status: **NEEDS_EVIDENCE**. The implemented controls and the scoped source/rendered behavior pass their checks. Missing native evidence prevents a clean UX claim. A fresh independent review and actual installed acceptance remain with the parent delivery task.

The source implementation is frozen at `347420978a439c169dc628a7ffbe8d4313c02e9a`. Its exact rendering-source fingerprint is `1bbcbb1b28b6daf2d926c3875effb6bc97d8b141698a9360681be82d8a31d24e`. The source includes the current-format SDK disclosure from PR303. No wallet, armed configuration, protected TUI or shared collector was changed by this work.

The target is the Oracle wrapper → Leverage panel, for the owner, on macOS with the installed Textual renderer. The frozen matrix contains 16 states at 80×24, 120×42 and 180×60: live, either provider hidden, both hidden, re-enabled, loading, stale, empty, missing/partial data, unsupported shape, backend failure, unsigned preview, synthetic armed/blocked-close, keyboard, mouse and asset-switch states. Full selection and cells are recorded in /Users/mitch/dev/worktrees/oracle-ui-2399/docs/design/oracle-ui-2399/scope.json. The initial scope is retained alongside it; only the accepted Console rendering dependency was added.

| Review stage | Methods | Source edits | Outcome |
| --- | ---: | --- | --- |
| Initial full sweep | 48 | Yes | Six defects repaired; selected evidence gaps retained |
| PR303 integration inspection | Partial | Yes | Long current-format preview exposed one further layout defect; repaired immediately |
| Final full sweep | 48 | No | No unresolved confirmed Medium+; seven selected evidence gaps |

The run completed two full sweeps under the default five-sweep cap. The intervening integration inspection is not counted as a complete sweep. Research P49–P70 was unrequested and remained OUT_OF_SCOPE. No participant studies, analytics, messages or inference jobs ran.

Final method coverage: 37 PASS, 4 N_A, 5 PARTIAL, 2 UNAVAILABLE, 22 OUT_OF_SCOPE. N_A applies only to observed absences: images, localization/RTL mode, search and interactive AI controls.

| ID | Severity | Repair |
| --- | --- | --- |
| UI-001 | Medium | Independent persistent view switches remove provider content and mixed basis; foreground Coinbase subscription pauses |
| UI-002 | High | Short terminals scroll while feed switches and Return stay visible |
| UI-003 | Medium | Snapshot failure has a visible Refresh recovery notice |
| UI-004 | Medium | Bar labels select black/white for contrast; Preview uses a darker blue |
| UI-005 | Medium | LIVE/DELAYED/STALE and STALE PAIR remove color-only status meaning |
| UI-006 | Medium | Null nested provider/model sections remain recoverable instead of crashing |
| UI-007 | Medium | Long market previews scroll in a bounded region and show the critical consequence summary first |

All seven findings have current-source check/render receipts in /Users/mitch/dev/worktrees/oracle-ui-2399/docs/design/oracle-ui-2399/report.json. Final unresolved severity totals are 0 Critical / 0 High / 0 Medium.

Completed checks: 85 integrated tests passed with ResourceWarning treated as an error; pinned Ruff 0.17.4 and owned-file format checks passed; all 48 rendered cells completed with zero disabled-provider text leaks, zero execute calls and joined owned panel workers; the ledger validator returned valid=true. The 201 bar-intensity values meet 4.5:1 for their selected label foregrounds. These are controlled-fixture results, not funded execution, user-study or field-performance results.

The full raw captures, actions, source/runtime identity, command logs and continuation are under /Users/mitch/.local/state/oracle-ui-2399. The capture driver is /Users/mitch/.local/state/oracle-ui-2399/capture.py. Native fixture previews call the actual Console.preview with fake CLI/SDK adapters in a temporary home. The screenshots in /Users/mitch/dev/worktrees/oracle-ui-2399/docs/design/oracle-ui-2399/screens are synthetic examples.

Remaining selected evidence:

- P18 PARTIAL: Repaired measured bright-bar label failure by choosing black/white from actual luminance; 201 intensities satisfy 4.5:1. Preview now uses opaque white on darker blue. Default rendered colors are available; actual user terminal font/palette and every system-theme pair remain unavailable, so no full WCAG conformance claim.
- P19 PARTIAL: Checked default comparison enclosure, checkbox mark and focus boundary against the dark surface. The macOS terminal accessibility/color pipeline and full selected-state compositing measurements are unavailable; retain this as partial rather than infer all contrast from screenshots.
- P29 UNAVAILABLE: Textual DOM/widget labels and values are inspectable, but this harness has no native terminal accessibility-tree bridge. A DOM dump cannot stand in for the native accessibility exposure required by this selected method.
- P30 PARTIAL: Terminal-column reflow at 80/120/180 columns and short-height scrolling were exercised and the disappearing-control defect was repaired. Native terminal font scaling/line spacing and its OS accessibility interaction are not available to this fixture renderer; no WCAG resize claim is made.
- P33 PARTIAL: The panel has no autoplay or intentional flashing; price updates retain focus and feed switches reduce visible data. Textual focus scrolling animates. Native reduced-motion preferences and terminal sensory behavior were not available, so this selected evidence remains partial.
- P39 PARTIAL: Actual Textual APIs and run_test execute on this macOS Python environment, with keyboard/pointer fixtures and three terminal sizes. Native Terminal event delivery and the newly installed revision are separate pending acceptance evidence. Context7 was quota-blocked; no new library API assumptions were substituted as documentation results.
- P41 UNAVAILABLE: No runnable VoiceOver/screen-reader automation or spoken-output capture is available in this harness. The selected assistive-technology task cannot be replaced by expert inference, terminal screenshots or widget names.

Evidence kinds are EXECUTED commands, OBSERVED actual Textual event/render behavior and EXPERT inspection. There is no PARTICIPANT evidence. No ISOLATED final-review receipt is claimed yet. The parent will dispatch a fresh read-only reviewer, then complete CI/merge and independently verify the actual canonical wrapper and an owned monitor. The current protected replacement user TUI is PID 35320; reinventory before any lifecycle action.

Snapshot & rollback: the original owned source preimages are preserved under /Users/mitch/.claude/skill-consolidation/backups/ui-deep-optimizer-20261116-1537. For the isolated candidate only, the literal panel restore command is:

```sh
cp /Users/mitch/.claude/skill-consolidation/backups/ui-deep-optimizer-20261116-1537/research/zec_leverage_panel.py /Users/mitch/dev/worktrees/oracle-ui-2399/research/zec_leverage_panel.py
```

Restore only after verifying ownership/current hashes; do not replace the separately owned SDK Console or another active checkout. Source tests, rendered fixtures and installed behavior remain separate acceptance gates.
