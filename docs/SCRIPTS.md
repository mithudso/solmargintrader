# Scripts

Every runnable entry point in this repo: what it is for, when to reach for it, **when
not to**, its options, a real invocation, and the output you should expect.

`docs/COMPONENTS.md` is the shape of the code; `docs/FILES.md` is the exhaustive file
list. This page is the operator's manual — the commands you actually type.

Every example below was executed against this repo. Where output is shown it is
real, trimmed for length, never illustrative.

## The one rule

**A number produced by any script here is not evidence until something other than
the ranking that produced it has confirmed it.** PBO is measured at **0.700** at the
daily horizons against a 0.500 pure-noise line, which means the in-sample
leaderboard is worse than a coin flip at predicting out-of-sample rank. Read
"Reading the numbers correctly" at the bottom before quoting anything.

Three commands are gates rather than experiments. Run them before trusting the rest:

```bash
python3 research/verify_numbers.py                   # docs match their result files
python3 index/build.py --check                       # the index matches the tree
python3 research/cross_asset_cpcv.py --self-test     # the harness reproduces the reference
```

## Quick reference

| Command | For | Network |
|---|---|---|
| `python3 -m backtester.cli` | one backtest, many strategies, full report | no |
| `python3 -m backtester.gridcli` | resting-ladder grid backtest | no |
| `python3 -m backtester.paircli` | cointegration / pairs backtest | no |
| `python3 -m backtester.core.fetch` | fetch one asset's bars into `data/` | **yes** |
| `python3 -m backtester.core.universe` | fetch many assets, refuse a partial set | **yes** |
| `python3 -m backtester.core.ticks` | fetch trade ticks into `data/ticks/` | **yes** |
| `python3 research/candle_gap_audit.py` | classify and repair candle gaps using ticks | **yes** |
| `./research/run_backfill.sh` | long, resumable, low-priority tick backfill + audit | **yes** |
| `python3 -m backtester.core.fetch_minutes` | fetch 1-minute history (hours; resumable) | **yes** |
| `python3 research/minute_sweep.py` | preliminary 1-minute strategy sweep (no CPCV) | no |
| `python3 research/sweep.py` | the horizon parameter tables; single-split walk-forward | no |
| `python3 research/cpcv_sweep.py` | **primary evaluation** — CPCV + PBO | no |
| `python3 research/cross_asset_cpcv.py` | does a result transfer to another coin | no |
| `python3 research/perturb.py` | ±10% parameter robustness | no |
| `python3 research/geometry.py` | is the leaderboard an artifact of block count | no |
| `python3 research/decide.py` | per-bar readout of what each rule decided | no |
| `python3 research/dso_audit.py` | deflated-Sharpe / evidence-floor audit of results | no |
| `python3 research/verify_numbers.py` | **gate:** every quoted figure vs its CSV | no |
| `python3 research/turnover_table.py` | the one comparable turnover table | no |
| `python3 research/leverage_economics.py` | what leverage costs before it earns; the viable region | no |
| `python3 research/ratio_rotation.py` | multi-asset numeraire-switching rotation; chained-vs-direct routing | no |
| `python3 research/short_horizon_economics.py` | the same cost question below one hour, where turnover dominates | no |
| `python3 index/build.py` | build the four repo indexes | localhost only |
| `python3 index/search.py` | search the repo three ways | localhost only |
| `python3 scripts/check_docs.py` | **gate:** doc drift, test counts, dead index paths | no |
| `node --test` (in `extension/`) | extension unit + parity tests | no |
| `node tools/dryrun.js` | headless grid dry run, no orders | optional |

---

## Backtesting

### `python3 -m backtester.cli` — one backtest, full report

**Purpose.** Run one or every registered strategy over one series and print a
comparison table: return, CAGR, Sharpe, Sortino, max drawdown, Calmar, win rate,
trade count, exposure fraction, fees, borrow fees, liquidations, final equity. Then
print the same table at zero cost, so cost drag is visible rather than assumed.

**When to use it.** You want to see how a strategy behaves on a series, with a
report a human reads. It is the fastest way to sanity-check a mechanism.

**When *not* to use it.** Never as evidence for a claim. It is a **single path** over
one window — the thing CPCV exists to replace. If you are about to write a number
from this into a document, you want `cpcv_sweep.py` instead.

**Options** (the ones that change results, not just presentation):

| Flag | Default | Note |
|---|---|---|
| `--asset` / `--interval` / `--start` / `--end` | SOL, 1d | which series |
| `--strategy` | all | a registry name, or `all` |
| `--mode {spot,perp}` · `--leverage` · `--allow-short` | spot, 1 | exposure model |
| `--fee-bps` · `--slippage-bps` | 6 · 2 | **do not zero these to make a result look better** |
| `--fill-delay` | 1 | 1 is the conservative choice; 0 fills on the signal bar |
| `--split` | 0.7 | in-sample fraction for the walk-forward legs |
| `--borrow-bps-long/short` · `--utilization` | — | financing for perp mode |
| `--synthetic N` | — | N bars of generated data; no `data/` needed |
| `--data` · `--allow-gaps` · `--seed` · `--out` · `--no-charts` | — | plumbing |

**Example and real output:**

```bash
python3 -m backtester.cli --synthetic 400 --strategy ma_crossover --no-charts
```

```
BACKTEST REPORT -- SOL 1d
Range          : 2021-01-01 .. 2021-10-17  (290 bars)
Costs          : fee 6bps, slippage 2bps
Fill           : signal at bar t -> fill at t+1 open
Data           : synthetic:seed=42,n=400 (sha256:94aa291d3c296e6d)

          strategy  total return  sharpe  max drawdown  trade count  final equity
      buy_and_hold         9.76%   0.547       -41.53%            1     10,975.77
ma_crossover_20_50       -18.81%  -0.241       -35.04%            4      8,119.20
```

