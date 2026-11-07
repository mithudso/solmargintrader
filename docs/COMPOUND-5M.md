# Compound five-minute scorecard

A tester for one question: **will the next 5-minute bar close up or down?** Every metric in
`5minleveragestrategies.json` (and the ones it was missing) scores that bar from -1 (down) to +1
(up). The scores are combined into one call (UP, DOWN or FLAT), which you can backtest and
forward test, metric by metric and combined. Nothing here places an order.

| Piece | Where |
| --- | --- |
| Scoring and aggregation (pure, no I/O) | `backtester/core/scorecard.py` |
| Historical evaluation through the engine | `backtester/core/compound.py` |
| Saved config, live reads, forward ledger, sweeps, CLI | `soltui/compound.py` |
| The tab | soltui → **Compound 5m** |
| Registry commands (TUI, CLI, API, extension host) | `compound.catalog`, `compound.config`, `compound.save`, `compound.reset`, `compound.signal`, `compound.backtest`, `compound.results`, `compound.forward_tick`, `compound.forward_status` |
| Agent skill | `skills/five-minute-signal/SKILL.md` (live copy in `~/.claude/skills/`) |
| One command for everything | `research/full_suite.py` |

## How a call is made

1. **Score.** Each enabled metric returns a score in [-1, 1] for the latest *closed* bar, or
   "undefined" (warming up, or a live input missing). Undefined is never treated as zero.
2. **De-duplicate families.** RSI, Stochastic and CCI measure one thing; MACD and an EMA cross
   share two EMAs. With `dedupe_families=1` each family votes once, at its heaviest member's
   weight, so the family with the most indicators does not win by count.
3. **Weight by regime.** Each bar is classified trend (ADX ≥ 25), range (ADX ≤ 18), squeeze
   (Bollinger width in its lowest 15% over a day) or neutral. Trend styles weigh 1.5× in a
   trend and 0.5× in a range; reversion styles the reverse; breakouts 1.6× in a squeeze.
   This is the catalogue's own regime table, and the measurements below show it points the
   wrong way at 5m.
3b. **Learn.** With `adaptive=1` (default) each metric's weight is also multiplied by its own
   learned edge over a coin flip (see below).
4. **Threshold.** |composite| ≥ `entry` (0.25) calls UP or DOWN. A held position stays on while
   the composite keeps its sign above `exit` (0.10): hysteresis, because every flip pays a
   round trip.
5. **Gate.** Any enabled gate that blocks forces FLAT and is named in the call. A gate that
   cannot be evaluated blocks (fails closed); a score that cannot be evaluated counts as
   undefined and lowers coverage. Cross-parameter mistakes (an EMA "fast" span not below "slow",
   a Fibonacci zone upside down) are refused when saved, not discovered at scoring time.

## Learning from its own record (on by default)

With `adaptive=1` every metric's weight is multiplied by **its edge over a coin flip, learned
from its own calls**. A metric "calls" a bar when |score| ≥ `entry`; once the next bar closes,
the call is right or wrong.

* **Bayes, literally.** Each metric's hit probability has a Beta(`adaptive_prior`/2,
  `adaptive_prior`/2) prior: 50 right and 50 wrong pseudo-calls by default. Every resolved call
  updates it. The posterior mean is the "learned hit"; the tab and `signal` also show
  P(better than a coin flip) from the posterior.
* **Edge, not raw hit rate.** Multiplying by 55% vs 47% would barely separate a useful metric
  from a harmful one and would still let the harmful one vote. The multiplier is
  2 × hit − 1: zero at 50%, so a metric with no proven skill gets no say.
* **Inverting the reliably wrong (on by default, `adaptive_flip=1`).** A metric whose record is
  below 50% has its vote reversed, weighted by how far below. Each trend metric inverted scored
  50–55% on nearly every coin. With inversion on, the compound's losses were smaller on all five
  coins than with muting.
