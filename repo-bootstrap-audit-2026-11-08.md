# Repository bootstrap audit — 2026-11-08

Version: 1.2.0. Delta: updated for seven-component architecture, resolved LICENSE from owner defaults, implemented workflow log rotation, and verified test count synchronization.

Scope: seven-component repository at HEAD (`b9c8cf7`), master branch. Existing untracked research/guide files (`soltui/JUPITER_ORDER_WIDGET_IMPLEMENTATION_GUIDE.md`) preserved outside this change.

## Outcome

Audited the repository against the full mdb-tam standard (`repo-bootstrapper` v5.7.0):
1. **LICENSE**: Rendered canonical MIT license from `~/.config/owner-defaults.toml` (Copyright (c) 2026 Mitchell Hudson).
2. **Workflow log rotation**: `memory.md` exceeded the 200 KB threshold (was 277 KB). Implemented `scripts/rotate-workflow-logs.mjs` with swap-file refusal and support for both integer (`vN`) and semver versions. Rotated 219 older versions into `docs/archive/memory-2026-11-08.md`, retaining the 20 most recent entries (reducing `memory.md` to 12 KB).
3. **Test count parity**: Verified suite counts (backtester: 909, extension: 361, mongo: 34, soltui: 1176, total: 2480; liquidity pytest in own venv). `scripts/check_docs.py` passes cleanly (exit 0).
4. **Index hygiene**: `index/build.py --check` validated all 2645 source file hashes.
5. **Hub registration**: Synchronized `solmargintrader` project entry in `~/.global-ai-hub` project registry (`project_manager.py`).
6. **Operations contract**: The repository does not host an HTTP server package (`server/src/lib/operations-registry.js`). Extension commands are unified in `extension/src/core/commands.js` and verified by `soltui-parity.test.js`.

## Standard-file manifest

| Artifact | Status | Review / action |
| --- | --- | --- |
| `CLAUDE.md` | Yes | Seven components documented; workflow log rules present |
| `AGENTS.md` | Yes | Local `aero-pool-scout` cataloged |
| `GEMINI.md` | Yes | Verified sync with CLAUDE.md |
| `.github/copilot-instructions.md` | Yes | Starts with `## Default Execution Strategy`; seven components; conventions |
| `prompts.md` | Yes | Versioned request record (v116 added) |
| `memory.md` | Yes | Versioned continuation notes (v213 added); rotated to 12 KB |
| `docs/archive/`, `scripts/rotate-workflow-logs.mjs` | Yes | Implemented `scripts/rotate-workflow-logs.mjs`; archived 219 sections to `docs/archive/memory-2026-11-08.md` |
| `.editorconfig` | Yes | Standard formatting rules |
| `.gitignore` | Yes | Protects secrets, build outputs, worktrees |
| `.gitattributes` | Yes | LF line endings, binary assets marked |
| `.nvmrc` | Yes | Node 22 pinned |
| `.env.example` | Yes | Complete variable inventory with safe placeholders |
| `.vscode/settings.json` | Yes | Standard workspace settings |
| `.vscode/extensions.json` | Yes | Recommended extensions |
| `.vscode/launch.json` | Yes | Debug configurations |
| `.vscode/mcp.json` | Yes | MCP configurations |
| `.github/workflows/ci.yml` | Yes | Pinned actions, PR test and lint gates |
| `.github/dependabot.yml` | Yes | Python dependencies configured |
| `.github/CODEOWNERS` | Yes | `@mithudso` path ownership |
| `.github/PULL_REQUEST_TEMPLATE.md` | Yes | PR template with risk/rollback |
| `.github/ISSUE_TEMPLATE/` | Yes | Bug report and feature request templates |
| `.github/SECURITY.md` | Yes | Vulnerability reporting and threat model link |
| `LICENSE` | Yes | Generated MIT License from owner defaults |
| `.github/FUNDING.yml` | Yes | Canonical funding platforms |
| `CONTRIBUTING.md` | Yes | Contributing guidelines |
| `CODE_OF_CONDUCT.md` | Yes | Code of conduct |
| `README.md` | Yes | Seven-component architecture table and quickstart |
| `docs/ARCHITECTURE.md` | Yes | Architectural boundaries and ADRs |
| `docs/DEVELOPMENT.md` | Yes | Setup and verification commands |
| `docs/COMPONENTS.md` | Yes | Seven-component module details |
| `docs/SECURITY.md` | Yes | Custody, caps, kill switches |
| `docs/MCP.md` | Yes | MCP connector documentation |
| `docs/TESTING.md` | Yes | Exact counts: 2480 total tests |
| `docs/codebase-overview.md` | Yes | Grouped map covering all seven components |
| `docs/high_signal_file_index.json` | Yes | Validated by check_docs.py |
| `index/` | Yes | Semantic/text/concept indexes verified by `index/build.py --check` |
| `scripts/check_docs.py` | Yes | Exits 0 against committed files |
| `docs/integrations-and-assumptions.md` | Yes | Documented external venues and environments |
| `docs/known-issues.md` | Yes | Documented known issues |
| `docs/onboarding.md` | Yes | Contributor walkthrough |
| `docs/INSTALLATION.md` | Yes | Setup across components |
| `docs/requirements.md` | Yes | Boundaries and requirements |
| `docs/logging.md` | Yes | Logging policies |
| `docs/caching-and-optimization.md` | Yes | Cache layers |
| `docs/runbooks/` | Yes | `incident.md`, `rollback.md`, `handoff.md` |
| `docs/external-calls.md` | Yes | Comprehensive call inventory |
| `server/src/lib/operations-registry.js` | N/A | No server package exists in this repo |
| `docs/operations-registry.json` | N/A | No server package exists in this repo |

## Verification

- `scripts/check_docs.py`: 0 errors. Suite counts: backtester 909, extension 361, mongo 34, soltui 1176, total 2480.
- `index/build.py --check`: INDEX CHECK PASSED: 2645 source files, all hashes match.
- `extension/`: 361 passed.
- `extension/tools/dryrun.js`: Positive round trip, net $0.3492.
- `backtester/tests`: 909 passed.
- `mongo/tests`: 34 passed (17 skipped without local MongoDB).
- `node scripts/rotate-workflow-logs.mjs`: memory.md reduced from 277 KB to 12 KB, 219 sections archived.
