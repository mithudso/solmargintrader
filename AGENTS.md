# AGENTS.md

Agent instructions for this repository live in [CLAUDE.md](CLAUDE.md). Read that file first.

Save the request in `prompts.md` and keep versioned continuation notes in `memory.md`.
Follow the workflow-record rule in `CLAUDE.md` before implementation and at delivery.

## Repository-local agents

| Agent | Scope | Model | When to use | Tools / access |
| --- | --- | --- | --- | --- |
| [oracle](.claude/agents/oracle.md) | Oracle inspection and guide routing | inherit | Market provenance, strategy votes, lifecycle and readiness | Bash and Read; no signing or orders |
| [aero-pool-scout](.claude/agents/aero-pool-scout.md) | `liquidity/` research only | sonnet | Independently check the daemon's pool ranking | Bash, Read, Write, WebSearch, WebFetch; Base RPC and public market sources; no signing or config changes |

The agent definitions are the source of truth.

Summary of the rules most often broken here:

- Dry-run is the default and the extension installs disarmed. Do not change that.
- Risk rails are enforced in `extension/src/core/risk.js` and must fail closed.
- Never guess a price, quantity or fee that becomes an order — refuse and surface it.
- Reconcile against the venue before planning; never auto-retry an ambiguous submit.
- Add actions to `extension/src/core/commands.js` only. The parity test enforces this.
- No secrets in logs, `chrome.storage.sync`, the DOM, or a response body.

Verification commands are in [CLAUDE.md](CLAUDE.md#before-you-claim-a-change-works).

<!-- llms-routing:pointer --> See `## llms routing` in CLAUDE.md for the llms files and quick answers.