* **A capped record.** Only calls from the last `adaptive_window` bars count (4,032 = two
  weeks), each equally. Without a cap, five months of history would make each new miss move a
  weight by a meaningless amount; with it, a miss moves a metric's weight as much in month five
  as in week two, and a metric that stops working loses its weight within two weeks. Shorten or
  lengthen the window in the Aggregate box. `adaptive_halflife` > 0 also fades calls inside the
  window (off by default). On the 30-day sample the two-week window and the earlier one-week
  fade gave hit rates within 0.6 points of each other on every coin.
* **No look-ahead.** A call made at bar t is only counted once bar t+1 has closed. The
  prefix-invariance test runs with adaptive weighting on.
* **Live and forward.** A live call fetches up to the window (two weeks of bars) and learns from
  them, plus any older forward-ledger calls still inside the window, counted only when that
  metric's settings were the same and never twice. Live-only metrics (premium, open interest, order book) learn only from the
  ledger, so their weight grows as forward ticks accumulate.

### Moving the settings, carefully (`tune=1`; autopilot turns it on)

Each metric also runs shadow copies at ×(1 − `tune_step`) and ×(1 + `tune_step`) of each of its
numbers. It moves to a neighbour only when the posterior says that neighbour is more accurate
with probability above `tune_confidence` (0.95) after `tune_min_calls` (300) calls. Then it
re-centres on the new settings and waits `tune_cooldown` bars (two days). Moving after every
single miss would chase noise, because at 5m about half of all outcomes are coin flips.
With autopilot on (the default) every forward tick makes a move permanent by itself;
**Adopt tuned settings now** in the tab does it by hand.

Measured on the same 30 days, out-of-sample hit rate of the default compound:

| | BTC | DOGE | ETH | SOL | ZEC |
| --- | --- | --- | --- | --- | --- |
| static weights (`adaptive=0`) | 48.5% | 44.0% | 45.6% | 46.3% | 48.9% |
| learned weights (`adaptive=1`, two-week record) | 46.5% | 55.6% | 52.0% | 50.2% | 51.6% |
| + tuning at 0.65 / 50 calls | 47.4% | 56.2% | 53.4% | 52.1% | 51.4% |

After the four new metrics, the family regrouping and inversion by default, the default compound
scored (static → learned + invert): BTC 50.3% → 49.5%, DOGE 44.9% → 55.8%, ETH 45.6% → 52.6%,
SOL 47.3% → 51.1%, ZEC 48.3% → 51.1%. Returns: BTC −13% → −20%, DOGE −49% → −27%,
ETH −43% → −40%, SOL −50% → −34%, ZEC −69% → −70%.

Learning fixes the direction problem on four of five coins: it mutes the trend metrics and
leans on reversion, without anyone choosing. Tuning at the default 0.95 bar moved one metric
once in five coins and thirty days. Neighbouring settings are nearly the same signal, so the
data rarely proves one better. A looser bar moves the hit rate by about a point either way,
inside the noise, and several bars were tried, which is itself selection. So the scorecard's own
default stays `tune=0`; autopilot turns the search on because adopting its rare, well-evidenced moves
is what the owner asked for, not because tuning was shown to add return. **Returns stayed negative
in every row**: a better hit rate does not beat a 16 bps round trip on a 6–9 bps move.

## Every coin, in parallel, each with its own numbers

The compound runs on ten coins: **BTC, ETH, SOL, XRP, HYPE, DOGE, LINK, NEAR, SUI, AVAX**
(`COMPOUND_5M_UNIVERSE` in `backtester/core/universe.py`). The owner chose them on 2026-11-07
from a screen of the top 50 coins by market cap, pegged tokens left out
(`research/results/top50-nonpegged-2026-11-07.json`). The screen, with each coin's live turnover,
perp leverage, Coinbase status, verdict and reason, is `research/results/top50-screen-2026-11-07.json`.

A five-minute call pays only with leverage and a round trip near 13 bps, so the screen asked:

| Test | Why it disqualifies |
| --- | --- |
| A perpetual market with 10x or more (Hyperliquid) | Without leverage a 5m move cannot beat the fees. Jupiter Perps lists only SOL, ETH and BTC. |
| 24h volume above 0.5% of market cap | Below that, a 5m position is the visible order book and the 2 bps slippage model is wrong. |
| Coinbase USD candles | Live calls and forward training read Coinbase. |
| No exchange-token, rename or privacy-delisting distortion; enough history | Exchange tokens trade on their exchange's buybacks; a renamed token's history is another token. |

13 coins failed outright: LEO, M, RAIN, CRO, OKB, BGB, HTX, WBT, BTW, QNT, JST (no perp, thin
volume or exchange token), CC and SKY (perp capped at 3x, turnover near 0.3%). Eight more carry a
caution: ZEC (60% incomplete bars), XMR, TRX, MNT, GRAM, WLFI, PUMP, ASTER. The screen did not
check news after early 2026; check for a recent hack, migration or delisting before relying on a
coin. Cached data for any other coin can still be backtested from the CLI with `--asset`.

**Costs are Hyperliquid's.** The owner can trade on Hyperliquid (confirmed 2026-11-07), which
lists perps for all ten coins and charges less than Jupiter Perps. The default execution is its
base taker fee, 4.5 bps per side (Jupiter: 6 bps), plus 2 bps slippage per side: a **13 bps**
round trip (16 on Jupiter). `research/results/hyperliquid-costs-2026-11-07.json` holds the live fee
schedule and an order-book walk per coin. At $2k a market order cost at most 2.2 bps from mid on
every coin, so 2 bps holds for small size. At $10k–$50k, LINK, SUI and AVAX reached 2–6 bps on one
side. Raise `slippage_bps` for that coin before sizing up. A resting (maker) order pays 1.5 bps,
but a 5m call that enters at the next bar's open is a taker order. Funding is not modelled
separately: the engine's perp borrow charge stands in for it, and over a 5–30 minute hold either
is a small fraction of one basis point. The 2026-11-07 findings below were measured at 16 bps.

**Liquidation is Hyperliquid's too.** Hyperliquid's maintenance margin is half the initial margin
at the coin's max leverage (`HYPERLIQUID_MAX_LEVERAGE` in `backtester/core/compound.py`): 1.25% of
notional on BTC (40x), 2% on ETH (25x), 2.5% on SOL and XRP (20x), 5% on the 10x coins. Jupiter's is
0.2%. At 5x a 10x-max coin is liquidated about 15% away, not about 19.7%. The engine, the
liquidation price in each sized call and `gate_liquidation` all use the coin's margin.

* **Data.** `research/full_suite.py` caches 1-minute candles back to each coin's earliest
  available minute: `python3 -m backtester.core.fetch_minutes --assets BTC,ETH,... --years 7`. That
  is the finest history Coinbase serves; trade-by-trade ticks exist but a single month took days
  to backfill.
  * For a coin Coinbase does not list, `python3 -m backtester.core.fetch_minutes_alt --assets TRX`
    fetches 1m candles from OKX, KuCoin, Bitget or WhiteBIT against **USDT** (`ASSET_VENUE`). Each
    file gets a `<COIN>_1m.source.json` sidecar naming the venue and pair, and the backtest label
    shows it. A USDT price is not a USD price. KuCoin and WhiteBIT return rows as
    `[time, open, close, high, low, ...]`; the fetcher reorders them and stops when more than 1% of
    a page has impossible OHLC. These coins are backtest only.
* **Data quality, per coin.** Coinbase's 1m endpoint drops minutes that *did* trade (84% of
  sampled gaps, `research/CANDLE-GAP-AUDIT.md`), so a 5m bar built from fewer than five minutes
  can carry a wrong close and an understated high or low, which flatters liquidation checks.
  Coinbase's own 5m candles carry the same damage. Every bar records how many minutes it came
  from. Each backtest reports the share of incomplete bars, and the status bar warns above 1%.
  Measured 2026-11-07 on the full history:

  | Coin | History | 5m bars | Incomplete bars |
  | --- | --- | --- | --- |
  | BTC | 2019-11 to now | 735,480 | 0.03% |
  | ETH | 2019-11 to now | 735,474 | 0.50% |
  | SOL | 2021-06 to now | 566,776 | 1.04% |
  | DOGE | 2021-06 to now | 570,808 | 4.49% |
  | ZEC | 2020-12 to now | 575,919 | **60.3%** (64% minute coverage; read its results as unreliable) |

  Only trades repair a bar (`research/tick_backfill.py`).
