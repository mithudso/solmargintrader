# Frozen meta-analysis paper cohort

This service compares the selected hourly ZEC Bollinger breakout with passive
ZEC, initially equal-weight BTC/ETH, and cash. Every account starts with its own
virtual USD10,000. They are independent comparisons, not multiple claims on one
funded portfolio. No code in this module signs, submits, funds or routes an order.

The default primary scenario charges 90 bps commission and 2 bps execution drag per
side. The 50 bps maker scenario is a cost sensitivity: it does not establish limit
order execution, queue priority or nonfills. Coinbase One does not establish a
waiver on this API path. Current accounts expose marked equity and an estimated
net-liquidation value that also charges the modeled exit cost on open inventory.
That estimate is not a quote or an executed exit.

## Start a new cohort

Use a dedicated installed environment and a fresh home. These commands prepare
and explicitly activate paper evidence; the first eligible open is in the future.
Do not point them at an existing Volty or ZEC ensemble home.

```sh
python -I -m ecosystem.meta_forward --home /absolute/new/cohort init --passive-zec-weight 0.25 --seed-not-before 2026-11-08T22:00:00Z
python -I -m ecosystem.meta_forward --home /absolute/new/cohort activate
python -I -m ecosystem.meta_forward --home /absolute/new/cohort run
```

The optional weight adds a fixed ZEC-passive/cash comparator in each cost
scenario. Choose its weight before activation from the declared training/risk
procedure; it never adapts to prospective results. A supplied frozen JSON
configuration can declare other fixed sleeve weights, but cannot be combined
with the weight override. No allocation can exceed 100% of account capital.

Read status without modifying the store:

```sh
python -I -m ecosystem.meta_forward --home /absolute/new/cohort status
```

For a persistent deployment, launch the `run` command through a uniquely named
launchd job. Use a stable installed Python and home rather than a temporary
worktree. The runner holds an exclusive home lock; a second writer is refused.
The existing specialized forward services and Oracle publication pointers have
separate owners and are not changed by this cohort.

## Timing and recovery

The public source is native Coinbase Exchange USD 1h OHLCV for BTC, ETH and ZEC.
The actual indicator needs 41 contiguous closed bars for the frozen 40-bar
breakout. The optional seed boundary filters earlier observations before OHLC
validation or any feature computation. Its exact boundary and retained source
bounds are frozen in metadata. Warmup price movement never
earns account P&L. Preparation creates no orders or decisions. Activation primes
the exact canonical strategy, commits a target and its completed-bar marks, then
records a separate confirmation after the first commit returns. The eligible
candle opens two nominal bars after the source candle opened, giving a real
future boundary after the source candle has closed.

The service later observes that eligible candle after it closes and applies the
already confirmed target to its reported open through the canonical spot
accounting engine. This is **reference paper accounting**, not evidence that an
executable quote was observed at the historical open. Decision and trade records
carry this distinction. Stored book/cursor/fees and candle/snapshot changes share
one SQLite transaction with FULL synchronization.

A crash between decision commit and confirmation leaves that decision
ineligible permanently. A delayed commit cannot backdate its confirmation.
Duplicate polls do not create duplicate trades. A source revision, implementation
change, gap or missed decision window blocks the whole shared-calendar cohort.
It never fills missed intervals on restart. A transient network failure may
retry only while the same decision window is still open. Preserve blocked
cohorts as evidence; a replacement requires a new home and fresh activation.

Config bytes, SHA256 and all canonical numerical source hashes are immutable.
Changing an installed numerical implementation blocks its existing cohort.
Future profitability needs elapsed observations; successful startup proves only
the deployed collection and accounting path.

## Verification

```sh
python -m unittest ecosystem.tests.test_meta_forward -v
ruff check ecosystem/meta_forward.py ecosystem/tests/test_meta_forward.py
```

Tests cover future-only activation, historical warmup, actual fees, exit-cost
estimates, fixed passive weights, duplicates/restarts, crash and real delayed
SQLite commit/lock boundaries, source revisions, missed windows and writer locks.

## Deployed cohort and frozen review

The 2026-11-11 cohort uses the installed environment
`/Users/mitch/.venvs/meta-forward-20261111`, home
`/Users/mitch/.local/share/solmargintrader/meta-forward-20261111`, and job
`com.solmargintrader.meta-forward.1391`. Its initial passive ZEC budget is
0.4793342110254035, calibrated from the historical training volatility ratio.
Fixed units and idle cash subsequently drift; the book does not maintain
matched volatility.

`docs/META-FORWARD-PROTOCOL.json` freezes the ten-book family, 30-day engineering
check, 180-day descriptive review, 365-day terminal review, paired dependence
analysis and promotion requirements. The dated risk amendment records the
owner's approximate 30% drawdown tolerance without changing the accounts.
Neither the schedule nor a statistically favorable result automatically deploys
investment capital.
