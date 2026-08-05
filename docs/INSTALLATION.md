# Installation

Four components, four different install stories. Only one of them installs anything
persistent on your machine.

| Component | Install | Persistent? |
| --- | --- | --- |
| `backtester/` | `pip install -r backtester/requirements.txt` | No |
| `research/` | Covered by the backtester's requirements | No |
| `extension/` | Nothing — zero dependencies. Load unpacked in Chrome | Browser profile only |
| `soltui/` | `pip install -r soltui/requirements.txt`, then a launchd agent | **Yes** — starts at login |

## Prerequisites

- **Python 3.13.** Verify with `python3 -V`. CI pins 3.13 and the code uses 3.13-era
  features (`enum.StrEnum`).
- **Node 22.** Verify with `node -v`. Pinned in `.nvmrc`. Ed25519 in WebCrypto and
  `node:test`'s output format both need a recent runtime.
- **Chrome or a Chromium browser**, for the extension.
- **macOS**, for `soltui/` only.

## Backtester and research

```bash
pip install -r backtester/requirements.txt
```

Verify:

```bash
python3 -m unittest discover -s backtester/tests -t .     # 454 OK
python3 -c "import backtester.cli; print('imports ok')"
```

Dependencies are minimal on purpose and `pyarrow`, `requests` and `pytest` are deliberately
excluded. Then fetch data, which is the only network step:

```bash
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01
```

`data/` is gitignored, so this is required on a fresh clone and repeatable at any time.

## Extension

There is nothing to install: zero runtime and zero dev dependencies, by design.

```bash
cd extension
npm test                                              # 114 pass
node tools/dryrun.js --ticks 8 --osc 6 --offline 100  # round trip must close positive
```

To load it in the browser: `chrome://extensions` → enable **Developer mode** → **Load
unpacked** → select the `extension/` directory.

**It installs disarmed, in dry-run.** `DEFAULT_CONFIG.mode` is `dry-run` and no default may
ever be changed such that a fresh install can place an order. Leave it that way until you
have read `extension/README.md`'s **Verification status** section — no live order has ever
been placed through this code.

The unpacked load cannot be automated (`chrome://extensions` needs a human), so it is never
verified by CI. Do not claim it as verified; the headless dry run is the gate.

### Optional: the local HTTP surface

```bash
node tools/api-server.js
```

Reads `SMT_API_PORT`, `SMT_API_TOKEN` and `SMT_PASSPHRASE` from the environment. Put values
in a local `.env` (already gitignored) and treat the port as trusted-local only. An empty
`SMT_PASSPHRASE` leaves the session-key vault sealed, which makes full-auto degrade to
approval rather than fail silently.

## soltui

This one installs a launchd agent that runs at login, so read `soltui/README.md` first.

```bash
pip install -r soltui/requirements.txt
python3 -m unittest discover -s soltui/tests -t .   # 95 OK, ~70s
python3 soltui/soltui-service build                 # build the app bundle
python3 soltui/soltui-service install               # install bundle + launchd agent
python3 soltui/soltui-service status                # bundle / agent / flag / launchd state
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

## Uninstall

```bash
python3 soltui/soltui-service stop        # remove the flag file; launchd stops supervising
python3 soltui/soltui-service uninstall   # remove the bundle and the agent
```

Use the subcommand rather than deleting files by hand — it removes the bundle from
`~/Applications`, the `com.mitchhudson.soltui` agent, and the supervise flag together. The
full subcommand set is `build`, `install`, `start`, `stop`, `status`, `uninstall`.

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
cd extension && npm test
python3 scripts/check_docs.py
```

If `soltui` is installed, rerun `soltui-service build` after a pull that touched it — the
alias bundle picks up source changes automatically, but a changed dependency set or a moved
file does need the rebuild.