Note what the header gives you: the exact cost model, the fill rule, and a **hash of
the input series**. A report without those three is not reproducible.

### `python3 -m backtester.gridcli` — resting-ladder grid

**Purpose.** Backtest the ladder the extension actually trades, which is *not* a
`Strategy` in the engine's sense: it rests limit orders rather than mapping history
to one target exposure.

**When to use it.** Sizing rungs, spacing, deadband — anything about the live grid.

**When *not* to use it.** For directional-signal questions. A grid has no view; it
monetises oscillation. And note the documented failure mode: a resting grid turns a
sustained trend into a maximum-size losing position.

**Required:** `--lower` and `--upper`. Then `--rungs`, `--notional-per-rung`,
`--spacing {arith,geom}`, `--deadband-bps`, `--min-order-usd`,
`--carry-bps-per-hour`, plus the usual data and cost flags.

```bash
python3 -m backtester.gridcli --lower 60 --upper 90 --rungs 7 \
  --notional-per-rung 12 --synthetic 400
```

### `python3 -m backtester.paircli` — peer relative value

**Purpose.** Two-leg peer-relative-value backtest with a hedge ratio (its own
docstring calls it a "peer-relative-value backtest entry point").

**When *not* to use it.** On assets whose histories do not overlap cleanly. Check
`docs/known-issues.md` for the XRP gap first — a concatenated series hides a
two-and-a-half-year join, and every statistic computed across it is wrong.

---

## Data

Both of these touch the network. **Nothing under `backtester/core/` that the engine
uses at runtime does** — fetching is a separate, explicit step, and `data/` is
gitignored because it is a regenerable cache.

### `python3 -m backtester.core.fetch` — one asset

```bash
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01
python3 -m backtester.core.fetch --asset SOL --interval 1h --start 2025-08-01 --allow-gaps
```

Options: `--asset`, `--quote`, `--start`, `--interval`, `--out`.

**When *not* to use it.** To "fix" a gap. It refuses gappy series on purpose;
`--allow-gaps` is a disclosure, not a repair. A forward-filled gap flatters every
volatility and mean-reversion statistic computed afterwards.

### `python3 -m backtester.core.ticks` — trade ticks, not bars

**Purpose.** Fetch individual trades from `/products/<id>/trades`, below the 1m
floor of the candle endpoint, and optionally aggregate them into bars.

```bash
python3 -m backtester.core.ticks --asset SOL --start 2026-08-05T12:00:00Z \
    --end 2026-08-05T12:05:00Z --bars 1m
```

Options: `--asset`, `--quote`, `--start`, `--end`, `--max-trades`,
`--allow-truncated`, `--out`, `--bars`, `--bars-out`.

Output lands in `data/ticks/`, deliberately outside the `data/<ASSET>_<interval>.csv`
namespace `CsvLoader` reads — a tick frame is not a bar frame and a backtest that
loaded one as the other would be a confident wrong number.

**When *not* to use it.** For a long window. The endpoint takes no time range at
all (`start`/`end` are silently ignored, which is why the window is located by
bisecting `trade_id`), and a month of SOL-USD is millions of trades. `--max-trades`
defaults to 500,000; a window cut short is **refused** rather than written, because
`to_csv` drops the in-frame truncation marker and the file name would still claim
the full window. `--allow-truncated` is a disclosure, not a repair.

**Why this exists.** It is the only source below 1m, and the only way to check the
candle endpoint against raw prints. It found that the candle endpoint drops minutes
that traded — see **Candle data is not trustworthy near a gap** below.

### `python3 research/candle_gap_audit.py` — why a candle is missing, and repair

**Purpose.** A missing 1m candle has two causes that look identical in the file and
mean opposite things: the minute genuinely had no trades, or the minute traded and
the endpoint dropped it. Only the trades endpoint can tell them apart. This script
asks it, and can rebuild the affected bars.

```bash
# classify a sample of gap runs, no writes
python3 research/candle_gap_audit.py --assets SOL,BTC,ETH --sample 5

# rebuild every gap window from ticks into data/repaired/
python3 research/candle_gap_audit.py --assets SOL --repair --report research/CANDLE-GAP-AUDIT.md
```

Options: `--assets`, `--quote`, `--interval`, `--suffix`, `--data-dir`, `--sample`,
`--seed`, `--repair`, `--max-runs`, `--out-dir`, `--report`.

**Repaired series are mixed-provenance and say so.** Output goes to `data/repaired/`,
never over the candle cache: the file is candle bars everywhere except the repaired
windows, which are tick-derived. A capped run (`--max-runs`) is written as
`..._repaired_PARTIAL.csv` — an asset with thousands of quiet minutes cannot be
repaired in one pass, because every gap run costs a tick fetch.

`data/` is gitignored, so repaired series are **not in git** and are regenerable by
re-running the command above. Point `--out-dir` at the repo you actually want them in
when running from a worktree.

### Candle data is not trustworthy near a gap

Established 2026-08-06 by `candle_gap_audit.py` against the trades endpoint, over
2026-07-06 .. 2026-08-06. **This is a data-integrity finding, not a tooling note.**

1. **A missing candle is usually not a quiet minute.** Across **31 gap runs sampled
   over five assets, 26 (84%) had trades the endpoint dropped.** Per asset:

   | asset | gap runs | missing min | sampled | dropped | est. dropped minutes (95% CI) |
   |---|---:|---:|---:|---:|---|
   | SOL | 5 | 6 | 5 of 5 | 4 | 4 (2–5) |
   | BTC | 1 | 1 | 1 of 1 | 1 | 1 (0–1) |
   | ETH | 1 | 2 | 1 of 1 | 1 | 2 (0–2) |
   | DOGE | 3,739 | 4,260 | 12 of 3,739 | **11** | **3,905 (2,752–4,196)** |
   | ZEC | 987 | 1,062 | 12 of 987 | 9 | 796 (496–967) |

   DOGE's 9.5% missing month is therefore mostly **dropped trading, not illiquidity** —
   the reading a single spot-check wrongly suggested. DOGE and ZEC figures are
   sample-based estimates (Wilson intervals), not censuses.

   The same minutes — 2026-07-06 01:38 and 01:39 — are missing for **SOL, BTC, ETH,
   DOGE and ZEC**, so that one is an exchange-side event, not a per-series artefact.
   BTC lost 390 trades in one minute; ETH lost 428 across two.

