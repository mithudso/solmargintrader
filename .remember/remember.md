# Handoff — 2026-08-04

## State: all merged to master, local only (no remote)

`python3 -m unittest discover -s backtester/tests -t .` → **250 OK**
`python3 -m unittest discover -s soltui/tests -t .` → **95 OK**
`python3 research/verify_numbers.py` → **exit 0**, 795 figures verified

## soltui menu-bar app — installed and running at login

Bundle `~/Applications/SolTUI.app`, agent `~/Library/LaunchAgents/com.mitchhudson.soltui.plist`.
Verified: launchd `state = running`, clean log, and the flag-file off switch works both ways.

```bash
python3 soltui/soltui-service status     # bundle / agent / flag / launchd state
python3 soltui/soltui-service stop       # removes the flag -> launchd stops supervising
python3 soltui/soltui-service start      # recreates it -> starts, and starts at login
python3 soltui/soltui-service build      # rebuild after moving the repo
```

**The flag file is the real off switch**, not the menu-bar Quit item — `KeepAlive`
necessarily overrides Quit, so removing `~/Library/Application Support/soltui/supervise.enabled`
is how you actually stop it.

### Packaging traps already paid for (do not re-learn)

- **Alias build (`py2app -A`), so the bundle references `/Users/mitch.hudson/dev/solmargintrader`.**
  Rebuild if the repo moves. A full freeze would have to embed pandas/numpy.
- **Never install a bundle built from a worktree.** `.claude/worktrees/` gets deleted and login
  startup breaks silently. `soltui-service install` refuses the target and warns on the source.
- **py2app runs its target as a top-level script**, so `app.py`'s relative imports failed.
  `menubar_launcher.py` exists for that, and also `chdir`s to the repo because a Finder/launchd
  launch starts at `/` and `data_dir="data"` would miss.
- **A py2app "Launch error" dialog keeps the process ALIVE.** Checking liveness alone reports a
  broken bundle as working — assert the stderr log is empty instead.
- **No `RunAtLoad`.** It starts the app at every login regardless of the flag, so `stop` silently
  undoes itself.
- **launchd provides no `LANG`**, making the locale US-ASCII; the status glyphs are non-ASCII.
  Set in the agent, the bundle plist, and the launcher.

## Signals tab is editable

`soltui/signals.py` holds every indicator tunable. Precedence: **signal defaults fill only what
was not pinned explicitly in the Strategies tab** — explicit always wins. `STRATEGY_PARAM_MAP` is
explicit, not name-inferred, with tests asserting every registered strategy is mapped and every
mapped strategy actually constructs from its merged params.

## Menu-bar app: installed, running, with the tree-of-life icon

Bundle `~/Applications/SolTUI.app`, agent `com.mitchhudson.soltui`. Icon generated from code by
`soltui/make_icon.py` (a tree whose three roots ARE the Solana mark) so it is reviewable and
regenerable rather than an opaque binary.

```bash
python3 soltui/soltui-service status | start | stop | build | install
```

### Icon design note

Driven by the **16px** size, not 1024. First attempt failed there: bare recursive branches are
sub-pixel at 16px and vanished, leaving a stick above three bars. What fixed it — a FILLED canopy
of overlapping lobes (solid silhouettes survive downscaling), branch texture **carved out** rather
than drawn on (subtractive detail fades gracefully; additive hairlines become grey noise), a short
thick trunk, and a root flare tying trunk to bars. Verified by rendering 16/32/64px and looking.

### The install race — do not "simplify" reload_agent()

`launchctl bootout` is **asynchronous**. Issuing `bootstrap` immediately after races it, fails with
"try re-running as root", and leaves the agent UNLOADED while install reports success. This was
caught only because a reinstall silently stopped starting the app at login. `reload_agent()` polls
for each step to take effect and returns False if the agent does not end up loaded.

## cdo pass — four real defects found and fixed

Static patterns were clean. These came from probing behaviour:

1. `pbo_cscv`'s `max_splits` cap took the FIRST N combinations; `itertools` emits lexicographically
   so those share low-index blocks — a biased PBO. Now strides evenly, still deterministic.
2. The install race above.
3. `SweepRunner` left `done`/`total` set after a failure, so a later phase change could show
   progress for a sweep that died. `_fail()` clears it.
4. The error title elided its middle into unreadable fragments (`✕: …or — no data —…`). Same class
   as the earlier activity bug: **cap variable-length text BEFORE composing the title**, never let
   `_clip` handle it. Full text lives in the menu summary.

## Cross-session integration

