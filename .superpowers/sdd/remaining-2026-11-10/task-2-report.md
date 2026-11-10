# Task 2 — accounting/reports implementation

Status: source implementation and owned tests complete; controller owns registry/CLI integration, full-suite/release and installed verification.

Added pure Decimal FIFO accounting with quote-denominated entry/exit fees, partial inventory fee allocation, cashflow-adjusted equity identity, explicit missing marks/fees, retained inventory, refundable rent assets and transaction expenses. Canonical reference checkpoints retain original floats and are labelled independent virtual accounts.

Added keyed current/archived report selection with pinned configuration/provenance, source/timeframe, dataset/cost/engine identity, sample and learning/selection labels, compatible comparison checking, common human/JSON/CSV projection. Event pages use SQL sequence bounds; revision history pages use revision cursors; archived run indexes use SQL rowid and current runtime is separate metadata. A report pages runtime events, not the entire archive. Individual immutable checkpoint/archive bodies remain bounded by existing runtime limits and validated by existing decoder.

Oracle read_quote_page adds versioned sequence-bearing items, next_after and has_more. read_quotes remains the legacy list projection. Ignored inserts cannot cause duplicate/omitted paging.

Integration: import report_commands.command_specs after CommandSpec definition, add returned definitions to COMMANDS; report_command returns page/format/rendered. CLI prints rendered for human/CSV; normal JSON stays envelope. Existing registry history/events should route bounded APIs if public pagination is desired; controller owns shared integration.

Verification: owned accounting/report/Oracle quote suites: 21 tests passed, exit 0. Includes hand arithmetic (cash 984, equity 1056, net 26, realized 18.2, unrealized 10.8), missing values, rent neutrality, immutable archived configuration attribution, byte-for-byte read nonmutation, gaps/append/replay. Ruff executable absent from solbot environment; system ruff used separately. Full manager and affected Oracle suites and installed acceptance remain controller release gates.

Limitations: no wallet aggregation; live/backtest event import absent. Generic exact ledger supports long FIFO spot inventory only and refuses oversells. Existing reference engine owns its gross attribution; unavailable gross is explicit. Report cannot manufacture absent measurements or certify Jupiter execution. Stopped/quiescent archive/current semantics remain owner contract.

## Independent review remediation — version 2

Version: 2. Delta: 1 -> 2. Status: owned review findings fixed and covering checks passed; controller owns final integration/delivery.

Supersedes the earlier claim that archive bodies are inherently bounded by runtime segment limits. They are not. Reports now preflight evidence with SQL length projections and capped row counts before any full runtime/archive fetch or decoder call. The read-only transaction pins the preflight and decoder to one snapshot. A fixed 8 MiB aggregate evidence budget, 4096 current fill rows, 128 runtime segments, SQLite 8 MiB value/row limit, and 2,000,000 SQL VM instruction budget bound verification independently of historical growth. Oversized historical shapes fail with `report_budget_exceeded` and explain that a trusted compact manifest is required. The existing checkpoint hash, canonical simulator validation, fill reconciliation, segment chain and archive checksum checks remain mandatory inside the envelope. No database/schema initialization or unchecked financial total was introduced. Reports for bounded legacy/current/archive shapes remain useful; arbitrarily long history cannot be reported until an explicit writer provides a trusted compact manifest.

Accounting now tracks fill and cashflow completeness independently. Missing/invalid fills null traded/marked inventory and residuals with reasons while preserving complete cashflow/rent measurements. Missing/invalid cashflows null rent, marked inventory and cash/equity/net totals while preserving complete FIFO trade attribution. Unknown residuals use null plus `residuals_reason`, distinct from an authoritative empty list. None/nonmapping marks and nonmapping fill/cashflow entries return unavailable measurements instead of raising AttributeError. Existing fees, gross/net identities and canonical reference floats remain unchanged.