2. **The loss is permanent, not a transient serving hiccup.** Re-requesting the
   affected ranges narrowly, weeks later, still omits 07-26 07:28 and 07-31 23:29 and
   still reports 65.3978 for 07:27. **Refetching does not repair it** — which is why
   the tick path is the only remedy.

3. **Bars adjacent to a gap can be wrong too, in both directions.** They are
   *present*, so nothing flags them:

   | asset | minute | field | candle | ticks |
   |---|---|---|---|---|
   | DOGE | 07-06 01:37 | volume | 112.9 | **11,630.4** |
   | BTC | 07-06 01:37 | volume | 0.719 | **9.171** |
   | BTC | 07-06 01:39 | volume | 0.046 | **1.221** |
   | SOL | 07-06 01:37 | volume | 120.4 | **204.2** |
   | SOL | 07-26 07:27 | volume | 65.398 | **60.042** |

   In the two isolated single-minute drops the neighbour is *too big* by exactly the
   dropped minute's volume (07-26 07:27 by 5.3562; 07-31 23:28 by 0.2402), which looks
   like the dropped minute being folded into its neighbour. That tidy explanation does
   **not** extend to the 01:38–01:39 outage, where the neighbouring candles are too
   *small* instead — BTC 01:37 by 12×. Two exact matches are a pattern worth knowing;
   they are not a validated mechanism, and the outage neighbourhood behaves differently.

   **Not every diff is candle error.** Some are boundary attribution: at SOL 07-31,
   23:30 is −0.135896 and 23:31 is +0.135896, exactly zero-sum. That is one trade on
   the minute boundary, assigned to different sides by the two surfaces. No volume is
   lost, and the repair rewrites those bars on a convention that has not been
   validated — treat sub-0.01 price shifts and zero-sum volume pairs as attribution
   noise, not recovered data.

4. **The damage propagates to coarser bars, including prices.** The 5m bar at
   2026-07-06 01:35 is short **254.782 SOL (9.6% of real volume)** and reports a low
   of **81.91 against a true 81.86**. A wrong low is what stop-loss and liquidation
   logic reads, which makes this a correctness problem for any backtest that models
   intrabar stops, not merely a volume-accuracy one.

5. **The corruption is not confined to gaps.** A full tick reconstruction of
   2026-08-04 — a day with **zero gaps** in the SOL 1m cache — disagrees with the
   candle file on **133 of 1,440 minutes (9.2%)** by volume, plus 2.8% of opens,
   3.1% of closes, 1.7% of highs and 1.4% of lows. 100 of those 133 are exact
   adjacent-pair reassignments (volume mis-binned into the neighbouring minute), but
   the day's total volume still differs by 932.4 SOL, so it is not purely a binning
   convention. Two independent tick paths — the streaming backfill and
   `fetch_trades` — agree with each other exactly and disagree with the candle, and
   there are no trades near the affected boundaries, so this is not rounding.

**What to do about it.** Treat a gap as *suspected data loss* until classified —
never assume a quiet minute — and do not treat a gapless window as clean either.
Before trusting a result that depends on volume or on intrabar extremes, rebuild the
range from ticks (`research/tick_backfill.py`) and compare. Small spot checks will
mislead you here: many windows match bit-exactly, and roughly one minute in eleven
does not.

Full evidence, per asset, with the sampled gap runs: **`research/CANDLE-GAP-AUDIT.md`**.

### `research/run_backfill.sh` — the long, polite version

**Purpose.** `candle_gap_audit.py` pays a ~29-request bisection to locate each gap,
which is fine for five gaps and absurd for DOGE's 3,739 (~24,000 requests, mostly
spent finding windows rather than reading them). `research/tick_backfill.py` walks
the window **once**, backward, at `total_trades / 1000` requests, and classifies
every gap instead of a sample — while producing an authoritative bar series that
also exposes the errors in bars that are *present*.

```bash
./research/run_backfill.sh            # start or resume, detached
./research/run_backfill.sh --status   # progress and checkpoints
./research/run_backfill.sh --tail     # follow the log
./research/run_backfill.sh --stop     # checkpoint and stop cleanly
```

Env: `BACKFILL_ASSETS`, `BACKFILL_START`, `BACKFILL_END`, `BACKFILL_PAUSE`,
`BACKFILL_HOME` (**set this to the main checkout when running from a worktree**, or
hours of output are deleted with the worktree).

**"Polite" means three things, only one of which is the scheduler.** `nice -n 19`
yields CPU; macOS `taskpolicy -b` also throttles disk I/O and parks the job on
efficiency cores, which `nice` alone does not do; and the Python side rate-limits
itself, because the resource most likely to disrupt other work is the shared public
API quota, which no scheduler priority can protect.

**It is interruptible without loss.** State is checkpointed every 25 pages via an
atomic write, `--stop` sends SIGTERM which is trapped to checkpoint after the
current page, and a resumed run is verified to produce byte-identical results to an
uninterrupted one. A run that was interrupted **refuses to write** its bar series,
so a partial series can never be mistaken for a complete one.

### `python3 -m backtester.core.universe` — many assets

**Purpose.** Fetch a whole universe and **refuse a partial one by default**. Coinbase
does not list TRX or RAIN, so an honest "top 10" fetch is an 8-of-10 fetch, and the
dangerous outcome is not an error — it is eight files that look like a complete set.

