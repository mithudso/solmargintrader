# Testing

```bash
python3 -m unittest discover -s backtester/tests -t .   # 542 tests
python3 -m unittest discover -s soltui/tests -t .       # 313 tests (~300s)
cd extension && npm test                                # 131 tests
python3 scripts/check_docs.py                           # these counts, and the retrieval indexes
```

986 tests total, no test-framework dependency in any component (`unittest` and `node:test`).

Every count on this page is checked by `scripts/check_docs.py`, which counts the suites by
discovery and fails on a stale figure. That exists because these numbers were wrong for
several commits — the docs claimed 250 backtester tests while the suite had grown to 454, and
nothing caught it.

## Extension — what the 131 tests cover

| Area | Examples |
| --- | --- |
| Grid math | Arithmetic and geometric ladders against hand-computed values; endpoint pinning; degenerate configs rejected |
| **Round-trip economics** | An exit rests one rung above its lot, never at the same level; `gross === notional × rungWidth` |
| Planning | Lot aggregation (two lots on one rung produce **one** order, not a duplicate key); venue minimum; deadband; already-resting suppression |
| Risk rails | Each rail fires on its own breach; a batch cannot collectively breach a cap each member passes; rails **fail closed** on missing or NaN state; unusable orders blocked |
| P&L | FIFO across lots; partial closes realizing a proportional share of entry fees; carry subtracted; fees turning a gross win into a net loss; unmatched sells surfaced |
| Reconciliation | A venue echoing fewer decimals is matched, **not duplicated**; a missing order is orphaned and never auto-retried; unknown live orders adopted; two near-identical orders do not bind to one intent |
| Tick guards | Unusable price aborts before P&L; the daily counter measures today, not lifetime; a short grid on a spot venue says so |
| Wallet | base58 against real mints and the all-zero pubkey; shortvec boundaries; signature insertion into the correct slot; non-signer refused |
| Crypto | Sealed-seed round trip; wrong passphrase fails closed; fresh salt and IV per seal; Ed25519 signing |
| **Surface parity** | Every command routable over the API; `GET` restricted to read-only; CLI help lists all commands and every argument; UI messages all map to real commands |

The parity suite probes all 22 commands with a deliberately invalid argument, which proves the route
resolved **without executing the handler** — no side effects, no network calls.

## What is NOT covered

Read this before trusting anything with money.

1. **No live order has ever been placed.** The write path (auth → vault → deposit craft → sign →
   create) matches the documented shapes but has never executed. It needs an API key and a funded
   wallet. Test with one rung at the $10 minimum.
2. **The Trigger order-list response envelope is guessed.** `normaliseOrders()` infers field names for
   the orders/history endpoint, and reconciliation depends on them. Verify against a real response.
3. **Fee attribution is unconfirmed.** Fills take `feeUsd` from the venue when present and 0
   otherwise. Zero fees make a grid look better than it is.
4. **Signature insertion is tested against synthetic transactions**, not a real Jupiter deposit.
5. **Loading unpacked in Chrome is not automated.** `chrome://extensions` requires a human. The
   headless dry run is the integration gate instead; the CI job validates the manifest statically.
6. **The Chrome alarm floor is assumed to be 30s.** The engine logs the real wake delta — watch it
   before trusting a sub-minute tick.

## Verification commands

```bash
cd extension

npm test                                              # unit + parity
node tools/dryrun.js --ticks 8 --osc 6 --offline 100  # a round trip must close positive
node tools/dryrun.js --ticks 4 --walk 5 --offline 100 # trending case: bids fill, no exits
node tools/verify-endpoints.js                        # live Jupiter reachability
find src tools test -name '*.js' -print0 | xargs -0 -n1 node --check
```

The oscillating dry run is the meaningful one: it is the only check that closes a round trip and so
the only one that can detect a zero-spread regression.

## Backtester — 542 tests

Correctness of the simulation is the priority, so the suite concentrates on the things that silently
inflate a result: **lookahead leaks**, cost application, and metric arithmetic. Any change touching
signal generation or fill timing needs a test that would catch a one-bar leak. See
`backtester/README.md`.

32 of those cover the ladder-grid simulator (`core/gridsim.py`), and they exist because that module
has to agree with `extension/src/core/grid.js` about what a round trip earns. Three groups matter
most: the **round-trip invariant** (gross `== notional × rung width`, plus rung width asserted
against the JavaScript implementation's own figures), the **no-lookahead group** (nothing fills on
bar 0; a bar spanning both legs books only the entry), and the **failure modes** (a one-way
downtrend fills every bid and loses; an unfundable rung is skipped rather than overdrawn; a forced
end-of-run exit is never counted as a captured rung).

36 of them cover the **strategy cards** (`core/strategy_cards.py`). Those tests exist because a card's
frontmatter supplies numbers to a backtest, so the machine-readable half is checked against the code
rather than trusted: registry drift is asserted in **both** directions (every registered strategy has
a card, every card's `registry_key` still exists), every declared default is compared against its
constructor's actual default, `warmup_bars` and `family` against the code, and every card's presets
against `research/sweep.py` so a card documents the same experiment the sweep runs. Every buildable
card is also constructed and run through a full backtest. Prose in a card can still be wrong — no
test catches that — but a number cannot.

31 more cover the **nine strategies implemented from spec-only cards**
(`core/strategies/advanced.py`). Each test targets what that mechanism could get
*wrong* rather than that it runs: the excluded window in dual momentum, the strength
gate in ADX, and above all the **displacement trap in Ichimoku** — the cloud sitting
at the current bar was computed 26 bars ago, so reading it as current reads 26 bars of
future data. That test asserts the value used equals the cloud computed from the
truncated slice *and* differs from the full-history cloud, so the distinction is
verified rather than assumed.

63 cover the **per-bar rule readout** (`research/decide.py`), and the one that matters
asserts *engine parity*: a recording wrapper captures every `on_bar` return
`run_backtest` asks for, and the readout's replay must reproduce that index sequence and
those values exactly for all 25 strategies. The rest guard the two ways the readout can
lie — a truncated-history test that fails if the replay is ever "optimised" into a single
call on the last bar, and a constructed series where that shortcut gives the *opposite*
answer, so the first test is known to be load-bearing rather than vacuously true.

## soltui — 313 tests

Slower than the others (~70s) because the TUI tests drive real render cycles. Three
files: `test_signals.py` (signal derivation), `test_status_roster.py` (status and roster
state) and `test_tui.py` (rendering). Run them with
`python3 -m unittest discover -s soltui/tests -t .`.

soltui is read-only over the research side and places no orders, so its tests are about
display correctness, not money. The packaging paths — the py2app alias bundle and the
launchd agent — are **not** covered by any test; see `soltui/README.md` for the manual
checks that stand in for them.

## Adding tests

- Extension: `extension/test/*.test.js`, `node:test` + `node:assert/strict`. Assert behaviour and
  observable effects, not line execution.
- Backtester and research: `backtester/tests/`, `unittest`. `research/` has no test directory of
  its own; its modules are tested from there (`test_decide.py`, `test_cpcv.py`, `test_interpret.py`).
- soltui: `soltui/tests/`, `unittest`.
- A new command needs no new parity test — the registry-driven suite picks it up automatically. If it
  takes an argument that changes money, add a behavioural test for that argument.
