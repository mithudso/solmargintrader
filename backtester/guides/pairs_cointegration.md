---
id: pairs_cointegration
name: Pairs Trading / Cointegration vs BTC or ETH
kind: exposure-strategy
status: measured
family: mean-reversion
summary: Trade a spread whose stationarity is actually tested. The rigorous version of zscore.
registry_key: null
runner: backtester.paircli
warmup_bars: 251
evaluation: single-split-70-30
data_required: [ohlcv, peer-ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  peer_name: {default: BTC, type: str, desc: "peer asset symbol for the spread"}
  fit_window: {default: 250, type: int, desc: "bars per rolling OLS and ADF fit"}
  entry_z: {default: -2.0, type: float, desc: "spread z-score at or below which to enter"}
  exit_z: {default: 0.0, type: float, desc: "spread z-score at or above which to exit"}
  stop_z: {default: -3.0, type: float, desc: "spread z-score at which to stop out"}
  adf_max_p: {default: 0.05, type: float, desc: "maximum ADF p-value that permits a trade"}
  require_cointegration: {default: true, type: bool, desc: "gate entry on the ADF test"}
presets: {}
---

# Pairs Trading / Cointegration vs BTC or ETH

> **Unblocked and measured.** The data gap that made this spec-only was "no peer price
> series". Coinbase serves BTC-USD and ETH-USD keyless through the fetcher already in
> this repo, so both were fetched (1,875 daily bars each, exactly aligned with SOL) and
> the mechanism was measured.

## What it is
Fit `SOL = beta * peer + c` over a trailing window, ADF-test the residual, and trade the
residual's z-score **only while that test says it is plausibly stationary**.

## Equation
```
Engle-Granger two-step, refitted every bar on trailing data only:
  1. regress SOL = beta*peer + c            (closed-form OLS)
  2. ADF-test the residual for a unit root
if p > adf_max_p:  take NO position          # the relation is not established
spread_z = zscore(residual, fit_window)
enter if spread_z <= entry_z ; stop if <= stop_z ; exit if >= exit_z
```

## Why this is not `zscore` with extra steps
`zscore.md` applies a stationarity-dependent method to raw price, which is **not
stationary** — a known theoretical error its measured result does not repair. Here the
traded object is a residual constructed to be stationary, and the assumption is
*tested*. `require_cointegration` makes the strategy refuse to trade until the test
passes. That refusal turns out to be the whole story.

## Implementation
`core/cointegration.py` (ADF + Engle-Granger, MacKinnon critical values, no
`statsmodels`) and `core/pairs.py`. Run through `backtester.paircli` — **not** the
strategy registry, because it needs two series and a registered strategy that silently
does nothing when its peer is missing would be a footgun.

## Measured on SOL

| Peer | Full-sample beta | Full-sample ADF | Cointegrated at 5% | OOS return | OOS trades |
|---|---|---|---|---|---|
| BTC | 0.0018 | −2.648 (p≈0.087) | **No** | 0.00% | **0** |
| ETH | 0.0644 | −3.127 (p≈0.032) | **Yes** | 0.00% | **0** |

The rolling gate screened out 1,121 of 1,624 windows against BTC and 1,224 against ETH.

**The result that matters is the contrast.** Disabling the gate on the ETH pair
(`--no-cointegration-gate`) produces **2 out-of-sample trades and −24.70%**. With the
gate on: no trades, no loss. The ADF screen is not decoration — on this data it is the
difference between losing a quarter of the account and standing still.

The figures come from a **single 70/30 walk-forward split**, whose in-sample window
ends within one bar of the highest close in the series. `research/RANKED_LISTS.md`
documents why that makes it hostile, and `core/cpcv.py` is now the repo's primary
evaluation for exactly that reason. Read these as evidence about **one regime
transition**.

## Likelihood of success: low

*Basis: measured-oos. There is no 'high' rating in this scheme — across 311 rankable
configurations, 14% had a positive out-of-sample Sharpe and 9% made money.*

Two findings pull in opposite directions, and neither supports more than low.

**In favour:** the rigour works. SOL and ETH *are* cointegrated on the full sample at
5%, which is a real structural relationship rather than a fitted one, and the gate
demonstrably prevented a −24.7% loss. Compare `zscore.md`, which had no such test,
bought dips through the same window, and produced the previously top-ranked medium row
that `RANKED_LISTS.md` later found consistent with noise.

**Against:** it made no money either, because it took **zero out-of-sample trades**. A
mechanism that abstains has demonstrated a filter, not an edge. And the honest reading
of "cointegrated with ETH" is unflattering — SOL and ETH are both high-beta crypto, so a
stationary spread between them may be measuring the same market twice rather than
finding a relative-value opportunity.

## Caveats and limitations
- **This is not the dollar-neutral pairs trade the literature describes.** Exposure is
  single-asset long SOL; the peer is an input to the signal, not a shorted leg. A real
  pairs trade needs short exposure this harness cannot express. That gap is the largest
  single reason to discount the numbers above.
- Engle-Granger is **order-dependent**: regressing SOL on ETH and ETH on SOL can
  disagree. Johansen is preferred for three or more series.
- `adf_pvalue` interpolates a lookup table. Treat 0.04 and 0.06 as the same answer.
- The practitioner rule of requiring cointegration across 3-, 6- and 12-month windows is
  **not** implemented; a single window is checked.
- Scanning many windows for cointegration will find some by chance — a 5% test has a 5%
  false-positive rate, and `test_pairs.py` asserts that rate rather than pretending it
  is zero.

## How to run
```bash
python3 -m backtester.core.fetch --asset BTC --interval 1d --start 2021-06-17
python3 -m backtester.paircli --asset SOL --peer BTC --interval 1d --split 0.7
python3 -m backtester.paircli --asset SOL --peer ETH --split 0.7 --no-cointegration-gate
```