**When to use it.** Any cross-sectional study. `--plan-only` first, always.

```bash
python3 -m backtester.core.universe --assets SOL,DOGE,ZEC --plan-only
python3 -m backtester.core.universe --assets SOL,DOGE,ZEC
```

Options: `--assets`, `--quote`, `--start`, `--end`, `--interval`, `--out-dir`,
`--refetch`, `--allow-gaps`, `--plan-only`, `--allow-partial`.

**Watch for silent truncation.** DOGE-USD begins 2021-06-03 on Coinbase, so an
earlier `--start` is quietly truncated rather than refused. A short series looks
exactly like a long one.

---

## Research and evaluation

### `python3 research/sweep.py` — the parameter tables

**Purpose.** Owns `HORIZONS`: per-horizon data file, interval, gap policy and the
parameter set for all 25 strategies. Also runs the single-split walk-forward that
CPCV superseded, retained because the disagreement between the two methods is
itself the finding.

**When *not* to use it.** As your evaluation. Its own documentation explains why the
single 70/30 split could not answer the question: the in-sample window ends on the
**highest close in the series** (bar 1311 of 1875), so any long-biased rule was
structurally required to look excellent in-sample and terrible out.

**Every other driver imports `HORIZONS` from here.** Editing a parameter moves every
downstream number in the repo.

### `python3 research/cpcv_sweep.py` — primary evaluation

**Purpose.** Combinatorial purged cross-validation over singles, pairs and triples,
then PBO across the configuration set. Prints its own legend so the numbers cannot
travel without their meaning.

**When to use it.** Any time you want a defensible number.

**When *not* to use it.** To pick a winner. It computes PBO precisely so you can see
that picking a winner does not work here.

| Flag | Default | Note |
|---|---|---|
| `--horizon {short,medium,long}` | all | short is hourly by construction |
| `--groups` | 8 | CPCV blocks. C(8,2) = 28 paths **nominally** |
| `--k` | 2 | blocks per test path |
| `--stage {singles,pairs,triples}` | all | |
| `--quiet` | off | suppress the legend — only for scripting |

```bash
python3 research/cpcv_sweep.py --horizon medium --groups 8 --k 2 --stage singles
```

**Expect fewer paths than 28.** Warm-up makes 1–2 blocks unusable for almost every
configuration: of 1,287 evaluated, **3 reached 28 paths** (all `buy_and_hold`, the
only zero-warm-up strategy), 1,094 ran on 21 and 190 on 15.

### `python3 research/cross_asset_cpcv.py` — does it transfer?

**Purpose.** Run the registered set on another coin with the SOL-tuned parameters
**deliberately not refitted**, so the measurement is transfer rather than fit.

**When to use it.** Before believing any SOL result generalises.

**When *not* to use it.** To find parameters that fit DOGE. Refitting answers "can
this be made to fit", which at PBO 0.700 the search cannot answer honestly.

Two gates, and they run before any new row is written:

```bash
python3 research/cross_asset_cpcv.py --self-test               # reproduces the BTC/ETH reference
python3 research/cross_asset_cpcv.py --assets SOL,DOGE,ZEC     # 25 singles, medium horizon
python3 research/cross_asset_cpcv.py --top5 --assets DOGE,ZEC  # the five, SOL as control
```

```
SELF-TEST PASSED: 50 rows reproduced, max abs diff 4.984e-07
CONTROL PASSED: SOL reproduces its published medians to max abs delta 0.0004
```

Options: `--assets`, `--horizon`, `--groups`, `--k`, `--self-test`, `--top5`,
`--no-control`, `--skip-self-test`, `--out`.

`--out` takes a bare filename inside `research/results/` and refuses both the
reference file and any path escaping that directory. At a geometry other than 8/k=2
the control declines to run rather than reporting a divergence it cannot attribute.

### `python3 research/perturb.py` — robustness

**Purpose.** The second independent axis: nudge each parameter ±10% and re-run CPCV.
A point that collapses under a small nudge was fitted to noise, whatever its Sharpe.

**When to use it.** On anything you are tempted to believe.

Options: `--horizon`, `--single NAME`, `--pair A B`, `--triple A B C`,
`--all-singles`, `--mode {all,any,vote,mean}`, `--pct` (default 10),
`--groups`, `--k`, `--no-geometry`, `--out`.

```bash
python3 research/perturb.py --horizon long --all-singles
```

Read `ratio_to_iqr` — max |Δ median| over the path IQR — and `sign_flips`. Compare
like with like: singles' median ratio is **0.171** at the long horizon against
**0.44** for the top pairs, i.e. combining raises parameter sensitivity ~2.6×.
Against the *pooled* singles median of 0.208 the multiple is 2.1×; quoting 0.21
alongside "2.6×" mixes two populations.

### `python3 research/geometry.py` — is it the block count?

**Purpose.** Sweep the CPCV block count and see how much the leaderboard moves.

**Why it matters.** The largest single sensitivity found in the whole study was the
**evaluation geometry, not any strategy parameter**: 8 blocks to 9 moved the best
pair's median Sharpe by −0.441, more than the worst parameter nudge (−0.392).

Options: `--horizon`, `--blocks LO HI`, `--k`.

### `python3 research/decide.py` — what did the rule decide, bar by bar?

**Purpose.** Per-bar readout of each strategy's signal, indicator values and target
exposure, with the guarantee that the targets are the numbers the engine would have
acted on.

**When to use it.** Debugging a mechanism, or answering "why was it flat there".

Options include `--asset`, `--interval`, `--data`, `--start`, `--end`,
`--strategy NAME` (repeatable), `--mode`, `--allow-short`, `--tolerance`,
`--fill-delay`, `--allow-gaps`, `--json`.

### `python3 research/dso_audit.py` — evidence-floor and deflation audit

