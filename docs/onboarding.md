# Onboarding

A first hour that ends with you having run every component and knowing which one can lose
money.

## The one thing to know first

Four components, three of which are harmless and one of which is not:

| Component | Worst case if you break it |
| --- | --- |
| `backtester/` | A dishonest number. Nobody loses money, but a decision built on it might |
| `research/` | An overstated result |
| `soltui/` | A wrong pixel |
| `extension/` | **A real order for real money** |

Read `CLAUDE.md` before touching anything. It carries the non-negotiables per component and
they are not stylistic — each one is there because the failure it prevents already
happened or was one review away from happening.

## Step 1 — get the Python side running (10 minutes)

```bash
pip install -r backtester/requirements.txt
python3 -m unittest discover -s backtester/tests -t .     # expect 454 OK
```

If that passes, the backtester and research components are healthy. No data needed yet —
the suite uses a synthetic loader precisely so tests need no network.

## Step 2 — fetch data and run a backtest (10 minutes)

```bash
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01
python3 -m backtester.cli --asset SOL --strategy all --split 0.7 --out results/
```

Read the output rather than skimming it. Note that buy-and-hold is in the comparison on
purpose: a strategy that cannot beat it has not earned anything, and the tool is built to
say so.

## Step 3 — ask what the rules say right now (5 minutes)

```bash
python3 research/decide.py --asset SOL --interval 1d
```

Three sections, and the useful lesson is in the disagreements: the same band break reads
bullish to the mean-reversion rule and bearish to the breakout rule. There is deliberately
**no** consensus verdict. If you find yourself wanting one, read
`research/cpcv_sweep.py`'s `interpret()` — it exists specifically to stop the "lots of
strategies agree, so it must be real" conclusion.

Note the header: decision bar, close, checksum, and how stale the data is. That header is
there so the output can be disbelieved.

## Step 4 — the extension, without arming it (15 minutes)

```bash
cd extension
npm test                                              # expect 114 pass
node tools/dryrun.js --ticks 8 --osc 6 --offline 100  # a round trip must close POSITIVE
node tools/cli.js                                     # every command in the registry
```

The dry run is the integration gate. It is the only check that closes a round trip, so it
is the only one that catches a zero-spread regression — the bug where an exit rests at the
level it was bought at, capturing nothing and paying two fees.

Then read three files, in this order:

1. `src/core/commands.js` — the single registry. Three surfaces are thin adapters over it.
2. `src/core/risk.js` — the rails. Note `normaliseState`: rails **fail closed**, because a
   missing or NaN field must not silently disable one.
3. `src/core/engine.js` — reconcile, then plan. The venue is the source of truth; local
   state is a cache.

You may load it unpacked (`chrome://extensions` → Developer mode → Load unpacked →
`extension/`). It installs **disarmed, in dry-run**, and you should leave it that way.

## Step 5 — soltui, if you are on macOS (10 minutes)

```bash
pip install -r soltui/requirements.txt
python3 -m unittest discover -s soltui/tests -t .   # expect 95 OK, ~70s
python3 soltui/soltui-service status
```

Before you install it, read `soltui/README.md`. The packaging traps there have been paid
for once already, and the important one is counter-intuitive: the menu-bar **Quit item
does not stop it** — `KeepAlive` overrides Quit, so the flag file is the real off switch.

## Step 6 — confirm you can verify your own work (5 minutes)

```bash
python3 scripts/check_docs.py
```

That checks the docs against the repo: test counts and retrieval-index paths. It exists
because the docs claimed 250 backtester tests for several commits while the suite had grown
to 454, and nothing caught it.

## Where to read next

| Question | Page |
| --- | --- |
| How is this laid out? | `docs/codebase-overview.md` |
| What does this module do? | `docs/COMPONENTS.md` |
| How do I run X? | `docs/DEVELOPMENT.md` |
| Why is it built this way? | `docs/ARCHITECTURE.md` |
| What is already known to be broken? | `docs/known-issues.md` |
| What leaves the machine? | `docs/external-calls.md` |
| What is actually tested? | `docs/TESTING.md` |
| What can move money? | `docs/SECURITY.md`, `.github/SECURITY.md` |

## Conventions worth absorbing early

- **Comments explain why, not what** — especially where the obvious implementation is
  wrong. MV3 timers, base58 zero bytes, FIFO versus paired-lot attribution, one-bar leaks.
- **Python is stdlib-first**, 3.13, with `from __future__ import annotations`. Do not add a
  dependency for something `urllib` or `unittest` covers.
- **JavaScript has zero runtime dependencies**, and that is a hard rule, not a preference.
- **A new strategy ships its card in the same commit.** The card's numbers are checked
  against the code in both directions.
- **Any change to signal generation or fill timing needs a test that would catch a one-bar
  leak.**
