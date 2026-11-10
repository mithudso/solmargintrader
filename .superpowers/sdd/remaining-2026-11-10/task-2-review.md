# Task 2 independent review — version 3

Version: 3. Delta: 2 -> 3. Reviewed original Task 2 scope and frozen package, accounting/report remediation `bb50442e5835f0fd298e93b7d87c79d3d6fdd766`, shared learning-reader remediation `0dac4a1330b687275fc096e0eda9805862a14708`, and updated implementation report version 3.

## SPEC COMPLIANCE — PASS

No remaining findings in the reviewed Task 2 scope. FIFO partial closes allocate entry fees once, preserve retained fees, and separate transaction expenses. Cashflow-adjusted equity and rent neutrality retain their hand-calculated coverage. Missing/invalid fills, cashflows and marks now null affected values with reasons while preserving independently known values. Unknown residuals are distinct from an authoritative empty position. Canonical reference checkpoints retain simulator float lineage and independent virtual-account labels. Current/archive projections retain pinned identity/configuration attribution and currency/source compatibility checks. The common projection serves human, JSON and CSV consumers. SQL event/history/quote cursors use actual stable sequences and bounded next cursors, including gaps, append and replay.

The full integrity decoder now executes only inside a fixed evidence envelope: 8 MiB aggregate evidence, 4096 current fills, 128 segments, SQLite value/row cap and SQL VM budget. Oversized shapes explicitly refuse with report_budget_exceeded. This closes the original unbounded historical evidence read without trusting unchecked totals or weakening checkpoint/archive validation. Long-run reporting beyond that envelope remains explicitly unavailable until a trusted compact manifest exists.

The remaining shared learning-read finding is resolved. Each read-only metadata connection has a 32 KiB SQLite value/row cap and 100,000 VM-step budget. A capped candidate window preflights per-body and aggregate bytes before JSON decoding. Adoption lookup no longer evaluates JSON through arbitrary unrelated history. Missing coverage, corrupt pointers and exceeded budgets return explicit unavailable status. Exported pointer fields are validated and arbitrary payloads are omitted. The documented auxiliary envelope is additive: two 256 KiB sources plus the independently bounded 64 KiB schedule receipt, at most 576 KiB, separate from financial evidence.

## CODE QUALITY — PASS

No remaining medium-or-higher findings. Pure accounting, attributed report selection and rendering remain separated clearly. Read-only transactions pin preflight and decoder reads, strict page checks protect public arguments, and remedial tests target the actual failures. The shared reader fails closed without raw payload leakage, database initialization, schema migration or owner subprocesses. No style-only changes requested.

## Independent evidence and remaining release gates

Reviewed both exact remediation diffs and focused regressions. The accounting/report tests address malformed/null marks, independently incomplete ledgers, large segment/fill/archive refusal, SQL work bounds and retained corruption denial. Public report/status regressions cover metadata above 8 MiB and 10,000 unrelated adoption rows, small explicit unavailable outputs and byte-for-byte database nonmutation. Reader tests cover malformed/deep JSON, pointer validation, per-record/aggregate caps, unindexed scan bounds, valid states and the schedule cap.

Independently reran the exact original oversized-learning-payload reproduction in a temporary SQLite database. The corrected reader returned state=unavailable, an empty proposals list, omitted the payload and left database bytes unchanged; command exit 0. Existing reported covering checks are 41 accounting/report/learning-read/learning tests, Ruff lint and format, all exit 0. No broad suites were rerun during review. No live application state, service, install, orders or product source changed. Only this review artifact was updated.

This is source/spec acceptance, not an assertion of completed deployment. Controller still owns final full manager/affected Oracle suites, independent installed acceptance and verified remote default-branch delivery.
