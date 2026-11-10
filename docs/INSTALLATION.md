# Installation

The managed paper suite installs the headless manager, research runtime, Oracle and
control room together. See [managed suite setup](bot-manager-managed-suite.md) for
`solbot stack install`, UI discovery, machine health, the Chrome helper, and the
macOS/Linux/Windows comparison.

Other components have separate dependencies. The optional soltui app and liquidity daemon
can each install a persistent macOS launchd service. Test commands below do not install them.

| Component | Install | Persistent? |
| --- | --- | --- |
| `backtester/` | `pip install -r backtester/requirements.txt` | No |
| `research/` | Covered by the backtester's requirements | No |
| `extension/` | Nothing — no npm dependencies (Lightweight Charts is vendored). Load unpacked in Chrome | Browser profile only |
| `soltui/` | `pip install -r soltui/requirements.txt`, optionally install a launchd agent | Optional login service |
| `mongo/` | `pip install -r mongo/requirements.txt`, plus backtester deps | Local MongoDB service managed separately |
| `liquidity/` | `uv sync --extra dev -p 3.13` in its directory | Optional live daemon; separate from installation |
| `executor/` | `uv sync --extra dev -p 3.13` in its directory | No; the API server is started by hand |

## Prerequisites

- **Python 3.13.** Verify with `python3 -V`. CI pins 3.13 and the main Python suites are
  verified against that runtime. Liquidity declares its own Python range in `pyproject.toml`.
- **Node 22.** Verify with `node -v`. Pinned in `.nvmrc`. Ed25519 in WebCrypto and
  `node:test`'s output format both need a recent runtime.
- **Chrome or a Chromium browser**, for the extension.
- **macOS or Linux**, for the headless managed suite. The full SolTUI app and its
  production blind judge retain macOS requirements. Native Windows does not run
  the complete stack unchanged; see the managed suite guide for WSL2 boundaries.

## Backtester and research

```bash
pip install -r backtester/requirements.txt
```

Verify:

```bash
python3 -m unittest discover -s backtester/tests -t .
python3 -c "import backtester.cli; print('imports ok')"
```

Dependencies are minimal on purpose and `pyarrow`, `requests` and `pytest` are deliberately
excluded. Then fetch data, which is the only network step:

```bash
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01
```

`data/` is gitignored, so this is required on a fresh clone and repeatable at any time.

## Extension

There is nothing to install: no npm runtime or dev dependencies, by design. The one runtime library,
Lightweight Charts, is vendored in `extension/vendor/lightweight-charts/`.

```bash
cd extension
npm test
node tools/dryrun.js --ticks 8 --osc 6 --offline 100  # round trip must close positive
```

To load it in the browser: `chrome://extensions` → enable **Developer mode** → **Load
unpacked** → select the `extension/` directory.

**It installs disarmed, in dry-run.** `DEFAULT_CONFIG.mode` is `dry-run` and no default may
ever be changed such that a fresh install can place an order. Leave it that way until you
have read `extension/README.md`'s **Verification status** section — no live order has ever
been placed through this code.

`npm run e2e` loads the unpacked extension in Chrome for Testing and checks the dry-run path
(see `docs/TESTING.md`); it does not verify live orders. Loading it by hand in your own Chrome via
`chrome://extensions` is still how you install it. Do not claim live execution as verified.

### Optional: the local HTTP surface

```bash
export SMT_API_TOKEN="$(openssl rand -hex 24)"
node tools/api-server.js
```

Reads `SMT_API_PORT`, `SMT_API_TOKEN` and `SMT_PASSPHRASE` from the environment. Export values
in the invoking shell and treat the port as trusted-local only. The program does not load
a `.env` file automatically. An empty
`SMT_PASSPHRASE` leaves the session-key vault sealed, which makes full-auto degrade to
approval rather than fail silently.

## soltui

This one installs a launchd agent that runs at login, so read `soltui/README.md` first.

