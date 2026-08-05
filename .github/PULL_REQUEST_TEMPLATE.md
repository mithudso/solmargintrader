## What changed

<!-- One or two sentences. What does this do that the repo could not do before? -->

## Which component

- [ ] `backtester/` — simulation only. A dishonest backtest is the failure mode.
- [ ] `research/` — analysis. Overstating a result is the failure mode.
- [ ] `extension/` — **can place real orders.** Treat as production software.
- [ ] `soltui/` — read-only display.
- [ ] Repo-level (docs, CI, tooling).

## Verification

Paste the actual output, not a claim that it passed.

```
python3 -m unittest discover -s backtester/tests -t .
python3 -m unittest discover -s soltui/tests -t .
cd extension && npm test
node tools/dryrun.js --ticks 8 --osc 6 --offline 100
python3 scripts/check_docs.py
```

- [ ] The suites above pass, and I have pasted the counts.
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