Added regressions: malformed marks; absent and malformed ledgers including a malformed late fill/cashflow; unaffected known totals; canonical reference loss/fee float lineage; refusal before decoding with 629 segment rows, 4097 fill rows or an archive above 8 MiB; SQL scan work refusal; and retained corruption rejection. Existing archive attribution, currency/source comparison, exact fee arithmetic, page replay and read-nonmutation tests continue to pass.

Final verification from `/Users/mitch/dev/solmargintrader-wt-01a1c447`:

- `PYTHONPATH=botmanager/src:botmanager /Users/mitch/.venvs/solbot/bin/python -m unittest tests.test_accounting tests.test_reports -v` — exit 0, `Ran 24 tests in 0.127s`, `OK`.
- `ruff check botmanager/src/botmanager/accounting.py botmanager/src/botmanager/reports.py botmanager/tests/test_accounting.py botmanager/tests/test_reports.py` — exit 0, `All checks passed!`.

An initial test invocation from the component directory failed because reference-input setup resolves repo-root paths. Re-running the exact covering suite from the repository root passed. No external service, install or application state changed. Remaining: controller's independent re-review, full manager/affected Oracle checks, installed acceptance and final remote delivery. Workflow prompts/memory and task tracking remain controller-owned.

## Shared learning read remediation — version 3

Version: 3. Delta: 2 -> 3. Status: shared-reader integration finding fixed; independent re-review and controller delivery remain.

Changed only `learning_snapshot` in the learning module; owner/writer/adoption behavior is unchanged. Each of its two read-only SQLite connections now enforces a 32 KiB SQLite row/value cap and 100,000 SQL VM instruction budget. Preflight selects at most 257 rowid/body-length pairs; more than 256 candidates refuses the source. Each body must be at most 16 KiB and each source's aggregate bodies at most 256 KiB before JSON transfer/decoding. Legacy adoption lookup no longer evaluates `json_extract` across history. It checks a bounded rowid window and explicitly reports unavailable metadata if that window cannot cover the legacy table. Proposal filtering is also instruction-bounded even without a bot_id index. No read creates an index or migrates/initializes a database.

The auxiliary input envelope is two 256 KiB sources plus the existing independent 64 KiB schedule-file cap: at most 576 KiB, separate from the financial report's 8 MiB evidence envelope. Each source returns at most 20 validated small pointers. Validation requires bounded identity/state strings, scalar pointer fields and bounded nonnegative integer counts. Unknown document payload fields are excluded. Invalid, oversized, incomplete or SQL-budget-exhausted sources return `local_metadata` unavailable reasons and overall `local_learning_metadata_unavailable`; no raw body or SQLite exception escapes. Known valid arrays remain visible, and fully valid proposal/adoption states retain their values.

New public report/status regressions exercise a proposal body above 8 MiB and 10,000 unrelated adoption rows. Both surfaces remain small, explicitly show unavailable learning metadata, omit the payload, and leave all SQLite files byte-for-byte unchanged. Focused reader regressions cover per-body/aggregate caps, malformed/deep JSON, invalid shapes, 50,000 unrelated unindexed proposal rows, valid proposal/adoption states and the schedule cap.

Final verification from `/Users/mitch/dev/solmargintrader-wt-01a1c447`:

- `PYTHONPATH=botmanager/src:botmanager /Users/mitch/.venvs/solbot/bin/python -m unittest tests.test_accounting tests.test_reports tests.test_learning_reads tests.test_learning -q` — exit 0, `Ran 41 tests in 1.186s`, `OK`. Existing reference metrics emitted two scalar-power overflow RuntimeWarnings; no check failed.
- `ruff check botmanager/src/botmanager/learning.py botmanager/tests/test_learning_reads.py botmanager/tests/test_reports.py` — exit 0, `All checks passed!`.
- `ruff format --check botmanager/src/botmanager/learning.py botmanager/tests/test_learning_reads.py botmanager/tests/test_reports.py` — exit 0, three files formatted.

Remaining: independent re-review, controller full-suite/installed acceptance and remote default-branch delivery. No external service, install or live application state changed.
