# Standalone bot manager milestone 1

Version: 1.0.0
Date: 2026-11-09
Status: implementation under final review; delivery not yet complete.

The approved standalone manager design and implementation order remain authoritative.
The control-room UI is a future client of the manager state and command receipts.
The prototype does not introduce another supervisor, recorder, optimizer or signer.

## Supplemental findings incorporated

| Finding | Current contract |
| --- | --- |
| Independent identities | A specification has a stable UUID and immutable configuration revision/hash. Runtime session, owner identity and generation are separate nullable fields. Saving a draft starts no worker or capital reservation. |
| Explain what the bot is doing | Versioned status separates lifecycle, desired/observed state, owner reachability, heartbeat/data age, evaluation, decision/reason, blockers and next trigger. Missing observations remain null with a reason. |
| Independent state dimensions | Mode, lifecycle, input quality, evidence and submission certainty remain distinct. A saved running intent is not a worker heartbeat. |
| Precise controls | Per-bot receipts distinguish acknowledged, pending, skipped, failed and unknown. Stop does not claim cancel, close or disarm. Missing exposure stays visible as unknown. Ambiguous requests never automatically resubmit. |
| Immutable evidence | Status binds strategy/configuration/market/timeframe/execution-model identity. Dataset, proof, engine, costs and dates remain null when unavailable. Backtest, paper and live evidence stay separate. |
| Manual pins | Explicit overrides and value provenance persist independently from effective defaults. Editing/adoption of active configuration is unavailable in this slice. |
| Actual strategy capability | Canonical manager families are Grid, DCA, Trend, Momentum and Arbitrage. Council is external-only. Arbitrage remains unavailable until a verified Solana adapter exists. |
| Legacy family occupancy | Delegated SolTUI controls guard the occupied strategy-family slot across markets. Per-coin settings do not imply independent workers. |

Guarded controls require the owner protocol and compare the observed session and
configuration under owner locks. Old owners remain inspectable and refuse controls
that they cannot safely acknowledge. Browser inventory reports registration required;
Node FileStore is a different installation and does not represent browser state.

## Findings assigned to later milestones

| Milestone | Remaining implementation |
| --- | --- |
| 2 — multi-instance paper runtime | Genuine independent instances, durable owner generations, actual heartbeats/evaluations, stop/recovery and pinned runtime adoption boundaries. The first grid slice uses explicitly labelled Coinbase reference paper. |
| 3 — strategy/data certification | Five-family semantic adapters, immutable coverage/proof manifests and Jupiter-specific observations. Proxy data cannot certify executable Jupiter prices or routes. |
| 4 — blind research | Isolated anonymous judge packets, private parameter mapping and the shared exposure/holdout authority. |
| 5 — diagnostics/accounting | Measured realized/unrealized P&L, costs/cash flows, health/alerts, compatible comparisons and load/fault acceptance. |
| 6 — learning | Current/proposed values, evidence/provenance, protected pins, explicit adoption, shadow gates and rollback. |
| 7 — integration | Real browser discovery/control and the fleet roster/selected-bot inspector. The graphical client consumes manager state and receipts. |
| 8 — gated execution | Verified executor capabilities, wallet-level limits and submission/reconciliation gates. No unsupported live operation is inferred from a UI action. |

## Conflicts and resolution

The UI proposal suggested extension integration. The approved standalone manager
remains the execution authority; the graphical work stays in its integration phase.
The illustrative Council template does not replace Momentum in the manager registry.
The legacy one-slot restriction applies only to legacy adapters and does not restrict
the genuine multi-instance runtime in milestone 2.

Coinbase USD examples describe their actual proxy economics. They do not establish
Jupiter SOL/USDC compatibility, historical routes, executable prices or a profitable
edge. The UI prototype's 49 browser assertions verify only that prototype.

## Verification and delivery

Final review, installed-console acceptance and final-head CI/merge are pending.
No production service, live bot, signing path or graphical client is activated by
this milestone. Verification results will be recorded here before delivery.