```bash
# The app bundle needs a framework build of Python (Homebrew python@3.13), not uv's standalone CPython
uv venv ~/.venvs/soltui-app -p /opt/homebrew/opt/python@3.13/bin/python3.13
uv pip install -p ~/.venvs/soltui-app/bin/python -r backtester/requirements.txt -r soltui/requirements.txt
~/.venvs/soltui-app/bin/python -m unittest discover -s soltui/tests -t .
~/.venvs/soltui-app/bin/python soltui/soltui-service build    # build the app bundle
~/.venvs/soltui-app/bin/python soltui/soltui-service install  # install bundle + launchd agent
~/.venvs/soltui-app/bin/python soltui/soltui-service status   # bundle / runtime / agent / flag / launchd state
```

Three things to know before you install it:

1. **Never install from a worktree.** `.claude/worktrees/` gets deleted and login startup
   then breaks silently. `soltui-service install` refuses a worktree target and warns on a
   worktree source — run it from the main checkout.
2. **It is an alias build** (`py2app -A`), so the bundle references this checkout by
   absolute path. Move the repo and it breaks; rebuild with `soltui-service build`.
3. **Quit does not stop it.** `KeepAlive` overrides the menu-bar Quit item.

### Verify

```bash
python3 soltui/soltui-service status
```

Expect the launchd state to read `running` with a clean log. A liveness check alone is not
enough: a py2app "Launch error" dialog keeps the process alive, so a broken app can report
as healthy. Read the log.

## MongoDB

```bash
pip install -r backtester/requirements.txt -r mongo/requirements.txt
python3 mongo/schema.py --describe
python3 -m unittest discover -s mongo/tests -t .
```

Schema description works without a server. The integration tests skip when mongod is
unavailable. Follow `mongo/README.md` to start a local server and load data; the loader
rebuilds its selected derived collections and is not a harmless connectivity probe.

## Liquidity

Read `liquidity/CLAUDE.md` and `liquidity/README.md` before live operation.

```bash
cd liquidity
uv sync --extra dev -p 3.13
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/pytest -q
cd ..
```

This installs the CLI into the component's own virtualenv. Offline tests exclude the
`network` marker. It does not start a daemon or load a signing key. Live reads and
`eth_simulateV1` still require network access even when no transaction is signed.

The service installer in `liquidity/scripts/aero-lp-service` defaults to a live daemon;
use its `install --dry-run` option for a simulated service. Installation is a separate
operational choice. Never raise the configured caps or lower `min_net_apr` during setup.

## Uninstall

```bash
python3 soltui/soltui-service stop        # remove the flag file; launchd stops supervising
python3 soltui/soltui-service uninstall   # remove the bundle and the agent
```

Use the subcommand rather than deleting files by hand — it removes the bundle from
`~/Applications`, the `com.mitchhudson.soltui` agent, and the supervise flag together. The
full subcommand set is `build`, `install`, `start`, `stop`, `status`, `uninstall`.

For liquidity, `liquidity/scripts/aero-lp-service kill` stops on-chain actions and
`liquidity/scripts/aero-lp-service uninstall` removes its agent. Preserve the state and
ledger for reconciliation; uninstalling a service does not withdraw an on-chain position.

For the extension: remove it at `chrome://extensions`. That also discards the API key and
the session-key vault, both of which live in `chrome.storage.local` and were never synced.

For the Python side there is nothing to uninstall beyond the pip packages; `data/` and
`results/` are regenerable and safe to delete.

## Upgrading

```bash
git pull
pip install -r backtester/requirements.txt   # in case deps moved
python3 -m unittest discover -s backtester/tests -t .
python3 -m unittest discover -s soltui/tests -t .
(cd extension && npm test)
python3 scripts/check_docs.py
```

If `soltui` is installed, rerun `soltui-service build` after a pull that touched it — the
alias bundle picks up source changes automatically, but a changed dependency set or a moved
file does need the rebuild.
