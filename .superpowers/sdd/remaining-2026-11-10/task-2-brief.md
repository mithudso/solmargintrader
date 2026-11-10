# Global constraints

- Defaults remain paper and disarmed. Saving a specification starts no worker, reserves no live capital and submits no order.
- Preserve distinct bot UUID, runtime ID, owner identity, generation and configuration revision/hash. Saving an edit never mutates an active run.
- Use the existing canonical algorithms. Grid ladder, DCA safety orders, buffered next-open Trend and time-series Momentum retain their exact semantics. Arbitrage remains conditional evidence unless verified execution exists. Council remains external-only initially.
- The manager uses one existing research authority. A new home, UUID, fingerprint or seed cannot reset attempts or reopen exposed dates.
- Missing price, amount, fee, mark or measurement remains unavailable with a reason. Never convert it to zero or guess a value that becomes an order.
- Process liveness, input quality, evaluation progress, evidence quality and submission certainty remain separate fields.
- Pause entries, stop owner, cancel orders, close positions and emergency kill/disarm are separate operations. Keep residual exposure and partial or unknown outcomes visible.
- Reconcile before planning. An ambiguous submit is never automatically retried. Preserve accepted request IDs and unresolved reservations across crashes.
- Reads do not initialize a database, start a producer, install a service, arm, optimize or adopt configuration.
- No new third-party runtime dependency unless an existing requirement cannot be met with the declared stack and the need is documented.
- Do not alter active immutable environments or another session's experiments to manufacture research coverage.
- Required checks must finish successfully. Every completed milestone reaches the remote default branch after final-head CI and independent installed acceptance where applicable.
- Keep /Users/mitch/dev/solmargintrader/prompts.md and /Users/mitch/dev/solmargintrader/memory.md versioned. Stage explicit task-owned files only.


### Task 2 — Implement M5 accounting and useful reports

**Tracking:** TASK-1111. **Depends on:** Task 1's immutable run/evidence/receipt contract.

**Tests:** /Users/mitch/dev/solmargintrader/botmanager/tests/test_accounting.py; /Users/mitch/dev/solmargintrader/botmanager/tests/test_reports.py; /Users/mitch/dev/solmargintrader/oracle/tests/test_quotes.py.

**Interfaces:** Add pure `accounting_snapshot(run: Mapping[str, Any]) -> dict[str, Any]` in the accounting module and `report_page(store, bot_id: str, *, run_id: str | None, after: int, limit: int) -> dict[str, Any]` in the reports module. Public `report` supports human, JSON and CSV rendering from the same projection. Pages return stable sequence cursors and a bounded next cursor; row count is never a cursor.

- [ ] Write `test_fifo_partial_close_charges_each_fee_once`, `test_cashflow_identity`, `test_missing_mark_keeps_pnl_null` and `test_rent_is_not_profit`. Assert `equity = cash + marked_inventory` and `net_pnl = equity − starting_equity − deposits + withdrawals`. Use hand-calculated entry/exit fees, retained inventory, deposits/withdrawals and transaction expense; an unknown required component makes the affected total null with a reason.
- [ ] Implement exact Decimal arithmetic where the input is exact. Preserve reference simulator float lineage. Keep realized/unrealized, gross/net, costs, cash flows and unresolved residuals explicit. Separate backtest, reference paper, prospective paper and live; separate USD and USDC. Independent virtual accounts are not a funded wallet total.
- [ ] Add attributed reports and export for current/archived runs, configuration/provenance, source/timeframe, dataset/cost/engine identity, sample size, learning/selection status and loss cohorts. Compatible benchmarks may compare; incompatible ones return the mismatch.
- [ ] Add stable bounded pagination for events, reports and history. In the Oracle owner add a versioned quote-page result carrying each SQLite sequence plus `next_after`; preserve old list callers. Test ignored inserts/sequence gaps, append during paging and exact replay.
- [ ] Run accounting/report/quote tests, full manager tests and the affected Oracle tests. Check old run attribution and no database mutation during reads. Commit explicit owned paths for review with Task 3.

**Done means:** a user can see where profit/loss came from, what costs are included and what is unknown, in all three formats, without loading an unbounded archive or double-counting capital/fees.
