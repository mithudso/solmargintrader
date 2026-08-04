# Handoff — 2026-08-04

## State: all merged to master, local only (no remote)

`python3 -m unittest discover -s backtester/tests -t .` → **119 OK**
`python3 -m unittest discover -s soltui/tests -t .` → **61 OK**
`python3 research/verify_numbers.py` → **exit 0**, 795 figures verified

## What exists

- `backtester/` — event-driven engine, look-ahead-guarded, 16 strategies, CPCV + PBO
- `research/` — 42-mechanism taxonomy, three ranked lists, sweeps, `verify_numbers.py`
- `soltui/` — five-tab Textual console + macOS menu-bar indicator (**dry-run only**)

## Findings that should survive

1. **PBO is the number that matters.** Calibrated: **0.500 = pure noise**, 0.000 = rank
   predicts perfectly. Singles sit at 0.43–0.46. **Pairs/triples reach 0.857/0.886** — worse
   than random. Combining signals made overfitting worse while producing MORE positive-looking
   results (96% of long triples positive). That pairing is the overfit signature.
2. **Low PBO is not automatically good.** Short triples: PBO 0.086 but only 6/61 positive — the
   in-sample winner generalises reliably as a *loser*. `cpcv_sweep.py` now detects and prints
   this automatically (`interpret()`), because it's the misreading most likely to cost money.
3. **The old 70/30 split was structurally doomed:** its in-sample window ended on bar 1311, the
   highest close in the entire series. Under CPCV, buy-and-hold ranks 1st at the medium horizon.
4. `zscore_20_-2` and `bb_reversion_20_2` are the **same mechanism** (same inequality, differing
   only in stdev ddof). Family labels are not a substitute for measuring signal correlation.
5. `obv_trend_60` is the only row worth attacking: +0.774 median Sharpe, 81% of paths positive.

## Gotchas that cost time before

- `verify_numbers.py` has a **preflight** that fails loudly on stale/partial results. If it
  exits 1 saying labels are missing, regenerate BOTH sweeps — do not assume the docs are wrong.
- An **unanchored** `results/` gitignore pattern matches `research/results/` at any depth. It is
  `/results/` now. `research/results/` is deliberately **tracked** — it is the evidence.
- Never grep verifier output for `"MATCH"`: it matches **"MISMATCHES"**. Use the exit code.
- Textual 8.x: `Static.content`, not `.renderable`. `Pilot.click()` raises OutOfBounds on
  off-screen widgets — pass a large `size=` to `run_test()`.
- `rumps` is macOS-only and not installed globally; `soltui/app.py` imports it lazily.

## Safety posture (do not regress)

`soltui/` has **no order path** — no network capability, no keys/signing, no venue client.
`config.MODES` is `('dry-run',)`; `armed` needs a second explicit acknowledgement so an old
config cannot arm a future build. `paper.py` is a **replay** of one engine run, deliberately not
a second fill path. Live execution would route through `extension/src/core/commands.js` and its
risk rails as separate, explicit work.

## Next, by value

1. Parameter-perturbation stability on every ranked row — start with `obv_trend_60`.
2. Measure pairwise signal correlation instead of trusting family labels.
3. Fetch a **peer universe** — unlocks cross-sectional momentum and cointegration.
4. Deflated Sharpe accounting for the ~1,300 configurations already evaluated.
5. `/cdo` outstanding on the newer modules (indicators, signals, composite, cpcv, soltui/*).