Master also received `worktree-signals-concept-map` (strategy cards, ladder-grid simulator, nine
new strategies). Combined state verified green: **25 REGISTRY strategies, all mapped in
`STRATEGY_PARAM_MAP`, all with a family**, so the editable Signals tab covers them. Backtester
suite is now 228 tests.

## Latest sweep: all 25 strategies under CPCV

1,287 configurations (75 singles + 1,002 pairs + 210 triples), 28 paths each.
`python3 research/cpcv_sweep.py` reproduces it; 870 figures in the docs are verified against the
CSVs by `verify_numbers.py`.

| | short | medium | long |
|---|---|---|---|
| Singles PBO | 0.343 | **0.700** | **0.700** |
| Pairs PBO | 0.229 | **0.650** | **0.650** |
| Triples PBO | 0.086 | **0.886** | 0.543 |

**Short horizon: 0 of 25 singles has a positive median path Sharpe.** Daily horizons are all
*above* the 0.500 noise line, i.e. in-sample rank is anti-informative.

### The one result worth defending carefully

Growing the search 16 -> 25 moved singles PBO 0.457 -> 0.700, which reads like a clean
multiple-testing effect. It is not clean. Adding the 250-bar-window strategies (OU, Hurst,
vol-regime) shrank the common CPCV block set from 7 to 6 (they cannot warm up before block 1), so
two variables moved together. Holding blocks fixed:

    medium: 16cfg/7blk 0.457 -> 16cfg/6blk 0.600 -> 25cfg/6blk 0.700   (search: +0.100)
    long:   16cfg/7blk 0.457 -> 16cfg/6blk 0.550 -> 25cfg/6blk 0.700   (search: +0.150)

Search size is real but is only a third to a half of the move. **Do not re-simplify this into
"more configs -> higher PBO".**

### New leaders, all previously spec-only or untested

`hurst_switch` (medium +0.699, 93% of paths positive), `obv_trend_60` (long +0.774, 81%),
`vol_regime` (long +0.696, 80%). Buy-and-hold is 2nd at medium and 3rd at long — and the rows
ahead of it are separated by less than their own IQR.

Best figure anywhere: `all(dual_momentum+vol_regime)`, long, median Sharpe **+1.345** on
**+75.1%**. It tops a 295-configuration search with PBO 0.650, so it is precisely the row not to
trust. That tension is the finding, not a caveat on it.

### Two traps this sweep re-taught

- **`vol_regime` was 16.02s per hourly backtest** (100x its peers) because `on_bar` rebuilt ~230
  realised-vol values per bar. `indicators.rolling_realised_vol()` vectorises it to 0.56s, proven
  equivalent to 0.0 absolute difference. The slow path was invisible from the results — only from
  the clock.
- **Strategy cards and `research/sweep.py` must agree exactly**, enforced by
  `test_presets_agree_with_the_sweep_grid`. Adding strategies to the sweep without card presets
  breaks it, correctly. Generate presets FROM the sweep; the test compares floats and ints
  strictly (25.0 != 25).

## Perturbation stability check (research/perturb.py)

Answers a narrower question than it appears to: **were the PARAMETERS cherry-picked?** It nudges
each parameter ±10% one at a time, re-runs the full CPCV evaluation, and compares max|Δ median
Sharpe| against the configuration's **own path IQR** — not an absolute threshold.

One-at-a-time on purpose. A joint grid *is* a parameter search and would reintroduce the very
selection bias the documents warn about.

### Result on `all(dual_momentum+vol_regime)` (the best figure anywhere, +1.345)

- **0 of 12 perturbations flip the sign;** the median never drops below +0.904.
- Ratio 0.44 on parameters alone, 0.50 with geometry — **mid-pack**, not exceptional.
- **The largest single move came from the CPCV geometry** (8→9 blocks, −0.441), bigger than any
  strategy parameter (worst −0.392). The result is more sensitive to how you slice the data than
  to the strategy's own settings. That was not the expected answer.
- Across seven top configurations and 59 perturbations, **not one flipped sign**.

Reference population for the ratio (recorded as `REFERENCE_*` in perturb.py so the verdict compares
against something measured): **0.13–0.72, median 0.44**.

### Do not over-read this

Perturbation stability and multiple testing are **different failure modes**. Passing this says the
parameters were not cherry-picked. It says nothing about whether the *configuration* was
cherry-picked from 295 candidates — **PBO 0.650 says that concern stands undiminished**. A robust
row at the top of an anti-informative ranking is still a row chosen by an anti-informative ranking.

### Two traps hit while wiring this up