* **Own numbers.** Each coin has its own learned record, backtests and forward ledger. It can also
  have its own settings stacked on the shared ones. Pick the coin at the top of the tab.
  **Edits apply to** switches between all coins (the shared base) and this coin. Adopt tuned
  settings always saves to the coin.
* **Backtest all coins** runs every coin at once in parallel processes, each with its own settings.
* **Start unattended: all coins** starts one forward-training process for all ten coins. Each
  bar it ticks the coins one after another, so ten coins cost one background process, not ten.
  Each coin keeps its own lock, log and stop file, so **Stop unattended** on one coin releases
  it from the shared loop and the rest keep running. Closed candles are cached per coin, so after
  the first tick each coin costs one request per bar. A rate-limit reply (429) is retried with
  back-off.
* **Every coin at a glance**: own settings, cached data, latest backtest verdict and hit rate,
  forward calls and hit rate, paper dollars, and whether its trainer is running.

## Unattended forward training

**Start unattended training** in the tab starts a separate background process at low priority
(autopilot does this for every coin by itself).
After every closed 5m bar it records the call, resolves earlier calls, and lets the learned
weights update from them. It keeps running after the console closes, logs and survives network
errors, and runs one per asset (a lock file proves it). **Stop unattended** ends it after the
current tick. From a shell: `python3 -m soltui.compound forward --asset SOL --loop`.

## Autopilot: hands-off and self-optimizing (on by default)

The owner asked for a trainer that runs and improves itself with no input. Autopilot is one switch,
`autopilot` at the top of `~/.config/soltui/compound/config.json` (missing means on), shown as
**Autopilot: on/off** in the tab. With it on:

- **Tuning runs.** The effective config has `tune=1` whatever is saved, so the config hash says so.
- **Tuned settings are adopted automatically.** Every forward tick (unattended or in the tab) saves
  the settings tuning moved a metric to as that coin's own settings, and appends an `adopt` row
  (`metric`, `from`, `to`, `ts`) to the coin's forward ledger. A metric adopts again only
  `tune_cooldown` bars (two days) after its last adoption: each evaluation restarts the search from
  the saved settings, so without that memory it could step once per bar. The call for the bar is
  recorded under the settings in force when it was made.
- **Every coin keeps training.** The console starts any coin's unattended loop that is not running
  when it opens, and a LaunchAgent does the same every five minutes, so a reboot, a crash or a
  closed console needs no one. Install it once from the main checkout (it refuses a worktree):
  `python -m soltui.compound_agent install`; check it with `status`. The job runs
  `python -m soltui.compound autopilot`. **Stop unattended** still stops a coin, but autopilot
  restarts it within five minutes: turn autopilot off to keep it stopped.
- **Learned weights** (on by default anyway) keep reweighting and inverting metrics from their record.

Every coin's process writes the same `config.json`, so `save_state` holds an exclusive lock
(`config.json.lock`) for its whole read-modify-write.

What autopilot does not do: it does not make the compound profitable. At the 0.95 bar tuning
rarely moves (above), and every backtested return was negative. It automates the evidence-gated
search and the forward record; it places no order. Turning it off leaves the saved settings and
the running loops as they are.

## Your wallet: where it is read from, and what it is used for

Wallet information has one home: **soltui Settings** (edited on the Settings tab, stored in
`~/.config/soltui/config.yaml`, owner-only). It never reads a key: private keys stay in their key
files, and sizing a call needs only public balances.

