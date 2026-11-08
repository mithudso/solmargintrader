---
id: jlp_vs_sol_relative_value
name: JLP-vs-SOL Relative Value
kind: exposure-strategy
status: implemented
family: mean-reversion
summary: The peer-spread mechanism pointed at JLP. Code is done; the price history does not exist yet.
registry_key: null
runner: backtester.paircli
warmup_bars: 251
evaluation: null
data_required: [ohlcv, jlp-price-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params:
  peer_name: {default: JLP, type: str, desc: "peer asset symbol for the spread"}
  fit_window: {default: 250, type: int, desc: "bars per rolling OLS and ADF fit"}
  entry_z: {default: -2.0, type: float, desc: "spread z-score at or below which to enter"}
  exit_z: {default: 0.0, type: float, desc: "spread z-score at or above which to exit"}
  stop_z: {default: -3.0, type: float, desc: "spread z-score at which to stop out"}
  adf_max_p: {default: 0.05, type: float, desc: "maximum ADF p-value that permits a trade"}
  require_cointegration: {default: true, type: bool, desc: "gate entry on the ADF test"}
presets: {}
---

# JLP-vs-SOL Relative Value

> **Status `implemented`, not `measured`.** The code is written, tested and runnable —
> it is the same `core/pairs.py` mechanism that `pairs_cointegration.md` measured
> against BTC and ETH. What does not exist is JLP **price history**, and that is a
> different kind of gap from the other blocked cards: it cannot be fetched
> retroactively from anywhere this repo can reach.

## What was actually checked

| Source | JLP result |
|---|---|
| Coinbase (`JLP-USD`, the host the SOL/BTC/ETH data came from) | **Not listed** — no such product |
| Jupiter Price v3, keyless | **Spot works**: `$3.5933` with liquidity, at the mint below |
| `datapi.jup.ag` charts endpoint | **Unreachable** |

So the earlier card's claim that "Jupiter's own Price API can supply the JLP mint" was
right about *price* and wrong about *history*. That distinction is the whole gap. The
mint, from the perps page's own hydration payload, is
`27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4` (6 decimals).

## How it was unblocked, as far as it can be

`core/archive_price.py` appends one spot observation per run:

```bash
python3 -m backtester.core.archive_price --mint JLP        # one row, append-only
python3 -m backtester.core.archive_price --mint JLP --dry-run
```

It refuses a missing or non-positive price rather than writing a zero, because a zero in
a price archive is indistinguishable from a real observation later and would poison
every spread computed from the file. It also **warns while the file is too short to
backtest**: a 250-bar fit window plus a test window needs several hundred rows.

Seeded with its first observation. It cannot recover the past — schedule it and the
series accrues going forward.

## Why the pair is worth the wait
JLP is roughly 68% crypto by composition and realises about **0.42–0.53x SOL's
short-horizon volatility**, so the two are mechanically related with a reasonably stable
beta. That makes it a better cointegration candidate than two unrelated tokens, and
unlike BTC or ETH it is **specific to this venue** — the thing being hedged is the pool
the perps strategy trades against.

## Likelihood of success: low

*Basis: a-priori — never run, because there is nothing to run it on. There is no 'high'
rating in this scheme: across 311 rankable configurations measured here, 14% had a
positive out-of-sample Sharpe and 9% made money.*

The mechanism now has a measured sibling, and that sibling is the best evidence
available: against ETH, where cointegration genuinely held, it took **zero
out-of-sample trades** and its ADF gate prevented a −24.7% loss. A JLP spread would
likely behave the same way — mostly abstaining, occasionally trading, with the gate
doing most of the work.

Two structural problems specific to JLP hold it at low rather than moderate:

1. **JLP accrues fees**, so its price carries a drift component that is not a market
   view. A pure mean-reversion read would fight that drift, and the OLS intercept
   absorbs a level but not a trend.
2. **JLP holds SOL.** The hedge is partly a hedge against itself, which caps how much
   independent information the spread can contain.

## Caveats and limitations
- **No measurement exists.** Nothing on this card is a performance claim.
- Same single-asset-exposure limitation as `pairs_cointegration.md`: this is not the
  dollar-neutral trade the literature describes.
- Spot archiving samples whenever it is run, so the resulting series has whatever
  cadence the schedule gives it — not clean daily bars. `align_peer` will refuse to
  match it against daily SOL bars until the timestamps line up, which is the correct
  behaviour and an additional job before this is runnable.

## How to run, once the archive is long enough
```bash
python3 -m backtester.core.archive_price --mint JLP     # on a schedule
# then, when several hundred aligned observations exist:
python3 -m backtester.paircli --asset SOL --peer JLP --split 0.7
```