- The first `PERTURB_ROW` regex collided with the single-split pair tables (identical 4-column
  shape) and produced three false failures. Fixed by scoping the match to the finding-1d section.
- The calibration table quoted numbers from an in-session heredoc run with **no CSV behind them**,
  so `verify_numbers.py` correctly refused them. Re-ran those six configurations through the CLI to
  leave durable evidence. 877 figures now verified.
- zsh does **not** word-split unquoted `$var`, so a `for spec in "--pair a b --mode any"` loop
  passes the whole string as one argument and every run fails silently.

## All-25 perturbation stability (72 configs, 329 perturbations)

`python3 research/perturb.py --horizon <h> --all-singles`

| Horizon | ratio min | median | max | sign flips |
|---|---|---|---|---|
| Short | 0.11 | 0.26 | 0.78 | 1/111 |
| Medium | 0.04 | 0.14 | 0.86 | 21/110 |
| Long | 0.06 | 0.17 | **1.33** | 13/108 |

1. **Singles median ratio 0.21 vs top pairs 0.44 — combining ~2.6×'s parameter sensitivity.**
   PBO said combining makes overfitting worse; perturbation says it makes the parameter choice
   matter more. Two independent methods, same direction. That is the strongest form of the
   "don't combine signals" conclusion in this repo.
2. **`bb_reversion` and `zscore` (long) are the two most fragile of all 72, both 1.33 — the only
   two above 1.0.** Same pair already proven from source to be ONE mechanism. **Three independent
   flags now:** the algebra, the 46-point natural experiment, the highest perturbation ratio.
3. **`obv_trend` is the standout** — long median +0.774 (best single anywhere), 81% of paths
   positive, ratio 0.13, 0 sign flips, only 2 perturbable params. Meanwhile the medium leader
   `hurst_switch` (+0.699, 93% positive) sits at ratio 0.60, near the top of the distribution.
   **Performance and robustness are different axes; the ranking shows only one.**

Spearman(median Sharpe, ratio): −0.045 long, −0.152 medium, **+0.328 short**. Long/medium
uncorrelated (benign). Short is the bad direction — better performers are less stable, so that
ranking partly selects parameter luck.

### Watch out

- `REFERENCE_*` in perturb.py is **split by configuration type** (`single` median 0.21, `combo`
  median 0.44) because I originally applied the pairs reference to singles and mis-calibrated every
  verdict. Do not re-merge them.
- The check answers "were the PARAMETERS cherry-picked". It says **nothing** about whether the
  CONFIGURATION was cherry-picked from hundreds — PBO answers that, and at 0.650 the concern stands.
- `buy_and_hold` is skipped: no parameters to perturb, which is its own kind of robustness.

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

### Update — strategy cards (commits `4073576`, `bc9fe2b`)

**43 cards under `backtester/strategy_cards/`**, one self-contained file per strategy or
signal: 17 measured (the 16 registered strategies + the resting-ladder grid) and 26
spec-only from `research/STRATEGIES.md` Tier 2. Each carries equations, a code pointer,
why it might work, how it fails, backtest caveats, measured numbers where they exist, and
machine-readable params with defaults and per-horizon presets.

`python3 -m backtester.core.strategy_cards` prints the inventory. No committed index
table — it would drift on the next card.

**The loader is `core/strategy_cards.py`** and parses a strict YAML subset **by hand**
(pyyaml is deliberately absent from requirements.txt). It refuses everything outside the
subset: block sequences, deeper nesting, nested flow collections, tabs, duplicate keys,
non-finite floats, trailing `#` comments, unknown fields, unknown param keys, and a
`type:` that disagrees with its default.

**What makes a card a contract and not a claim:** `tests/test_strategy_cards.py` (31
tests) checks registry drift **in both directions**, every declared default against the
constructor's actual default, `warmup_bars` and `family` against the code, every preset
against `research/sweep.py`, and constructs + backtests every buildable card. Prose in a
card can still be wrong; a number cannot.

**Schema notes worth remembering.** `kind` discriminates `exposure-strategy` from
`ladder`, because the ladder grid is implemented but has **no registry key** — it is not
a `Strategy`. So `implemented` keys off `runner`, and `buildable` off `registry_key`.
A param declares **either** `default:` **or** `required: true`, never both:
`GridConfig` gives `lower`, `upper`, `rungs` and `notional_per_rung_usd` no default, and
an earlier draft invented four. `data_required` / `data_available` are frontmatter so an
agent can filter without reading English — `implementable_today()` returns the **9** of
26 spec-only mechanisms needing no new data source.