**Hyperliquid account first.** The owner trades the ten coins on Hyperliquid. When
`hyperliquid_address` is set (default: the owner's `0x901a…5314`, the same address as Base), each
call is sized from that account, labelled `Hyperliquid (live)`. Two public `info` calls
(`clearinghouseState`, `spotClearinghouseState`) read it; no signature is involved.
**Usable** is the perp account's `withdrawable`, the margin not tied up in positions. Spot USDC is
shown but not counted, because it must move to the perp account before it can margin a trade.
Open Hyperliquid positions are listed with size, entry and liquidation price. A failed or malformed
read is reported as unavailable, never as $0. An empty account gives no size and says to deposit
USDC. On 2026-11-07 the account held $0.

**Solana wallet as the fallback.** With `hyperliquid_address` blank, the call is sized from
`solana_address`, scanned read-only with the same scanner as the Wallet tab. Jupiter Perps takes SOL, USDC and USDT as collateral, so those count as **usable**. USDC and USDT
are matched by mint address, so a look-alike token named "USDC" does not count. A balance with no
price is listed as unknown and left out, never counted as zero.

Every live call is then sized:

* **notional** = the smaller of usable × `leverage`, and the size at which reaching the stop
  (`stop_atr` × ATR, the stop the liquidation gate checks) plus the round-trip cost loses
  `risk_pct` (1%) of usable collateral;
* **collateral** = notional ÷ leverage; **loss at the stop** and **round-trip cost** in dollars;
* **liquidation price** from the engine's venue formula (`backtester/core/perps.py`), not 1/leverage.

Forward ticks record that notional with each call, so the forward test also reports **paper $ at
wallet size**: what trading every compound call for one bar would have made after costs. Set
`use_wallet=0` in the Aggregate box to stop reading the wallet.

Not read yet: **open Jupiter Perps positions** (Solana fallback only). No documented read endpoint
was found and the on-chain account layout is not verified here, so they are not guessed. The
sizing does not yet subtract an open position's exposure on either venue; it sizes against free
margin, which already excludes margin those positions use.

## Which metrics fight each other, and which repeat each other

Measured on five coins (correlation of their 5m scores):

* **Mutually exclusive:** `vwap_side` and `vwap_reversion` are mirror images (−0.99). Enable one.
  The same holds for `rsi` with `mode=0` versus `mode=1`.
* **Opposed:** the trend group (`ema_trend`, `ema_cross`, `ichimoku`, `roc`, `macd`) and the
  stretch group (`rsi`, `zscore`, `bollinger`, `cci`, `stochastic`) correlate −0.75 to −0.93.
  At 5m they disagree on nearly every bar. With both on, the call rests on which side has more
  weight. Learned weighting with inversion (below) settles it by flipping the side that is wrong.
* **Duplicates:** `cci` ≈ `bollinger` (+0.98), `rsi` ≈ `zscore` (+0.94), `ema_trend` ≈
  `ichimoku` (+0.87), `macd` ≈ `roc` (+0.80). These now share a family, so each group votes once.
* **Gates that leave nothing:** the cost gate plus the liquidation gate at high leverage block
  almost every 5m bar; the call is then FLAT by design.

The tab shows a live warning line for any enabled pair that fights (correlation ≤ −0.6) or
repeats across families (≥ 0.85) over the last two weeks (`scorecard.relations`).

## Metrics

| Group | Metrics (id) | Source in the JSON |
| --- | --- | --- |
| Trend / direction | `ema_trend` (price vs one EMA), `ema_cross`, `adx_dmi`, `vwap_side`, `htf_trend`, `ichimoku`, `zigzag` (non-repainting swing leg) | EMA, MA crossover, ADX, VWAP, execution step 3, Ichimoku, ZigZag |
| Momentum / adaptive | `roc`, `macd`, `persistence` (lag-1 autocorrelation × last move) | Breakout / momentum, MACD; added |
| Stretch (one family) | `rsi`, `stochastic`, `cci`, `bollinger`, `zscore` | RSI, Stochastic, Bollinger, Mean reversion; CCI added |
| Mean reversion | `vwap_reversion` | VWAP |
| Breakout / structure | `donchian`, `squeeze`, `trend_continuation`, `liquidity_sweep`, `fib_pullback` | Breakout, Volatility squeeze, 5m continuation, Liquidity sweep, Fibonacci |
| Volume / flow | `volume` (unusual volume signed by the candle), `obv`, `money_flow` (candle proxy, not taker delta), `bop` (balance of power), `book_imbalance` (live) | Volume, OBV, Balance of power, Order-flow imbalance |
| Positioning | `funding`, `premium` (live), `oi_flow` (live) | Funding arbitrage input, cross-venue observation |
| Cross-asset | `btc_lead` | added |
| Lifecycle | `trend_lifecycle` (early / mature / exhausted), `cycle_phase` (markup / markdown / accumulation / distribution) | added |
| Gates | `gate_cost`, `gate_liquidation`, `gate_shock`, `gate_volume`, `gate_events`, `gate_session`, `gate_news` (live) | Execution checklist 1-2, regime table "no-trade" |

Every metric's formula, parameter ranges, "works when" and "fails when" are in the tab (select a
row) and in `python3 -m soltui.compound catalog`. Eight catalogue entries are not five-minute
direction calls (grid, scalping as a style, swing, DCA, three kinds of arbitrage, Jupiter's
unpublished flow imbalance); `scorecard.NOT_DIRECTIONAL` says why for each, and the tab lists
them.

