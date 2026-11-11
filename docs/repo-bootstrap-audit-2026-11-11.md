# Repository bootstrap audit — 2026-11-11

Version: 1.0.0
Delta: Revalidate the standard manifest and correct execution-boundary and dependency-maintenance drift.
Task: TASK-1369. Baseline: 789d3bdd6b7f6a2ff2f0822a1da7325a262c278c.

## Outcome

The bootstrap pass corrected verified stale documentation and automation metadata. It does not establish complete five-standard compliance, whole-repository code convergence, live execution or a profitable strategy. The separate code-optimizer report and its per-file ledger carry actual code-review coverage.

The current forecast/MCP service remains read-only. The separately enabled Oracle TradingView worker can submit Coinbase spot orders or locally constructed GUM ZEC perpetual Actions. The extension's read-only Perps adapter is a different implementation. GUM application funding and perps collateral deposits are distinct from order Actions. An order Action verifier does not verify an arbitrary deposit transaction.

## Manifest and accuracy checks

| Area | Presence | Current assessment / action |
| --- | --- | --- |
| CLAUDE.md, AGENTS.md, GEMINI.md, prompts.md, memory.md | Present | Shared workflow and local-agent routing retained. Refreshed only CLAUDE.md's LLM routing block; parent owns versioned task records. |
| .github/copilot-instructions.md | Present | Corrected six-component and read-only SolTUI claims; lists all ten components, the webhook boundary and relevant Oracle/ecosystem checks. |
| .github/PULL_REQUEST_TEMPLATE.md, .github/SECURITY.md | Present | Corrected omitted live-capable paths and require actual applicable checks/skipped-gate evidence. |
| .editorconfig, .gitignore, .gitattributes, .nvmrc | Present | Existing Python/Node, LF, binary and private-output conventions retained. No formatter churn or new dependency introduced. |
| .env.example | Present | Added the optional ORACLE_WEBHOOK_SECRET name with no value; private --secret-file remains preferred. This is not a proof that every runtime variable is inventoried. |
| .vscode/settings.json, extensions.json, launch.json | Present | Existing Python/Node editor/debug entries retained. |
| .mcp.json, .vscode/mcp.json | Absent | Intentional authenticated host-specific registration; docs/MCP.md explicitly documents the omission. No credentials or fictional portable binding added. |
| .github/workflows/ci.yml | Present | Existing SHA-pinned PR tests/lint retained. Parent owns changes for this feature's research checks. |
| .github/dependabot.yml | Present | Added monthly updates for Oracle, manager and ecosystem pip manifests, plus executor's uv manifest/lock pair. Existing components retained. Coupled first-party updates still require integration checks. |
| .github/CODEOWNERS, issue templates, LICENSE, CONTRIBUTING.md, CODE_OF_CONDUCT.md | Present | Existing owner/reporting/license conventions retained. No invented disclosure SLA. |
| README.md | Present | Removed the global claim that no Jupiter leveraged REST write API exists. The extension and separate GUM path remain explicit. |
| docs/ARCHITECTURE.md, COMPONENTS.md, SECURITY.md | Present | Corrected Oracle version and signing boundaries; documented durable close/settle/open and separate funding verification. |
| docs/logging.md, external-calls.md | Present | Added actual webhook/CLI/GUM transport, journal and redaction boundaries; explicitly no universal per-request error sink. |
| docs/TESTING.md, DEVELOPMENT.md, INSTALLATION.md, requirements.md, integrations-and-assumptions.md, known-issues.md, onboarding.md, caching-and-optimization.md | Present | Existing source-backed guides retained; owning checkers validate counts/paths, not all historical prose or live runtime. |
| docs/ECOSYSTEM-WIKI.md and packaged wiki | Present | Existing wiki remains authoritative navigation; parent rebuilds exact tracked source snapshots after feature and doc edits settle. |
| docs/codebase-overview.md and high_signal_file_index.json | Present | Corrected Oracle money-moving boundary, added webhook/GUM modules and regenerated 272 file/directory entries through the existing generator. |
| scripts/rotate-workflow-logs.mjs and docs/archive/ | Present | Logs were below the approximately 200KB per-file threshold at intake; no rotation or unrelated archival rewrite. Workflow versions remain distinct from package versions. |
| docs/operations-registry.json, docs/tool-inventory.json | Absent | Existing major architectural backlog remains explicit; no fake generated inventory or generic retry controller added. |

## LLM navigation refresh

The old family pointed at a removed bootstrap worktree and Oracle0.2.2. The current family is a **partial delta navigation refresh**. It verifies current package metadata and changed execution boundaries, retains source tags and regenerates a shallow sitemap of 3297 existing tracked/non-ignored working paths. It does not claim new deep semantic coverage of all source bodies, complete dynamic flags, or an executable call graph. The outside-repository artifacts are at `/Users/mitch/.research/distillations/solmargintrader-health-20261111.repo/`; its manifest records scope and package versions. Bootstrap updates the maintained root copies. CLAUDE.md now points at the canonical repository family.

The generic llms_lint tool exits0 but emits warnings because these repository navigation files do not use its web-mirror page grammar and the maintained copies are not a standalone export directory. That is not an LDO clean result. Source-path existence, honest scope, package metadata and normal repository doc checks are the concrete gates used here. No inference, embedding index or paused service was started.

## Verification

| Check | Actual result |
| --- | --- |
| Oracle baseline unittest discovery/execution | Exit0; 183 tests in6.061s. One existing unclosed SQLite ResourceWarning was observed. |
| ruff check oracle | Exit0; all checks passed. |
| scripts/build_doc_index.py | Exit0; 272 entries generated from the source overview. |
| scripts/check_docs.py, configured docs environment and source manager path | Exit0; 2957 discovered tests:1005 backtester,434 extension,46 mongo,1472 SolTUI. This command discovers counts; it does not run those suites. |
| Dependabot YAML/source/duplicate validation | Ruby stdlib YAML validation exit0; nine unique ecosystem/directory entries; both uv owners have lockfiles. Python attempts failed with ModuleNotFoundError:yaml; no dependency was installed merely to parse YAML. |
| registry_drift_check.py solmargintrader --no-log | Exit0. No project was created or rebound. |
| Owned documentation diff check | Exit0. Parent runs final combined checks after all task changes settle. |

## Residual gaps and preservation

- The full five-standard operation registry, common failure schema, complete remediation maps and generated per-call cards remain absent. The prior Nov10 audit states this correctly. No historical finding marked retracted was reintroduced without new evidence.
- External-call documentation describes implementations and logical boundaries; it is not an exhaustive generated per-call-site census. Unknown logs/coverage are labelled rather than inferred.
- Dependabot coverage is improved. No current whole-dependency vulnerability clearance is claimed.
- Code review remains incremental and coverage-limited; consult the CDO receipt and remaining plan rather than treating this checklist as a code certificate.
- Preserved other worktrees, unrelated files, archived liquidity/KILL state, paused inference and existing runtime owners. Only the separately requested forward watcher and UI deployment are parent/worker-owned operational changes.
