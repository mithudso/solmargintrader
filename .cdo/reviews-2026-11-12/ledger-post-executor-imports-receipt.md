## Passes that ran (receipt)

| Pass | State | Files | Note |
|---|---|---|---|
| C1 | ran | 4 |  |
| C2 | ran | 4 |  |
| C3 | ran | 4 |  |
| S1 | ran | 4 |  |
| S2 | ran | 4 |  |
| S3 | ran | 4 |  |
| S4 | ran | 4 |  |
| S5 | ran | 4 |  |
| P1 | ran | 4 |  |
| P2 | ran | 4 |  |
| M1 | ran | 4 |  |
| M2 | ran | 4 |  |
| M3 | ran | 0 | Exact four test import-only deltas preserve architecture; earlier repository M3 Medium settings/error/sink residuals remain PARTIAL. |
| M4 | ran | 4 |  |
| T1 | ran | 4 |  |
| T2 | ran | 0 | Exact import multiset and all non-import AST preserved; dependencies/locks/advisory graph unchanged; inherit scoped prior T2 receipt and explicit limits. |
| T3 | ran | 0 | Root reproduced CI I001; four import groups corrected. Component Ruff0.17.4 check src/tests and format38files both completed0; full offline557passed/5networkdeselected exit0. Final remote CI remains separate. |
| T4 | blocked | 4 | Global parallelism/setup-hoisting equivalence remains BLOCKED (ambiguous intent/equivalence). Four import-only deltas preserve test semantics and distinct assertions; no unsafe thread rewrite. |
| M5 | na | 0 | This delta contains only four existing pytest modules, no new user entrypoint. Existing41file M5 qualification limitations remain explicitly partial in remaining-source-dispositions.json. |

Fix-track passes that ran: 17 of 18 (+0 conditional)
Mode: incremental   Status: FULL_SOURCE_INSPECTION_SHORT_INTEGRATION_GREEN_SOLTUI_AND_DELIVERY_PENDING
Files reviewed this run: 4
Source files covered by the ledger now: 824 of 824
Still unreviewed or changed since review: 0