**Two bugs the /cdo review caught that the suite could not see:** the ladder card's
declared defaults were verified against nothing (no registry key → never in the drift
map), and two cards claiming one `registry_key` silently shadowed each other, which was
mutation-proved by giving `macd` a wrong default that passed every test. Both fixed, both
now covered.

**Highest-value spec cards, by the reference's own reckoning:** `hurst_regime_test`
(a meta-signal selecting trend vs reversion — attacks the failure dominating all 16
measured results), `ou_half_life_sizing` (the missing hold cap in both reversion cards),
`atr_position_sizing`, and `funding_utilization_extremes` (on Jupiter there is **no
funding rate** — the signal is pool *utilization*, which would also improve every
leveraged backtest here). `jlp_vs_sol_relative_value` is the cheapest blocked item to
unblock: Jupiter's own Price API can supply the JLP mint.

Counts now: **153 Python, 110 JS** (263 total).

### Update — nine strategies implemented, all cards rated, Jupiter labelling (commit `019da89`)

**The nine spec cards whose gap was "code, not data" are now implemented and measured**
in `core/strategies/advanced.py`, on the real 1,875-bar SOL daily series with the same
70/30 split as every existing card. `buy_and_hold` reproduces its documented
IS +565.2% / OOS −70.8% exactly, which is how the new numbers are known to be
comparable to the old ones.

| strategy | OOS return | OOS Sharpe | trades |
|---|---|---|---|
| **hurst_switch** | **+15.6%** | **+0.564** | 10 |
| ou_reversion | −1.5% | +0.092 | 6 |
| atr_sized | −2.6% | −0.454 | 93 |
| ichimoku | −33.3% | −0.531 | 11 |
| vol_regime | −21.2% | −0.377 | 15 |
| garch_voltarget | −30.8% | −0.551 | 50 |
| adx_trend | −43.6% | −1.165 | 8 |
| ma_ribbon | −54.0% | −1.242 | 160 |
| dual_momentum | −65.3% | −1.303 | 37 |

**`hurst_switch` is the result worth remembering.** The research doc predicted before
any code existed that a regime selector would be the highest-value unimplemented item,
because trend and reversion invert between regimes and nothing else checks which is
present. It then made money out-of-sample through the leg that cost buy-and-hold 70.8%.
Ten trades is exactly the evidence floor, so it is "worth the next experiment" (CPCV),
not "works". It is the only card rated **moderate on measured evidence**.

Also notable: `garch_voltarget` landed within 0.3pp of `voltarget` (−30.8% vs −31.1%),
which says the lag in the volatility estimate was **not** what made vol-targeted trend
following lose here — the direction call was, and both share the same crude SMA gate.

**Ichimoku's displacement was the real implementation trap.** The cloud sitting at the
current bar was computed `displacement` bars ago, so reading it as current reads 26 bars
of future data. The implementation slices history to what was visible then, and a test
asserts the value used *differs* from the full-history cloud.

**Every card now carries `success_likelihood` + `success_basis`,** enforced by the loader
and by five tests. Scale is `very-low | low | moderate` — **no `high`**, because 14% of
311 rankable configurations had a positive OOS Sharpe and 9% made money. One test caps
`moderate` at a tenth of all cards, so the ratings cannot drift into marketing.
Distribution: 20 very-low, 21 low, 2 moderate (`hurst_regime_test`,
`pairs_cointegration`).

