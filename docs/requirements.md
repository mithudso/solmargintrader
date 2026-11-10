# Requirements

These requirements describe existing code boundaries, not future product promises.

| Component | Functional requirement | Verification |
| --- | --- | --- |
| Backtester | Run strategy/exposure and ladder-grid simulations from local bars, with costs and no lookahead | `backtester/tests/`; strategy-card and grid parity checks |
| Research | Preserve source/checksum/evidence limits and distinguish in-sample rankings from held-out results | `research/verify_numbers.py`, CPCV and interpretation tests |
| Extension | Reconcile before plan; enforce fail-closed risk rails; persist intents before submission | `extension/test/`, offline dry run |
| Soltui | Provide research and paper controls; isolate the separately armed manual Coinbase order path | `soltui/tests/`; installed app acceptance remains separate |
| MongoDB | Rebuild selected derived collections with provenance; repeated loads must not duplicate bars | `mongo/tests/`; server-backed cases skip if MongoDB is unavailable |
| Liquidity | Retain archived LP implementation; keep its daemon/scout disabled and kill switch set | Own pytest/Ruff suite; network simulation and live acceptance are separate |

| Bot Manager | Preserve specifications and desired intent; use bounded owner-aware paper workers and evidence gates | `botmanager/tests/`; independent installed acceptance |
| Oracle | Preserve source/instrument provenance and serve read-only forecast/history MCP; never sign or submit | `oracle/tests/`; installed MCP checks |
| Ecosystem | Reuse existing research owners; maintain scoped paper control room and compact availability measurements | `ecosystem/tests/`; isolated native/Chrome gate |
| Executor | Verify exact swap intent, hard rails, simulation and one-send reconciliation before signing | `executor/tests/`; real execution is a separate gate |

## Runtime and dependency requirements

- Main Python CI uses 3.13; requirements are component-specific. Liquidity's supported
  interpreter range and locked dependencies live in `liquidity/pyproject.toml` and `uv.lock`.
- Node 22 is the repository's verified runtime (`.nvmrc` and CI). The extension manifest
  remains ESM with zero runtime/development dependencies and no build step.
- Chrome MV3 APIs are required for the installed extension. CLI and HTTP tests use the
  same command registry without Chrome.
- The soltui menu-bar bundle and launchd services require macOS. Terminal research tools
  have different portability limits from the packaged menu-bar app.
- MongoDB integration needs a reachable local server; schema description does not.

## Non-functional boundaries

Fresh defaults remain dry-run/disarmed. Missing price/quantity/fee inputs that would size
an order must be surfaced rather than guessed. Signing keys, passphrases and API keys
must not enter logs, the DOM, synced storage or responses. Offline tests use fakes and
must not require market-data downloads, wallets, live services or inference.

There is no hosted multi-user service, uptime SLA, numeric coverage threshold, or common
operations-remediation server in this repository. See `docs/external-calls.md` for the
remaining five-standard gaps and `docs/known-issues.md` for live acceptance limits.
