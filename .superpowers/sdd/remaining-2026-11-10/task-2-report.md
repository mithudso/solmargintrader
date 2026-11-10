# Task 2 — accounting/reports implementation

Status: source implementation and owned tests complete; controller owns registry/CLI integration, full-suite/release and installed verification.

Added pure Decimal FIFO accounting with quote-denominated entry/exit fees, partial inventory fee allocation, cashflow-adjusted equity identity, explicit missing marks/fees, retained inventory, refundable rent assets and transaction expenses. Canonical reference checkpoints retain original floats and are labelled independent virtual accounts.

Added keyed current/archived report selection with pinned configuration/provenance, source/timeframe, dataset/cost/engine identity, sample and learning/selection labels, compatible comparison checking, common human/JSON/CSV projection. Event pages use SQL sequence bounds; revision history pages use revision cursors; archived run indexes use SQL rowid and current runtime is separate metadata. A report pages runtime events, not the entire archive. Individual immutable checkpoint/archive bodies remain bounded by existing runtime limits and validated by existing decoder.

Oracle read_quote_page adds versioned sequence-bearing items, next_after and has_more. read_quotes remains the legacy list projection. Ignored inserts cannot cause duplicate/omitted paging.

Integration: import report_commands.command_specs after CommandSpec definition, add returned definitions to COMMANDS; report_command returns page/format/rendered. CLI prints rendered for human/CSV; normal JSON stays envelope. Existing registry history/events should route bounded APIs if public pagination is desired; controller owns shared integration.

Verification: owned accounting/report/Oracle quote suites: 21 tests passed, exit 0. Includes hand arithmetic (cash 984, equity 1056, net 26, realized 18.2, unrealized 10.8), missing values, rent neutrality, immutable archived configuration attribution, byte-for-byte read nonmutation, gaps/append/replay. Ruff executable absent from solbot environment; system ruff used separately. Full manager and affected Oracle suites and installed acceptance remain controller release gates.

Limitations: no wallet aggregation; live/backtest event import absent. Generic exact ledger supports long FIFO spot inventory only and refuses oversells. Existing reference engine owns its gross attribution; unavailable gross is explicit. Report cannot manufacture absent measurements or certify Jupiter execution. Stopped/quiescent archive/current semantics remain owner contract.