**Purpose.** Audit result files for configurations that should not be ranked: below
the trade floor, or leaders whose Sharpe does not survive a deflation haircut for
the number of trials.

Options: `--floor` (minimum trades to count as evidence), `--swing`, `--glob`,
`--bars`, `--groups`, `--k`, `--top`.

**Why the floor matters concretely.** `cpcv_evaluate` marks a configuration
`insufficient` below `min_total_trades`, prints it **DROPPED**, and still returns a
full path count — so a filter on `n_paths > 0` counts rows the engine just refused.
BTC's *top-ranked* strategy is one of them: `ou_reversion` medians **+1.657 on six
trades**.

### `python3 research/verify_numbers.py` — the figure gate

**Purpose.** Re-check every number quoted in `RANKED_LISTS.md` and `STRATEGIES.md`
against the result files that produced them. No arguments; CI runs it.

```bash
python3 research/verify_numbers.py
```

```
figures checked against the run that produced them: 950
  RANKED_LISTS.md: 919  (cpcv 615, geometry 58, pair 36, perturb 7, prose 8, walk_forward 180)
  STRATEGIES.md: 31
```

**When *not* to rely on it.** It checks table cells, not prose — its own config
allows only 8 prose figures. `RANKED_LISTS.md:125` still reads "At the long horizon
buy-and-hold is 3rd" where its machine-generated table puts it **6th**, and the
verifier passes at 950 figures regardless. A green run means no *table* figure
drifted, not that the document is right.

### `python3 research/turnover_table.py` — one comparable table

**Purpose.** Build the ten-coin turnover table from a **single** timestamped pull,
and `--check` that every coin spoke agrees with it.

**Why it exists.** Ten spokes each pulling their own snapshot produced ten figures
that were ranked against each other anyway, and the ranking was wrong: the SOL spoke
claimed the highest turnover of the ten at 3.69% from a per-asset endpoint, while the
single-timestamp pull puts **DOGE ahead**, 3.44% to SOL's 3.32%.

```bash
python3 research/turnover_table.py            # print it
python3 research/turnover_table.py --check     # fail if a spoke disagrees
```

### `python3 research/leverage_economics.py` — what leverage costs before it earns

**Purpose.** The cost model for high-leverage perpetuals on Jupiter Perps: break-even
move by holding period, where borrow carry overtakes the round-trip fee, time to
liquidation from carry alone, and the fee cost of trade *count* at leverage. Generates
every table in `research/LEVERAGE-ECONOMICS.md`.

**No network, no data files.** Closed-form arithmetic over published venue parameters,
so it reproduces exactly and needs no cache. It is also the one research script whose
output does not move when `HORIZONS` changes.

**When to use it.** Before designing anything leveraged — it answers "what must this
trade overcome" independently of whether the signal is any good.

**When *not* to use it.** As evidence a strategy works. It is a **cost model and says
nothing about edge**. Across 48 out-of-sample months every strategy family in this repo
lost to buy-and-hold unlevered; leverage rescales an edge, it does not create one.

**The result worth knowing even if you never run it.** Leverage cancels out of the
break-even equation:

```
pnl%_collateral  = L*move - (fee_rt*L + rate*util*hours*L)
break_even_move  = fee_rt + rate*util*hours        <- L cancels
```

A 2x and a 250x position need the **same** price move to break even. Leverage changes
only how close the absorbing barrier sits and how fast carry consumes collateral — both
survival terms, not profitability terms. Two consequences the tables quantify: carry
overtakes the round-trip fee at **~15 h for longs and ~80 h for shorts**, splitting
leveraged trading into two regimes that reward opposite behaviour; and **100 round trips
at 10x costs 120% of collateral in fees alone**, which is why grid and market-making are
structurally insolvent at leverage rather than mistuned.

```bash
python3 research/leverage_economics.py --self-test   # gate: 7 load-bearing claims
python3 research/leverage_economics.py               # all tables
python3 research/leverage_economics.py --markdown    # the doc's tables, regenerated
```

**Limits, stated in the script and the doc.** Borrow rates are Gauntlet's May-2024
recommendation, not a live read, and utilisation moves continuously — treat every figure
as an order-of-magnitude frame. **Price impact is not modelled** (per-custody parameters
are on-chain and undocumented), nor are keeper latency, priority fees, failed
transactions, or the liquidation penalty itself. Every omission makes the real picture
worse, never better. Verify venue parameters at `docs.jup.ag` before relying on them.

### `python3 research/short_horizon_economics.py` — the same question below one hour

**Purpose.** The sibling of `leverage_economics.py` for holds of seconds to hours, where
the cost picture inverts. Generates every table in
`docs/short-horizon-leverage-concept-family.md`: the toll decomposed by sub-hour holding
period, fixed Solana transaction cost in bps of notional, the win rate a symmetric trade
needs to break even, daily fee burn by turnover, and where the liquidation barrier sits
relative to the noise band.

**When to use it.** Before taking seriously any strategy that holds for minutes. It
answers "how often can this trade before the fee eats the account" and "is the target
move even reachable net of costs".

**When *not* to use it.** As evidence about any specific strategy, and — more sharply
than for its sibling — as anything resembling a backtest. **This repo has no sub-hourly
data at all.** Every empirical result in `research/` is on 1-hour bars, which cannot
resolve the intrabar path that decides whether a leveraged position survives.

**The results worth knowing even if you never run it.**

- **Below an hour, carry is ~0.1% of the toll.** The 12 bps round-trip fee is the whole
  cost, which makes turnover — not leverage, and not duration — the binding constraint.
- **One-minute turnover costs 173% of collateral per day in fees at 1× leverage.** At 10×
  it is 1,728%. This is the number that ends most short-horizon designs.
- **A target move below the toll cannot break even at any win rate**, including 100%. A
  5 bps or 10 bps target is arithmetically dead, not merely difficult.