**The 17 remaining spec cards stay spec-only** — options surfaces, L2 depth, on-chain
flows, tick prints, OI history, a peer universe. `pairs_cointegration` and
`jlp_vs_sol_relative_value` are the cheapest to unblock (Coinbase serves BTC/ETH
keyless; Jupiter's Price API serves the JLP mint).

**Licence labelling is done.** `extension/src/jupiter/attribution.js` is the single
source for clause 8.4's exact "Powered by Jupiter" string and clause 2.3's
name-the-API requirement. Clause 2.3 is written around "Jupiter Ultra" and "Metis" and
this extension uses **neither** — Trigger V2 for orders, Price v3 for marks, no swap
router — so the label says exactly that rather than claiming the closest-looking name.
`SURFACES` imports the real base URLs, and four tests fail if an API is called without
being labelled.

Counts: **189 Python, 114 JS** (303 total).

### Update — merged to master; pairs + JLP cards unblocked

**Everything is on `master` now** (merges `e3b1701`, `14b6444`, `f8be140`). No remote, so
nothing is pushed. `chore/repo-bootstrap-and-surfaces` is gone — other sessions merged it
and moved to master, which advanced **four times while I was merging**, so the merge went
in as merge commits rather than fast-forwards. Nothing was lost either way: verified by
checking their reference commits are still ancestors after each merge.

**Two integration failures caught by tests at the boundary, both legitimate:**
1. `soltui`'s `test_every_registered_strategy_is_mapped` failed because my nine new
   strategies weren't in `STRATEGY_PARAM_MAP`. Wired them in with fields, groups and
   validation. Their test, my omission — the same drift discipline the cards use.
2. My `test_presets_agree_with_the_sweep_grid` failed because *they* added my nine
   strategies to `research/sweep.py` HORIZONS while my cards said `presets: {}`. Copied
   the presets **from** sweep.py so both describe one experiment. Note their short/long
   scalings differ from the defaults I measured at, so the measured numbers on those
   cards are medium-horizon and labelled as such.

Also: another session vectorised my `vol_regime` realised-vol loop (16.02s → 0.56s,
commit `3ebb34d`). Worth knowing that per-bar recomputation of a rolling distribution was
the bottleneck.

## pairs_cointegration — unblocked and MEASURED

Coinbase serves BTC-USD and ETH-USD keyless via the existing fetcher, so both were
fetched (1,875 daily bars, aligned with SOL). `core/cointegration.py` (ADF +
Engle-Granger, MacKinnon table, **no statsmodels**) and `core/pairs.py`, run through
`backtester.paircli`.

| Peer | ADF | Cointegrated 5% | OOS trades |
|---|---|---|---|
| ETH | −3.127 (p≈0.032) | **Yes** | 0 |
| BTC | −2.648 (p≈0.087) | No | 0 |

**The finding is the gate, not the return.** Disable it (`--no-cointegration-gate`) and
the ETH pair takes 2 out-of-sample trades and loses **−24.70%**. With it on: no trades,
no loss. That is exactly what `zscore` lacks — it applies a stationarity-dependent method
to non-stationary raw price and bought dips through the same window.

Caveat that bounds the whole card: exposure is **single-asset long SOL**; the peer is a
signal input, not a shorted leg. This is not the dollar-neutral pairs trade the
literature describes, and this harness cannot express one.

## jlp_vs_sol_relative_value — status `implemented`, deliberately not measured

What was actually checked: **Coinbase does not list JLP-USD**; Jupiter Price v3 serves
its *spot* price keyless ($3.5933); `datapi.jup.ag` charts is unreachable. So my earlier
card was right about price and **wrong about history** — it cannot be fetched
retroactively from anywhere reachable.

`core/archive_price.py` accumulates it forward instead: append-only, refuses a
non-positive price rather than writing a zero, warns while too short to backtest. Seeded
with one row. Schedule it if the series is wanted.

**This required a third card status.** `implemented` = code exists and is tested, no data
to run it on. Collapsing it into `spec-only` hides working code; into `measured` invents a
result. The loader enforces `evaluation: null` and forbids citing `measured-oos`.

Counts: **250 backtester, 114 extension, 95 soltui**. Cards: 27 measured, 1 implemented,
15 spec-only.

### Update — hurst_switch under CPCV: the pre-registered bet held

Full run for all 25 registered configurations is tracked at
`research/results/cpcv_all25_1d.csv` (SOL 1d, checksum `b68858b5deef2e35`, 1,875 bars,
8 groups, k=2). Merged to master as `f091942`.

**hurst_switch ranks 1st of 25 by median path Sharpe.**

| | hurst_switch | buy_and_hold | zscore |
|---|---|---|---|
| Median path Sharpe | **+0.699** | +0.534 | +0.036 |
| Q1 path Sharpe | **+0.609** | −0.095 | −0.539 |
| Paths positive | **93%** | 68% | 52% |
| Median path return | **+16.7%** | +9.4% | −10.0% |
| Trades | 24 | 16 | 50 |

It and `ou_reversion` are the **only two of 25 with a positive 25th-percentile path
Sharpe**. Per-block Sharpes: +0.86, +2.67, 0.00, 0.00, +0.99, +0.29 — **no negative
block**. Adding it to the set **lowered PBO** (0.600 → 0.400 on the six common blocks),
so it is not the artifact in-sample selection latches onto.

**Rating HELD at moderate, not raised.** 24 trades across six blocks, two of which
traded zero times — those 0.00 Sharpes are "never lost", not "usually won", which
inflates the 93%. Block 3's +2.669 rests on **two trades**. Next step is more data
(hourly, or a peer universe), not more confidence.

**Two PBO gotchas for whoever runs this next.** `pbo_cscv` requires every config to
expose the *same* block count, and the 251-warmup strategies (hurst/ou/vol_regime) only
get 6 usable blocks against 7–8 for the rest — so intersect on common block indices or
it raises. Doing that leaves only 20 CSCV splits, which is why my PBO levels (0.600/0.400)
sit above the prior study's 0.429–0.457; read the *direction*, not the level.
Also `BlockResult` has no `.sharpe` — use `cpcv._sharpe(b.returns, ppy)`.

**Six cards re-rated, in both directions** (the table is in
`backtester/strategy_cards/README.md`): `ou_half_life_sizing` low→**moderate**;
`bb_breakout` very-low→**low** (3rd of 25 — its notorious single-split decay was
split-dependent); `zscore` low→**very-low** (the old top-ranked row is a coin flip whose
median path loses 10%); `adx_filtered_trend` held at low despite a positive CPCV median,
because Q1 is −0.603 with the widest spread of any config; `vol_regime_hmm` confirmed
very-low; `pairs_cointegration` had already gone moderate→low on measurement.

**The comparison worth keeping:** hurst_switch conditions on **serial correlation** and
ranks 1st; vol_regime conditions on **volatility level** and ranks near the bottom. Same
"pick the regime, then pick the rule" idea — the regime variable is the whole difference.

Distribution now: 20 very-low, 21 low, 2 moderate.

### Update — hourly test kills the hurst_switch result

`research/results/cpcv_all25_1h.csv` (SOL 1h, checksum `704dd982c4e810a0`, 8,823 bars,
`allow_gaps=True` as sweep.py uses, 8 groups k=2, all 25 configs built from each card's
**short** preset). Merged as `0ad8b55`.

**hurst_switch: 1st of 25 on daily → 23rd of 25 on hourly.**

| | daily | hourly |
|---|---|---|
| median path Sharpe | +0.699 | **−3.123** |
| Q1 | +0.609 | −3.878 |
| paths positive | 93% | 14% |
| median return | +16.7% | −12.8% |
| trades | 24 | 170 |

Seven times the trades, rank inverted from best to third-from-last. **Downgraded
moderate → low.** The moderate rating was conditional in writing on surviving the next
experiment; it didn't.

**The confound, stated because it matters but doesn't rescue it:** the hourly file is
only 2025-08→2026-08, **zero of 25 configs** had a positive median path Sharpe over it,
and buy-and-hold lost 22.9%. So "everything lost" is partly the period. But rank is
period-invariant — same bars for everyone — and this one moved from first to nearly last
*relative to its peers*. The repo's headline finding (in-sample rank doesn't predict
out-of-sample rank) now also holds **across horizons**, which is worse.