## What else should be checked, and what is

* **The whole technicals arsenal? No.** Most indicators are re-expressions of three quantities:
  trend (moving-average distance), position in the recent range (oscillators, bands) and
  volume. Adding Williams %R, MFI, TRIX or KST adds votes, not information. One or two per
  family is enough, and family de-duplication stops the rest from stacking.
* **Higher timeframe.** Added (`htf_trend`, completed 15m–1h bars only).
* **Cost hurdle and liquidation distance.** Added as gates. These matter more than any
  indicator; see the findings.
* **Derivatives positioning.** Funding (backtestable from the Hyperliquid cache), premium, open
  interest change and order-book imbalance (live only: no venue serves their history).
* **Cross-asset lead.** BTC's last closed bar.
* **News.** Treated as *risk*, not as a predictor: a scheduled-event blackout (`gate_events`,
  your events file), a shock detector for unscheduled news (`gate_shock`: range or volume far
  outside normal), and an optional live headline gate (`gate_news`, CoinDesk and Cointelegraph
  RSS, keyword match). Headline *sentiment* is not scored: there is no timestamped archive to
  test it on, so it could only be a guess presented as a number. An enabled news gate blocks
  the call when any of its feeds is unreachable (fails closed).
* **Lifecycle stage.** Two kinds are scored. The *trend's* lifecycle (`trend_lifecycle`: bars
  since the EMAs crossed and extension in ATRs; exhausted trends get faded) and the *market
  cycle* phase (`cycle_phase`, a Wyckoff-style read of the last day). A *token's* lifecycle
  (listing age, unlock schedule, supply concentration) moves on a scale of weeks, not five
  minutes; it belongs in coin selection (`research/coin-intelligence/`), not in this call.

## Findings: 1,420 configurations, five coins, 30 days of 5m bars

Run `20261107T130441Z-f7fea5b2368e`: `python3 -m soltui.compound sweep --perturb --aggregate-grid`
over the cached 2026-07-06 to 2026-08-06 bars (8,927–8,929 per coin) (SOL native 5m; BTC, ETH, DOGE, ZEC aggregated from
1m). In-sample = first 70%, out-of-sample (OOS) = last 30% (about 2,680 bars per coin). Costs:
6 bps fee + 2 bps slippage per side, a 16 bps round trip (Jupiter base fee plus its 1 bp impact
floor and adverse execution).

**1. No configuration made money after costs.** 10 of 1,420 had a positive OOS return; every one
of them had an OOS hit rate within 1.2 standard errors of a coin flip, and 7 of the 10 lost in-sample.
That is the shape of luck, not edge.

**2. Even perfect foresight loses on four of five coins.** The `oracle net bps` column is what a
call that is *always right* earns per one-bar round trip after costs:

| | BTC | DOGE | ETH | SOL | ZEC |
| --- | --- | --- | --- | --- | --- |
| mean \|5m move\| (bps) | 6.2 | 8.7 | 8.6 | 8.5 | 15.6 |
| oracle net per one-bar trade (bps) | -9.8 | -7.3 | -7.4 | -7.5 | -0.4 |

