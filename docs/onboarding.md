# Onboarding

An offline verification path, followed by optional component setup. Read each execution boundary before running any live command.

## The one thing to know first

Ten components with different failure modes:

| Component | Worst case if you break it |
| --- | --- |
| `ecosystem/` | Incorrect paper orchestration or UI owner control |
| `oracle/` | Mislabelled observations or unverified forecasts |
| `botmanager/` | Incorrect paper account state, evidence or lifecycle ownership |
| `backtester/` | A dishonest number. Nobody loses money, but a decision built on it might |
| `research/` | An overstated result |
| `soltui/` | Incorrect research state or a separately armed manual Coinbase order |
| `extension/` | **A real order for real money** |
| `mongo/` | Wrong derived research records; selected collections are dropped on load |
| `liquidity/` | **Retained live-capable code** — archived, disabled and killed |
| `executor/` | **A real Solana swap for real money** |

Read `CLAUDE.md` before touching anything. It carries the non-negotiables per component and
they are not stylistic — each one is there because the failure it prevents already
happened or was one review away from happening.

## Find current operations first

The [project wiki](ECOSYSTEM-WIKI.md) groups commands, reference, scripts and
strategy guides. For the installed managed suite, begin with `solbot --help` and
`solbot ui status`. Opening or starting the suite is an explicit operation; follow
[managed-suite setup](bot-manager-managed-suite.md) for a fresh installation and
macOS/Linux/Windows differences. Do not replace a running experiment's environment.

## Step 1 — get the Python side running (10 minutes)

```bash
pip install -r backtester/requirements.txt
python3 -m unittest discover -s backtester/tests -t .
```

If that passes, the offline backtester and research tests pass. No data needed yet —
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
(cd extension && npm test)
cd extension
# From this directory:
node tools/dryrun.js --ticks 8 --osc 6 --offline 100  # a round trip must close POSITIVE
node tools/cli.js                                     # every command in the registry
```

The dry run is the integration gate. It is the only check that closes a round trip, so it
is the only one that catches a zero-spread regression — the bug where an exit rests at the
level it was bought at, capturing nothing and paying two fees.

Then read three files from the repository root, in this order:

1. `extension/src/core/commands.js` — the single registry. Three surfaces are thin adapters over it.
2. `extension/src/core/risk.js` — the rails. Note `normaliseState`: rails **fail closed**, because a
   missing or NaN field must not silently disable one.
3. `extension/src/core/engine.js` — reconcile, then plan. The venue is the source of truth; local
   state is a cache.

You may load it unpacked (`chrome://extensions` → Developer mode → Load unpacked →
`extension/`). It installs **disarmed, in dry-run**, and you should leave it that way.

Return to the repository root with `cd ..` before continuing.

## Step 5 — soltui, if you are on macOS (10 minutes)

```bash
pip install -r soltui/requirements.txt
python3 -m unittest discover -s soltui/tests -t .
python3 soltui/soltui-service status
```

Before you install it, read `soltui/README.md`. The packaging traps there have been paid
for once already, and the important one is counter-intuitive: the menu-bar **Quit item
does not stop it** — `KeepAlive` overrides Quit, so the flag file is the real off switch.

## Step 6 — optional derived store and liquidity tests

```bash
pip install -r mongo/requirements.txt
python3 mongo/schema.py --describe
python3 -m unittest discover -s mongo/tests -t .
(cd liquidity && uv sync --extra dev -p 3.13 && .venv/bin/pytest -q)
```

The MongoDB integration tests skip when no server is available. Liquidity's default test
selection excludes live network calls. Read `liquidity/README.md` and `liquidity/CLAUDE.md` for historical context.
The liquidity service remains disabled and killed; onboarding does not install or
reactivate it. Its retained installer can select live mode, so do not run it here.

## Step 7 — confirm you can verify your own work (5 minutes)

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
- **Python is stdlib-first**, 3.13, with `from __future__ import annotations`. Backtester
  uses `unittest`; liquidity has its own web3/httpx dependencies and pytest suite.
- **JavaScript has zero runtime dependencies**, and that is a hard rule, not a preference.
- **A new strategy ships its card in the same commit.** The card's numbers are checked
  against the code in both directions.
- **Any change to signal generation or fill timing needs a test that would catch a one-bar
  leak.**