**`ou_half_life_sizing` is now the only moderate.** 4th of 25 daily, **2nd of 25
hourly**, median path return −3.4% vs buy-and-hold's −22.9% on 196 trades. Rank
stability across a change of scale is the closest thing to evidence this repo has
produced. Next test should be a different asset or a peer universe, not more SOL.

**A degeneracy worth remembering:** on hourly, `voltarget`, `garch_voltarget` and
`sma_regime` returned **numerically identical** rows (median −2.282, −19.9%, 292 trades).
At `target_vol` 0.8 on hourly SOL the vol cap binds every bar, so `min(1, target/sigma)`
= 1.0 and both vol-targeted rules collapse into the shared trend gate. Three "separate"
strategies, one row — a sweep's configuration count overstates how many distinct ideas
it contains.

Distribution: 20 very-low, 22 low, 1 moderate.

### Update — BTC/ETH sink the last moderate; the dataset outranks the strategy

`research/results/cpcv_all25_btc_eth_1d.csv` (BTC checksum `3042b33a202fe8ef`, ETH
`52c7bb3220d1e59a`, 1,875 bars each, medium preset, 8 groups k=2). Merged as `f66e7d4`.

**`ou_half_life_sizing` downgraded moderate → low.** Four independent tests:

| dataset | rank | medSh | Q1 | %pos | medRet | **trades** |
|---|---|---|---|---|---|---|
| SOL daily | 4/25 | +0.412 | +0.213 | 93% | +10.5% | **26** |
| SOL hourly | 2/25 | −0.595 | −1.296 | 33% | −3.4% | **196** |
| BTC daily | **1/25** | +1.657 | **+0.000** | 60% | +12.0% | **6** |
| ETH daily | **18/25** | +0.012 | −0.323 | 53% | +0.0% | **18** |

Read trades against rank: **every good result has a tiny trade count, and the one test
where it traded properly it lost.** BTC's rank-1 is six trades with Q1 exactly 0.000 (the
conservative quarter of paths did nothing). That is a filter, not an edge. Its real use —
bounding the hold on `bb_reversion`/`zscore` — remains untested.

