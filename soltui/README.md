# soltui — SOL strategy console

A five-tab Textual TUI plus a macOS menu-bar indicator over the backtester.
Structured like `~/dev/net-dns-monitor`: pure, tested logic modules with a thin
wiring shell.

> **Dry run only.** There is no order path in this package — no keys, no signing,
> no venue client, not even unreachable code. Every figure it shows is a
> historical simulation or a replay of one. See [Safety](#safety).

## Install and run

```bash
cd /Users/mitch.hudson/dev/solmargintrader
pip install -r soltui/requirements.txt

python3 -m soltui.tui     # the five-tab console
python3 -m soltui.app     # the macOS menu-bar indicator (needs rumps)
```

The TUI needs price data. If a sweep reports "no data", fetch it:

```bash
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01
```

## The menu-bar indicator

`status.build_title()` is a pure function, so what the bar shows is tested
without a macOS event loop. What you see, and why:

| State | Title | Why this and not something else |
|---|---|---|
| Idle | `◦ SOL: idle` | |
| Sweeping | `⟳ SOL: backtest 340/630` | While work is in flight, "how much is left" is the live question |
| Finished | `✓ SOL: last backtest +9.4%` | **"last backtest" is load-bearing** |
| Dry run open | `▷ SOL: paper +2.1% (12 fills)` | **"paper" is load-bearing** |
| Failed | `✕ SOL: error — no data` | Failures must be visible, not silent |

**Why every number carries a word.** A bare `+9.4%` in a menu bar reads, at a
glance, as *my money is up 9.4% right now*. There is no live account here. So the
source is always in the string, and a test asserts that exhaustively across every
phase rather than trusting review. If you add a phase that can show a percentage,
that test will fail until you label it.

Long titles clip from the **head**, never the tail, because the figure is at the
end — an earlier version clipped the tail and silently ate the number the
indicator exists to show. Its test is `test_clip_preserves_the_number_not_the_label`.

## The tabs

| Tab | What it does |
|---|---|
| **Settings** | Asset, interval, date range, capital, fees, fill delay, CPCV geometry. Saved to `~/.config/soltui/`. Validation refuses look-ahead (`fill_delay < 0`), a `k >= blocks` split, and any non-dry-run mode. |
| **Strategies** | Every registered strategy on the left, your roster on the right. Add with params (`fast=20 slow=50`). Validation happens **on add** — an unknown name fails with the valid list, bad params fail at the form, not mid-sweep. |
| **Signals** | Read-only reference: each indicator's actual equation as implemented in `backtester/core/indicators.py`, plus what each family is for and *when it fails*. |
| **Backtest** | Runs the roster through CPCV on a worker thread. Shows median path Sharpe, **IQR**, **% paths positive**, median return, trades. Cancellable. |
| **Execute** | Dry-run replay. Step a simulation bar by bar and see the fills a strategy *would* have made. |
| **Queue** | Starts and reads the low-priority background sweep. Start/Stop/Refresh, a live status line, a ranked table and a below-the-floor table. |

### The Queue tab — a sweep you interrupt, not one you finish

`python3 -m soltui.bgworker --asset SOL` grinds through parameter space in a
separate process at background QoS (`taskpolicy -b`, nice 19), so it can run
while you use the machine. The TUI only *reads* what it writes — the sweep keeps
going with the console closed, and resumes where it stopped after a reboot.

Because it is always interrupted rather than completed, the **order** is the
design, not the extent: every strategy card's own published preset is evaluated
before any variation of one, then near variations (0.75x/1.5x), then far
(0.5x/2x). Presets and the promise ordering come from the cards themselves
(`success_likelihood`, per-horizon presets), never a copy.

Two tables, and the split is the point. Ranking is out-of-sample CPCV median
Sharpe; anything under the 10-trade evidence floor is **listed but never
ranked**, because a Sharpe from three trades sorted descending is a ranking of
luck. The status line reports how many rows are *rankable*, not how many were
evaluated — the second number flatters the sweep.

```bash
python3 -m soltui.bgworker --plan --asset SOL      # what it would run, in order
python3 -m soltui.bgworker --asset SOL --max-tier 0  # presets only
```

Inspect it while it runs: `~/.config/soltui/bg/` holds `results.jsonl` (one JSON
object per job), `state.json` (progress) and `worker.log`.

### Read the Backtest tab correctly

Median Sharpe alone is not the answer. A median of `+0.5` with an IQR of `1.4`
straddles zero heavily, and `% paths positive` below ~70% means the sign of the
result depends on which regime you happened to sample. Both columns are shown for
that reason. The measured PBO for this strategy set is 0.43–0.46 against a 0.500
pure-noise control — so treat *ordering* as weakly informative at best, and read
the distribution.

## Safety

`CLAUDE.md` for this repo states: dry-run is the default, the extension installs
disarmed, and *"never change a default so that a fresh install can place an
order."* This package holds to that:

- **No order path exists.** Not stubbed, not disabled — absent. `grep` the package
  for a venue client and you will find none.
- **`config.MODES` contains only `dry-run`.** A config selecting `live` is refused
  by `validate()` with an explanatory error.
- **`armed` cannot be inherited.** Setting it requires an explicit second
  acknowledgement flag, so an old config file cannot silently arm a future build.
  Nothing in this build reads `armed` for anything.
- **The Execute tab is a replay, not a live loop.** Stepping bars and computing
  fills would create a *second* order-execution path alongside
  `backtester/core/engine.py`, outside the coverage of the engine's known-answer
  tests, and the two could diverge into wrong money. Instead `paper.py` runs the
  tested engine once and exposes a cursor over the result.
- `summary()["live_orders_placed"]` is structurally always `0`, and a test asserts
  it so a regression is loud.

Adding live execution later means routing through
`extension/src/core/commands.js` and its risk rails as separate, explicit work —
not extending this package.

## Tests

```bash
python3 -m unittest discover -s soltui/tests -t .        # 61 tests
python3 -m unittest discover -s backtester/tests -t .    # 119 tests
```

The TUI tests mount the real app through Textual's `run_test()` headless harness
and click real buttons, so a crash-on-mount is caught rather than shipped. Two
genuine bugs were found this way: a timer that queried a widget during teardown
and took the app down with it, and the title-clipping bug above.

## Layout

```
soltui/
  status.py    pure: AppState, build_title(), build_menu_summary()
  config.py    pure: Settings, validate(), load/save
  roster.py    pure: Roster add/remove, validated against the strategy registry
  paper.py     pure: PaperSession replay cursor over one backtest
  runner.py    worker thread: roster -> CPCV rows, progress for the indicator
  tui.py       Textual app, one tab per pane (presentation only)
  bgqueue.py   background sweep: job list, ordering, file contract, leaderboard
  bgworker.py  the background sweep process itself (python3 -m soltui.bgworker)
  bgcontrol.py spawn/stop the worker; the liveness lock
  app.py       rumps menu-bar shell (wiring only, lazy rumps import)
```

Anything that makes a decision lives in the top five. `tui.py` and `app.py` are
deliberately dumb, which is what lets the logic be tested without a terminal or a
macOS event loop.
