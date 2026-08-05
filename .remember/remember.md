# Handoff — 2026-08-04

## State: all merged to master, local only (no remote)

`python3 -m unittest discover -s backtester/tests -t .` → **228 OK**
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
