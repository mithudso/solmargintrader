# AGENTS.md

Agent instructions for this repository live in [CLAUDE.md](CLAUDE.md). Read that file first.

Summary of the rules most often broken here:

- Dry-run is the default and the extension installs disarmed. Do not change that.
- Risk rails are enforced in `extension/src/core/risk.js` and must fail closed.
- Never guess a price, quantity or fee that becomes an order — refuse and surface it.
- Reconcile against the venue before planning; never auto-retry an ambiguous submit.
- Add actions to `extension/src/core/commands.js` only. The parity test enforces this.
- No secrets in logs, `chrome.storage.sync`, the DOM, or a response body.

Verification commands are in [CLAUDE.md](CLAUDE.md#before-you-claim-a-change-works).