**NO CARD IS RATED MODERATE NOW** (20 very-low, 23 low). Both cards that ever held it lost
it to the experiment the rating was explicitly conditional on. That empty tier is the
result.

hurst_switch: 13th of 25 on BTC, 19th on ETH (4 trades, 0% of paths positive) — confirms
its downgrade.

### The finding worth carrying forward

Configurations with a positive median path Sharpe, per dataset:

| dataset | positive | buy-and-hold medRet |
|---|---|---|
| BTC daily 2021-06→2026-08 | **25 of 25** | +25.6% |
| ETH daily same window | 18 of 25 | −6.3% |
| SOL daily same window | mixed | +9.4% |
| SOL hourly 2025-08→2026-08 | **0 of 25** | −22.9% |

**The dataset explains far more than the strategy does.** On BTC every mechanism
"worked"; on the SOL hourly year not one did. Any ranking computed inside one dataset is
mostly measuring that dataset — the single-split critique, one level up. Before trusting
any future ranking here, check how many configs are positive in that dataset overall; if
it's 25/25 or 0/25, the ranking is about the market, not the mechanisms.

### Update — the ladder grid on real SOL, for the first time

`research/results/ladder_grid_sol.csv`. Merged as `54dd41a`. This is the strategy the
extension would actually place orders with; until now it had only run on synthetic bars.

**Bounds came from the extension's own convention** (`tools/dryrun.js`: 0.85×–1.15× of
price, 7 rungs, $12/rung), never from hindsight. P&L is against *deployed* capital, the
denominator `extension/README.md` already uses.

**One static ladder, whole series**

| | daily | hourly |
|---|---|---|
| realized | **+$7.51 (+10.4%)** | −$14.37 (−20.0%) |
| round trips | 68 | 36 |
| **bars outside ladder** | **93.1%** | **86.0%** |
| grid ret / maxDD | +5.21% / **−11.46%** | −9.98% / −18.68% |
| hold ret / maxDD | +88.25% / **−96.27%** | −57.12% / −75.80% |

**Re-centred per block** (8 blocks, ladder reset from each block's first close):
daily median **+7.5% of deployed capital, 5/8 positive**, beat hold 4/8 (hold median
−1.2%), worst block **−22.5%**; hourly median −1.2%, 3/8 positive, beat hold **6/8**
(hold median −16.1%).

The worst daily block ($28–38 ladder while SOL fell 39%, −22.5% of deployed at max
position) lands within a couple of points of the extension's own dry-run figure (−$8.62
on $48), which **cross-checks gridsim.py against grid.js on real data** — the parity that
CLAUDE.md makes a non-negotiable.

**THE PRODUCT FINDING: the extension does not re-centre.** `planGrid` reads `lower`/`upper`
straight from config and nothing recomputes them, so a live install behaves like the
*static* column — idle 86–93% of the time — not the re-centred one that was profitable on
daily. The gap between those two columns is the value of an unbuilt feature, and it is now
named in `extension/README.md` as the highest-value missing one.

Card basis moved base-rate → measured-oos, rating stays **low**: good drawdown profile,
but idle most of the time, hourly negative, the trend failure mode cost 22.5% of deployed,
and the profitable configuration needs re-centring that doesn't exist. Standing constraint
still outranks all of it — **no live order has ever been placed**, the Trigger order-list
envelope is unverified, fee attribution unconfirmed.
---

## Block-count geometry: the long-horizon leaderboard is mostly a slicing artifact

`research/geometry.py` re-ranks all 25 strategies at every CPCV block count from 6 to
12 and asks whether the *ranking* is a property of the strategies or of N. Nobody can
justify 8 blocks over 9 from first principles, so if the leaderboard reshuffles as N
moves, the leaderboard is partly reporting how the series was sliced.

| Horizon | mean pairwise Spearman | median rank move | distinct #1s |
| --- | --- | --- | --- |
| short | **+0.909** | 5 of 25 | 3 |
| medium | +0.772 | 9 of 25 | 4 |
| **long** | **+0.566** | **12 of 25** | **6** |

**The long horizon is much the worst, and that is where every positive result lives.**
Six strategies hold first place across seven block counts. The mechanism: slow
long-horizon parameters generate few trades, so each block's Sharpe is noisy, so the
order reshuffles. Short has 8,823 bars and stays stable.

