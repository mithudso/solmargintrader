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