A 5m direction call can only pay by holding through several bars in one round trip, which is
what the hysteresis and the cost gate (`hold_bars`) are for.

**3. Direction is weakly predictable, in the reversion direction.** Out-of-sample hit rates of
each metric alone (z = standard errors from 50%):

| Metric | BTC | DOGE | ETH | SOL | ZEC |
| --- | --- | --- | --- | --- | --- |
| `rsi` | 51.3% (+1.1) | 56.5% (+5.1) | 51.5% (+1.3) | 51.4% (+1.2) | 52.0% (+1.7) |
| `zscore` | 51.7% (+1.5) | 55.3% (+4.6) | 51.8% (+1.6) | 51.3% (+1.2) | 51.8% (+1.6) |
| `bollinger` | 51.0% (+0.9) | 54.5% (+4.0) | 52.4% (+2.1) | 50.8% (+0.7) | 52.0% (+1.8) |
| `ema_cross` | 48.7% (-1.2) | 45.8% (-3.9) | 48.6% (-1.4) | 48.5% (-1.4) | 48.0% (-1.9) |
| `htf_trend` | 47.9% (-2.0) | 47.2% (-2.6) | 47.8% (-2.0) | 46.6% (-3.2) | 49.2% (-0.7) |
| `trend_continuation` | 48.5% (-0.8) | 44.6% (-3.0) | 45.9% (-2.4) | 46.4% (-2.0) | 50.7% (+0.4) |

Reversion metrics beat 50% on every coin; trend metrics fall below it on nearly every coin. So
the catalogue's advice to favour continuation in trends is backwards at this horizon, and the
default compound (regime weighting on) inherits that: its OOS hit rate was 44–49% on all five.

**Read the reversion edge with three cautions.** (a) Part of it is probably bid-ask bounce:
Coinbase closes alternate between bid and ask prints, which creates negative autocorrelation
that cannot be traded. Jupiter fills at the oracle price, which has no bounce, and a taker order on
Hyperliquid pays the far side of the spread, which is the bounce. (b) Calls on
consecutive bars overlap, so the z-scores overstate independence. (c) 1,420 configurations were
tried on one 30-day window; the best few are expected to look good by chance. Thirty days is
one regime. Run the full suite (a year of 5m bars) before trusting any of this.

**Every sweep looks at the same out-of-sample slice.** Ranking on OOS keeps in-sample fitting
out of the leaderboard, but each new run that is ranked on the same slice spends it again. So
`compound.results` (and the tab, and `python3 -m soltui.compound results`) reports how many
configurations have been scored on that exact OOS window across all runs. That number, not one
run's count, is the multiple-testing denominator. A fresh fetch moves the window and resets it.

## Commands

```bash
# Live call with every metric explained (public data, no keys, no orders)
/Users/mitch/.venvs/soltui/bin/python -m soltui.compound signal --asset SOL

# Forward test unattended: one call per closed 5m bar, resolved when the next bar closes
/Users/mitch/.venvs/soltui/bin/python -m soltui.compound forward --asset SOL --loop
/Users/mitch/.venvs/soltui/bin/python -m soltui.compound status --asset SOL

# Backtest the saved config: the compound plus each enabled metric alone
/Users/mitch/.venvs/soltui/bin/python -m soltui.compound backtest --asset SOL

# Everything: fresh data for the universe, then every registry and compound backtest
/Users/mitch/.venvs/soltui/bin/python research/full_suite.py --plan
/Users/mitch/.venvs/soltui/bin/python research/full_suite.py
```

Files: config `~/.config/soltui/compound/config.json`; backtest rows
`~/.config/soltui/compound/backtests.jsonl`; forward ledger
`~/.config/soltui/compound/forward/<ASSET>.jsonl`. Scheduled events for `gate_events` go in the
config file's `events` list (`{"ts": <UTC epoch seconds>, "title": "CPI"}`) or through
`compound.save`.