- **Fixed transaction cost is the one term leverage improves**, because it amortises
  across a larger notional: a contested-priority round trip is 20 bps on $500 of notional
  and 0.04 bps on $250,000.

```bash
python3 research/short_horizon_economics.py --self-test   # gate: 10 load-bearing claims
python3 research/short_horizon_economics.py               # all tables
python3 research/short_horizon_economics.py --markdown    # the doc's tables, regenerated
python3 research/short_horizon_economics.py --vol 1.2     # barrier table at a different vol
```

**Limits.** It inherits every limit of `leverage_economics.py` — venue parameters are not
a live read, price impact is not modelled — and adds one of its own: the barrier table
assumes 70% annualised volatility with square-root-of-time scaling. **That is an
assumption, not a measurement**, and `--vol` exists so the sensitivity is visible rather
than buried. Keeper latency is not modelled because Jupiter publishes no figure for it.

---

### `python3 research/ratio_rotation.py` — hold whichever coin is cheapest against its peers

**Purpose.** Test the folk strategy of chaining discounted pairs — buy ETH because
ETH/BTC is cheap, then spend that ETH on SOL because SOL/ETH is cheap. Separates the
three claims bundled in that idea and answers each: chained routing, buy-the-discount
rotation, and its inverse. Generates every table in `research/RATIO-ROTATION.md`.

**Why it is not a registered strategy.** The engine is single-asset — `run_backtest`
takes one series and a strategy returning exposure on *that* asset, so "which of five
coins do I hold now" has no expression in the `Strategy` protocol. This is a standalone
portfolio simulator that borrows the project's cost model, `make_groups`, `pbo_cscv`
and the whole `deflated_sharpe` module, and implements only the missing part. It has no
strategy card for the same reason: there is no `registry_key` to attach one to.

**When to use it.** Before building anything cross-sectional or rotational, and any
time someone proposes routing through an intermediate asset to capture a better rate.

**When *not* to use it.** As evidence about triangular arbitrage. All series here are
USD-quoted, so cross rates are consistent by construction and no parity deviation can
exist to trade — see `backtester/strategy_cards/triangular_arbitrage.md`, which explains
at length why measuring it on this data would manufacture a spurious equity curve.

**The result worth knowing even if you never run it.** Cross rates derived from a common
numeraire close exactly:

```
(ETH/BTC) x (SOL/ETH) = SOL/BTC        to floating point
```

So BTC->ETH->SOL and BTC->SOL end holding the identical quantity of SOL, and the chained
route simply paid **two fee legs instead of one** (15.99 bps vs 8.00 bps). Chaining
cannot add return; it can only subtract cost. What survives is asset *selection* — and
measured over 72 configurations, **all 36 buy-the-discount variants had negative
out-of-sample Sharpe** (best -0.061, median -0.399). The inverse, buying relative
strength, was positive (best Sharpe 1.771, +12.93%/month) but **failed Deflated Sharpe on
both universes** and still lost to simply holding ZEC (+13.71%/month) on the same slice.

```bash
# data/ is gitignored; fetch the panel first on a clean checkout.
python3 -m backtester.core.universe --assets BTC,ETH,SOL,DOGE,ZEC --interval 1d

python3 research/ratio_rotation.py --self-test        # gate: 23 checks
python3 research/ratio_rotation.py --universes        # why the panel is 5 coins, not 8
python3 research/ratio_rotation.py --turnover-table   # cost drag by holding period
python3 research/ratio_rotation.py --demo-chain       # chained vs direct routing
python3 research/ratio_rotation.py --sweep --out rotation_5coin_1d.csv
python3 research/ratio_rotation.py --carry            # borrow-fee sensitivity
```

**Limits, stated in the script and the doc.** Rotation needs every asset present at bar
`t`, so the panel is the **intersection** and its length is set by the shortest member —
adding BNB or HYPE collapses the study from 1,875 bars to 287 or 181, which is why the
universe is five coins rather than "all of them". Long-only, one venue, daily closes, and
an out-of-sample slice containing one dominant idiosyncratic move (ZEC +979%). The
`--carry` table is a **borrow-fee cost curve, not a carry strategy**: `perps.py` models a
fee both sides pay, whereas funding changes sign, and no funding history is cached here.

---

## Index and search

Full detail in `index/README.md`. `build.py all` is offline; only `semantic` opens a
socket, to localhost ollama, and nothing under `backtester/` may import `index/` —
there is a test asserting it.

```bash
python3 index/build.py all          # metadata + BM25 + concepts
python3 index/build.py semantic     # embeddings (opt-in, needs ollama)
python3 index/build.py --check      # gate: index matches the tree

python3 index/search.py "how are costs applied"   # hybrid, the default
python3 index/search.py --text "fee_bps"          # exact
python3 index/search.py --semantic "why did this stop working"
python3 index/search.py --concepts                # 21 concepts
python3 index/search.py --concept evidence-floor
python3 index/search.py --file backtester/core/cpcv.py
python3 index/search.py --kind code-python "grid"
```

**When to use which.** `--text` when you know the identifier; `--semantic` when you
have a question and not a keyword; the default hybrid when you are unsure, which is
most of the time. **When not to use `--semantic`:** to find one specific identifier —
an embedding will rank `slippage_bps` beside `fee_bps` when you wanted one of them.

Regeneration order matters, because the two derived docs are themselves tracked:

```bash
python3 index/build.py all && python3 index/make_files_doc.py \
  && python3 index/make_concepts_doc.py && python3 index/build.py all \
  && python3 index/build.py --check
```

---

## Documentation gates

```bash
python3 scripts/check_docs.py            # test counts, doc drift, dead index paths
python3 scripts/check_docs.py --prune    # drop dead entries from the JSON index
python3 scripts/build_doc_index.py       # rebuild docs/high_signal_file_index.json
```

