# Ecosystem wiki and documentation ownership

The control room wiki collects the Oracle, ecosystem supervisor, Bot Manager and
Backtester documentation in one searchable snapshot. It also includes the
architecture, installation, testing, lifecycle, operating and accepted UI design
guides. Source documents remain authoritative for their stated version and
scope. The wiki preserves their text and authorship; it does not rewrite old
plans as delivered capabilities.

## Project navigation

This existing wiki is the repository's maintained navigation; no second wiki
service or duplicate command reference is needed. In an installed environment,
`solbot ui status` discovers the current verified address without starting it.
`solbot ui open` explicitly starts availability when needed and opens the control
room; select **Wiki**. The source links below remain usable without a running UI.

| Area | Start here | Authoritative detail |
| --- | --- | --- |
| Commands and setup | [Managed suite](bot-manager-managed-suite.md) | [Installation](INSTALLATION.md), [development](DEVELOPMENT.md), [Bot Manager](../botmanager/README.md) |
| Reference and architecture | [Component map](COMPONENTS.md) | [Architecture](ARCHITECTURE.md), [source file map](codebase-overview.md), [requirements](requirements.md) |
| Scripts and maintenance | [Script inventory](SCRIPTS.md) | [Testing](TESTING.md), [incident runbook](runbooks/incident.md), [rollback](runbooks/rollback.md) |
| Strategy and evidence | [Canonical strategy cards](../backtester/strategy_cards/README.md) | [Research survey](../research/STRATEGIES.md), [strategy optimization](strategy-optimization-concept-family.md), [Oracle consumer interface](bot-manager-oracle-interface.md) |
| Execution and security boundaries | [Security](SECURITY.md) | [Known issues](known-issues.md), [external calls](external-calls.md), [executor rules](../executor/CLAUDE.md) |
| Separate hosted website | [Website guide](../website/README.md) | [Read-only analysis bridge](../website/engine/README.md); wallet accounts and inactive paper definitions do not control the local owner suite |

For the manager's complete recommended command order, read `solbot --help` or
`solbot help`. The structured help and parser share the same command registry.
Use `solbot health-check`, `solbot metrics` and `solbot component-alerts` for
collector measurements and bounded availability events; use rich account status
for account evidence. These reads never supply a missing execution certification.

Keep historical research tables, frozen plans and archived liquidity guidance in
their original scope. The liquidity manager remains disabled and killed. A
strategy reference is neither a recommendation nor authority to place an order.

## Find an answer

Search uses every included document's title, source path and full text. The
catalog separates component guides, strategy cards, incomplete references,
architecture, design and historical plans. A matching strategy document does not
establish that its strategy is runnable. An incomplete reference remains an
incomplete reference.

Each page exposes its original file location, SHA-256, source commit when known,
and the snapshot hash. Pages compiled from changed or newly staged source are
labelled `working_tree_snapshot`; they do not claim a commit that contains those
bytes. Committed pages link to their specific GitHub revision. The source path
always points to the canonical checkout under
`/Users/mitch/dev/solmargintrader`.

The wiki is documentation, not a runtime health probe. Use the control room's
current owner state, lifecycle evidence, freshness and action results to decide
what is running. Historical accuracy and vote agreement do not establish profit.
Forward P&L needs recorded prospective economics and costs; missing accounting
evidence remains unavailable.

## Component and file map

| Responsibility | Source of truth |
| --- | --- |
| Paper orchestration and recovery | `/Users/mitch/dev/solmargintrader/ecosystem/runner.py` and `/Users/mitch/dev/solmargintrader/ecosystem/recovery.py` |
| Control room HTTP interface | `/Users/mitch/dev/solmargintrader/ecosystem/web.py` |
| Native manager event bridge | `/Users/mitch/dev/solmargintrader/ecosystem/telemetry.py` |
| Stable external trial registration | `/Users/mitch/dev/solmargintrader/ecosystem/registration.py` |
| Bot configuration and lifecycle commands | `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/registry.py` |
| Bot operation and P&L owner | `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/ledger.py` and `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/status.py` |
| Frozen historical matrix and forward handoff | `/Users/mitch/dev/solmargintrader/soltui/f5_batch.py` |
| Prospective calls and outcomes | `/Users/mitch/dev/solmargintrader/soltui/forwardtest.py` |
| Canonical costed simulation | `/Users/mitch/dev/solmargintrader/backtester/core/engine.py` |
| Strategy equations, limitations and defaults | `/Users/mitch/dev/solmargintrader/backtester/strategy_cards/README.md` |
| Oracle observations, forecasts and evidence | `/Users/mitch/dev/solmargintrader/oracle/engine.py` and `/Users/mitch/dev/solmargintrader/oracle/store.py` |
| Oracle vote thresholds and weights | `/Users/mitch/dev/solmargintrader/oracle/voting.py` |
| Oracle MCP and guide routing | `/Users/mitch/dev/solmargintrader/oracle/server.py` and `/Users/mitch/dev/solmargintrader/oracle/guidance.py` |

