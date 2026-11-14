## What changed

<!-- One or two sentences. What does this do that the repo could not do before? -->

## Which component

- [ ] `backtester/` — simulation only. A dishonest backtest is the failure mode.
- [ ] `research/` — analysis. Overstating a result is the failure mode.
- [ ] `extension/` — **can place real orders.** Treat as production software.
- [ ] `soltui/` — research console; separately armed manual Coinbase spot path.
- [ ] `oracle/` — shadow forecasts; separately enabled live-capable TradingView worker.
- [ ] `botmanager/` — paper accounts, lifecycle and evidence.
- [ ] `ecosystem/` — paper coordination and local control room.
- [ ] `executor/` — guarded Solana spot execution, own pytest/Ruff gates.
- [ ] `mongo/` — derived local datastore.
- [ ] `liquidity/` — retained Base signing code; archived daemon/scout stay disabled, own pytest/Ruff gates.
- [ ] `website/` — hosted wallet accounts, billing, research and inactive paper definitions; separate Node/Python/export gates.
- [ ] Repo-level (docs, CI, tooling).

## Why

<!-- Which concrete problem does this fix? -->

## Verification

Paste the actual output, not a claim that it passed.

```
python3 -m unittest discover -s backtester/tests -t .
python3 -m unittest discover -s soltui/tests -t .  # optional full suite; use focused checks where applicable
python3 -m unittest discover -s oracle/tests -t .
python3 -m unittest discover -s ecosystem/tests -t .
cd extension && npm test
node tools/dryrun.js --ticks 8 --osc 6 --offline 100
python3 scripts/check_docs.py
```

- [ ] Applicable suites pass; actual commands, counts, exit codes and skipped gates are recorded.
- [ ] The oscillating dry run still closes a round trip **positive** (extension changes).

## If this touches signal generation or fill timing

- [ ] There is a test that would catch a one-bar lookahead leak.

## If this touches the extension

- [ ] `DEFAULT_CONFIG.mode` is still `dry-run` and a fresh install is still disarmed.
- [ ] Every new rail is enforced in `src/core/risk.js` and **fails closed** on missing or NaN state.
- [ ] No price, quantity or fee is guessed, defaulted, or zero-filled on the way to an order.
- [ ] No secret material reaches a log, `chrome.storage.sync`, the DOM, or a response body.
- [ ] Any new action lives in `src/core/commands.js` (all three surfaces, one registry).

## If this changes the grid economics

- [ ] The matching change is in **both** `extension/src/core/grid.js` and `backtester/core/gridsim.py`.

## Docs

- [ ] `scripts/check_docs.py` passes, so no test count or index entry is stale.
- [ ] A new strategy ships its `backtester/strategy_cards/<id>.md` in this same PR.

## Risk and rollback

<!-- State changed behavior, material residual risks, and the exact revert or recovery step. -->