`docs/high_signal_file_index.json` is a **104-file curated** list for deciding what
to read; `index/` is exhaustive search over every file. Neither subsumes the other
and both are checked in CI.

---

## Extension (Node)

Run from `extension/`. Zero runtime and zero dev dependencies by design.

```bash
node --test                                    # unit + parity tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100   # headless, no orders
node tools/cli.js --help                       # the CLI surface
```

**`--offline` keeps it off the network.** `node tools/api-server.js` starts a
long-running HTTP server and will not return — do not invoke it from a script or an
agent expecting completion. `node tools/verify-endpoints.js` hits live Jupiter
endpoints and is scheduled rather than run per-commit, so a third-party outage does
not turn every PR red.

**Dry-run is the default and a fresh install must not be able to place an order.**
Read `docs/SECURITY.md` before touching anything here.

---

## soltui

### `python3 -m soltui.serve` — the console as a real window

**Purpose.** Serves the nine-tab console over loopback HTTP so it renders in a
browser window. This is the way to reach the console.

**Why it exists.** The console has had tabs, buttons and settings since it was
written, but the only route to them was the menu bar's Terminal spawn — an
`osascript` call wrapped in `check=False`. When Terminal automation is not
permitted, which is the default on a fresh macOS install, that fails **silently**,
so the app appeared to have no interface at all. It was a reachability bug, not a
missing UI. A menu-bar process has no controlling terminal; serving removes that
constraint.

**When *not* to use it.** On a shared machine without thinking about who can reach
the port. It binds `127.0.0.1` only and there is no flag to widen that, but
anything that reaches the loopback port can drive the console.

Options: `--port` (default: first free from 8899), `--no-open`.

```bash
python3 -m soltui.serve                    # opens http://127.0.0.1:8899
python3 -m soltui.serve --port 9000 --no-open
```

```
soltui console -> http://127.0.0.1:8899   (Ctrl-C to stop)
```

Needs `textual-serve` (`pip install -r soltui/requirements.txt`). Without it the
command prints the install line and the terminal alternative rather than failing
obscurely. **Like `api-server.js`, this blocks until interrupted** — do not invoke
it from a script expecting completion.

### The nine tabs

Settings · Strategies · Signals · Backtest · Execute · **Analyze** · **Cumulative**
· **Research** · **Docs**.

- **Analyze** — every registered strategy replayed for any cached coin **at any
  timestamp**. Distinct from Signals, which reads the latest bar of the configured
  asset. Strategies are path-dependent, so the series is truncated at the chosen
  moment and replayed from the start; reading a row out of a full-history replay
  would report a number that depended on the future.
- **Cumulative** — every CSV in `research/results/` with the 10-trade evidence
  floor applied. Rows below it are counted and listed separately, never pooled into
  a ranking — on the committed corpus that is **1,332 of 2,691 configurations**.
  Files are shown side by side rather than merged, because a median across
  different assets, horizons and geometries describes nothing.
- **Research** — which driver answers which question, and what each established.
- **Docs** — filterable catalogue of every tracked file with a **read-only**
  viewer. Read-only deliberately: `research/results/` is the evidence behind every
  published figure and `verify_numbers.py` assumes it changes through committed
  scripts, so a GUI editor would be an unlogged write path into that tree.

### macOS menu bar and packaging

```bash
python3 -m soltui.app                        # menu-bar shell
python3 soltui/soltui-service status|start|stop|build
python3 -m soltui.tui                        # the console in a terminal
```

The menu bar leads with **Open console** (the window) and keeps **Open console in
Terminal** as a labelled fallback that now reports the automation-permission error
instead of swallowing it.

The **flag file is the real off switch**, not the menu-bar Quit item: `KeepAlive`
necessarily overrides Quit, so removing
`~/Library/Application Support/soltui/supervise.enabled` is how you actually stop
it. py2app and launchd have no Linux equivalent, so CI runs this job on macOS and
covers the unit suite only — the packaging paths are verified by hand.

---

## The 1-minute pipeline

Separate from the daily and hourly fetch and sweep sections because the scale changes the engineering: ~2.6M bars per asset, ~1GB of CSV,
and a fetch measured in hours.

### `python3 -m backtester.core.fetch_minutes` — fetch 1-minute history

```bash
python3 -m backtester.core.fetch_minutes --asset BTC --years 5
python3 -m backtester.core.fetch_minutes --all --years 5 --workers 6
python3 -m backtester.core.fetch_minutes --all --coverage-only      # measure, fetch nothing
python3 -m backtester.core.fetch_minutes --asset BTC --max-windows 50   # pilot
```

| Flag | Meaning |
| --- | --- |
| `--asset` | repeatable |
| `--all` | BTC, ETH, SOL, DOGE, ZEC, XRP, BNB, HYPE — the Coinbase-listed subset |
| `--years` | default 5 |
| `--workers` | concurrent requests, default 6; a **shared** limiter still caps aggregate throughput at 8/s |
| `--max-windows` | stop after N windows per asset, for piloting |
| `--no-resume` | refetch everything, ignoring the progress sidecar |
| `--coverage-only` | re-measure what is on disk |

**It is resumable — kill it and re-run it.** Each completed 300-minute window is appended immediately
and its start recorded in `data/<ASSET>_1m.progress.json`.

**Read the coverage table, not just the bar count.** Two different absences look identical in a bar
count and the table separates them:

- **`short by`** — missing *calendar*. The venue has no more history. XRP starts at its 2023
  relisting; BNB has ~287 days; HYPE ~181.
- **`complete`** — missing *minutes inside* the calendar it does cover. **ZEC covers the full five
  years and is only 60.2% complete** — it does not trade every minute. Every lookback in the engine
  counts *bars*, so a 200-bar average on ZEC spans far more wall-clock time than 200 minutes, and
  nothing downstream can tell.

Coverage is recorded in `research/results/minute_coverage.json`, which is tracked. The CSVs are not.