**Topping the leaderboard is partly a symptom of instability.** Spearman between best
rank achieved and rank movement is **−0.390**; strategies that led somewhere move a
mean of 14.0 places against 11.6 for everyone else. `adx_trend` has the highest median
of all 25 (+0.604) while ranging +0.78 to −0.60 and moving 23 of 25 places — the
clearest example in the document of a number that means nothing. `obv_trend` survives
as the most rank-stable strategy in the set (moves 5 places), which **qualifies finding
1e**: its +0.774 was its value at 8 blocks, the geometry the document happened to use.
PBO is not geometry-invariant either — 0.700 to 0.943 at the long horizon.

## verify_numbers had a silent-pass hole, and it was not in the new code

Adding the geometry checks raised the count 877 → 932. The first run *passed at 877*,
which was the tell: none of finding 1f's figures were being checked, because the
extractor only ever looked numbers up and 1f's figures (median across geometries,
spread, rank movement) exist in no CSV. They are now **recomputed** from the raw
per-block medians.

A blind re-audit then found the larger, pre-existing hole: every check is regex-driven,
so a table whose format drifts stops matching and the run still prints a pass.
**Measured: deleting six CPCV rows took the count 923 → 893 — thirty figures silently
unverified — and the script exited 0.** `EXPECTED_FIGURES` now records the count each
document carries and fails on a mismatch in either direction. Be exact about what it
buys: it detects a *drop* from the recognised set; it cannot detect a figure that was
never recognised. "EVERY PARSED FIGURE MATCHES" carries real weight on "parsed".

Other fixes worth not re-discovering:

* **PBO was matched on block count alone**, so a long-horizon figure could verify
  against a medium run — at 8 blocks both are 0.700. Each is now tied to its horizon.
* **`abs(doc - recomputed) > tol` is False when the recomputation is NaN**, so an
  unrecomputable figure passed silently. Every geometry comparison now rejects
  non-finite.
* **Spread tolerance 0.005 on a 2dp figure is the rounding boundary with no slack** —
  `buy_and_hold`'s spread sits 4e-4 from a false failure. Now 0.0055. The median
  tolerance was the opposite error: 0.005 on a 3dp figure, eight times too loose.
* Two result files covering one horizon were silently merged, keeping whichever sorted
  last; a `--k 3` run would have verified k2 figures.

**The `spearman` duplication docstring overclaimed and is corrected.** Two identical
copies cannot catch a bug that was always in both. What separation prevents is a later
edit to `geometry.py` redefining the thing that checks it; the real independence lives
in `geometry_stats`, which re-derives every figure by a different route than `render()`.

**A contradiction survived every machine check.** 1f said `buy_and_hold` had "the
highest median across geometries (+0.587)" and, two sentences later, that `adx_trend`
had "the single highest median of all 25 (+0.604)". Every figure was correct and
verified; the defect was a comparative claim *about* verified numbers, which the script
structurally cannot catch — it compares prose against results, never prose against
prose. `buy_and_hold` is third of 25; its distinction is the smallest spread, 0.27.

Verification: the refactor was proven safe by regenerating all three horizons and
diffing — **csv, txt and json byte-identical** except the intended `unevaluable`
list→dict change. Each new guard was confirmed to fail on a mutated document.

Counts: **279 Python** (was 263), 95 soltui, 114 JS.

### The blind re-audit found the one that mattered

The `isfinite` guard was added to `compare()` — and `_check_geometry_pbo` does its own
comparison and did not get it. **A NaN in a JSON sidecar meant a quoted PBO was counted
as checked and compared against nothing: 932 figures, exit 0, "EVERY PARSED FIGURE
MATCHES".** `geometry.py` writes NaN whenever it cannot compute PBO for a geometry and
`json` round-trips it, so this was reachable, and the most realistic trigger was an
aborted run leaving a stale `geometry_long_k3.json` sidecar — which `load_geometry`'s
duplicate guard never saw, because that guard is on the CSV glob.

The lesson generalises: **the pure arithmetic was well covered while every function
whose job is *to fail* had no tests at all.** That is exactly why the missing guard
survived two functions away from a comment calling it load-bearing. `_check_geometry_pbo`
and `check_geometry`'s guards now have failure-path tests.

Also closed: the verdict word (`mostly stable` vs `geometry-stable`) was the one cell in
the 1f table a reader acts on and nothing checked it — flipping it to its opposite
passed. It is now re-derived locally from the recomputed statistics, deliberately *not*
by importing `geometry.verdict`. And renumbering the `### 1f.` heading silenced the
preflight, the checks and the coverage guard at once; geometry results with no matching
section is now a preflight failure.

Counts on the merged tree: **304 Python** (backtester; 292 from this work plus master's universe tests), **95 soltui**, **114 JS**.