## Architectural choices

The ecosystem coordinates existing owners. F5 retains its backtest queue and
forward ledger. Bot Manager retains bot operation and P&L. Oracle retains
instrument-bound forecasts and their evidence. The shared recorder remains a
singleton. The wiki creates no recorder, optimizer, worker or order path.

The wiki is a packaged snapshot rather than a filesystem browser. The build
command selects only tracked Markdown in an explicit allowlist. Untracked local
notes, private configuration, arbitrary HTTP paths and credential files cannot
be selected through the wiki API. Source Markdown and links are untrusted text;
the browser must render them without evaluating HTML, scripts or instructions.

The snapshot contains two generated files:

- `/Users/mitch/dev/solmargintrader/ecosystem/wiki_content/manifest.json` records
  page identities, categories, provenance, content hashes and the bundle hash.
- `/Users/mitch/dev/solmargintrader/ecosystem/wiki_content/pages.json` preserves
  the original Markdown bodies under deterministic page IDs.

The runtime validates both hashes and each page's content hash before serving
the snapshot. It refuses malformed IDs, unknown pages, changed content and
unavailable bundles. A caller supplies a page ID, never a local path. A rebuild
invalidates the runtime's bounded cache.

## API contract

`catalog(query="", limit=100, offset=0)` returns matching page metadata, total
matches, category names, pagination and `snapshot_sha256`. Search uses all terms,
ignores case and returns bounded text excerpts. The query limit is 256 characters;
page limits range from 1 to 5,000. `page(id)` returns one page with its Markdown
body and provenance. Both return schema version 1. Missing or corrupt snapshots
return `status=unavailable`; invalid argument shapes are rejected.

The HTTP owner maps these functions to `/api/wiki` and `/api/wiki/page`. Normal
control-room origin and authorization rules apply. A wiki page cannot invoke an
action. Documentation links never confer execution authority.

## Rebuild and verify

The generator uses Git's tracked-file inventory and does not fetch, embed or run
inference. Stage a newly created public guide before rebuilding, so it becomes
part of that reviewed inventory.

```sh
INDEX_NO_AUTO=1 python3 /Users/mitch/dev/solmargintrader/scripts/build_ecosystem_wiki.py
INDEX_NO_AUTO=1 python3 /Users/mitch/dev/solmargintrader/scripts/build_ecosystem_wiki.py --check
INDEX_NO_AUTO=1 python3 -m unittest ecosystem.tests.test_wiki
```

Unchanged pages retain their original build provenance, making rebuilds stable
after unrelated commits. `--refresh-provenance` explicitly refreshes source
commit bindings for unchanged content. Content changes always update page and
snapshot hashes. A source reference may be historical; a successful wiki check
proves snapshot integrity and current source coverage, not trading readiness.


## Maintenance ownership

The author of a behavior or command change updates its authoritative guide in the
same change. The repository reviewer is identified by `.github/CODEOWNERS`.
Reviewers check this navigation when commands, scripts, component boundaries or
strategy evidence change. Update the source guide first, then rebuild the
packaged snapshot with the commands above; never hand-edit the generated bundle.

Commit public source guides before the final provenance build when a committed
source binding is required. Verify local Markdown links, the wiki check and the
relevant command parser/help or focused tests. A newly created source page must
be tracked and pass the explicit allowlist in `ecosystem/wiki.py`. Otherwise add
a navigation link to the appropriate authoritative guide rather than widening
public exposure indiscriminately.

The packaged wiki is the maintained runtime documentation surface. No hosted
GitHub Wiki is required by this architecture; if a future hosted mirror is added,
record its accessibility and synchronization status separately. A failed hosted
mirror must not make this repository-local navigation unusable. Do not include
private memory, transcripts, credentials or machine state in public wiki sources.