### `python3 research/minute_sweep.py` — preliminary 1-minute sweep

```bash
python3 research/minute_sweep.py                                  # 500k bars per asset
python3 research/minute_sweep.py --common-window --tag common     # like-for-like
python3 research/minute_sweep.py --all-bars                       # full history; hours
python3 research/minute_sweep.py --param-scale 60                 # wall-clock params; slow
python3 research/minute_sweep.py --asset BTC --strategy macd --bars 50000
```

| Flag | Meaning |
| --- | --- |
| `--asset`, `--strategy` | repeatable filters |
| `--bars` | most recent bars per asset, default 500,000 (~347 days) |
| `--all-bars` | every cached bar |
| `--common-window` | intersect all assets' calendars so cells are comparable |
| `--param-scale` | multiply bar-count parameters (60 preserves the hourly wall-clock window) |
| `--workers` | default `min(6, cpu-2)` |
| `--tag` | suffix for the output filenames |

**Three things to know before reading its output.**

**It is preliminary, and the word is load-bearing.** One pass per cell — no CPCV, no PBO, no split.
This repo's own finding 1c measures in-sample rank as anti-informative, so a good number here is a
reason to spend a real protocol on that cell, not evidence.

**`--common-window` vs the default is a real choice.** By default each asset uses its own recent
bars, so spans differ and **cross-asset rows are not like-for-like**. `--common-window` intersects the
calendars, which is comparable but bounded by the shortest history (~181 days, HYPE).

**Parameters are bar counts.** `ma_crossover(fast=12, slow=48)` was tuned on hourly bars; at 1m the
same numbers mean 12 and 48 *minutes* — a different strategy, not the same one at finer resolution.
`--param-scale 60` restores the wall-clock window and only scales genuine bar-count keys, never a
threshold like `num_std`. It is expensive: `macd` went from 0.1s to 29.6s on 20k bars.

**Expect costs to dominate.** Measured on 100k bars of BTC, 22 of 25 strategies lost 79–100% of
capital with $7,800–$9,900 of fees against $10,000. Every row reports gross beside net for that

---

## Reading the numbers correctly

The scripts are honest; the risk is in what a reader does with their output. Five
findings that constrain every figure above.

**1. In-sample rank is anti-informative.** PBO **0.700** at both daily horizons
against a measured 0.500 noise line. Spearman ρ(in-sample, out-of-sample Sharpe) is
**−0.419** at the medium horizon. Picking the best-looking configuration was
measurably worse than choosing at random.

**2. The five recommended configurations do not transfer.** From
`research/CROSS-ASSET-TRANSFER.md`, run unchanged on DOGE and ZEC:

| # | Configuration | Horizon | SOL | DOGE | ZEC |
|---|---|---|---|---|---|
| 1 | `all(dual_momentum+vol_regime)` | long | **+1.345** | +0.476 | **−0.294** |
| 2 | `any(hurst_switch+ou_reversion)` | medium | **+1.290** | **−0.706** | +0.492 |
| 3 | `any(ou_reversion+obv_trend)` | long | **+1.054** | +0.669 | +0.348 |
| 4 | `obv_trend_60` | long | **+0.774** | +0.575 | +0.150 |
| 5 | `vol_regime_60_0.5` | long | **+0.696** | −0.125 | −0.057 |

**All ten transfers degraded; none improved.** Median degradation −0.821 on DOGE,
−0.753 on ZEC. Only **#3 and #4** — the lower-ranked pair — stayed positive on all
three assets, so the ordering 1–5 must not be read as a preference ranking. #2 is
100% positive on SOL and **0% positive on DOGE across the same 15 paths**, so the
collapse cannot be blamed on evaluation geometry.

**3. The path counts are 15 or 21, never the nominal 28.** Four of those five rest on
fifteen paths. Fewer paths is a weaker estimate, and every results CSV carries
`n_paths` per row.

**4. The dataset explains more than the strategy.** The same 25 strategies, identical
parameters: BTC **25/25** positive, ZEC 24/25, ETH 18/25, DOGE 16/25, SOL daily
13/25, SOL hourly **0/25**. Applying the 10-trade floor makes BTC 24 of 24 and ETH 18
of 24. A top-ranked configuration fell from 1st to 23rd on a timeframe change alone.
Of 25 singles across five assets, **eight are positive everywhere and not one is from
a reversion family** — and no reversion-family strategy clears all five.

**5. Buy-and-hold is the benchmark that keeps winning.** Zero parameters, median path
Sharpe **+0.534** on SOL, 2nd of 25 at the medium horizon. Exactly one single beat it
there. On ZEC (+0.659) it beat **all five** recommended configurations, the best of
which reached +0.492. And because it needs no warm-up it is evaluated on all 8 blocks
and 28 paths, giving it the tightest interval in the study by construction.

**Not investment advice.** Every figure here is a backtest on historical data, and
the point of the findings above is that most of them did not survive contact with a
different asset, timeframe, or evaluation geometry.

### 1-minute pipeline troubleshooting

**`fetch_minutes` is slow.** Expected throughput is ~6-7 windows/s against a shared 8/s limit. The
endpoint answers in ~0.20s median but ~15% of connections stall, which is why `REQUEST_TIMEOUT` is 3s
-- raising it makes throughput *worse*, not better.

**`fetch_minutes` reports `PARTIAL`.** Some windows were not attempted. Re-run the same command; it
resumes.

**`minute_sweep.py` dies with `BrokenProcessPool`.** Out of memory. Lower `--workers` or `--bars`.
Slices are prepared once in the parent precisely to bound this; if it still happens the slice itself
is too large for your machine.

**A strategy takes minutes per cell at 1m.** Indicator cost is proportional to the window, so
`--param-scale 60` multiplies it. `rsi` extrapolates to ~1.8h per asset on a full 2.6M-bar series.
Bound it with `--bars`.

