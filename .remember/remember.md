# Handoff — 2026-08-04

## State: all merged to master, local only (no remote)

`python3 -m unittest discover -s backtester/tests -t .` → **119 OK**
`python3 -m unittest discover -s soltui/tests -t .` → **93 OK**
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
