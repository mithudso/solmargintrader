# Security model

This repository contains software that can move real money. Key assets include **signing keys** and
the **Jupiter API key**. The separate hosted website also handles wallet account
identities, sessions, subscription data and server-side integration credentials.

## Threat model

| Adversary | Can they act? | Mitigation |
| --- | --- | --- |
| A web page you visit | Would try to reach the local API — a page **can** `fetch` localhost | Bearer token required; any request carrying `Origin` or `Sec-Fetch-Site` is refused outright; no CORS headers are ever sent |
| Another local process | Can read files it has permission to read | Config and journal files are written mode `0600`; the session-key seed is AES-GCM encrypted at rest |
| A malicious or compromised extension | Could read `chrome.storage` | Nothing is stored in `chrome.storage.sync`; a full-auto key holds working capital only |
| A compromised Jupiter response | Feeds bad prices or order data | Non-finite or non-positive prices abort the tick; a fill without a reliable price or quantity is refused, not guessed; venue-supplied strings never reach `innerHTML` |
| Someone reading your terminal or shell history | Sees whatever you typed | `setApiKey` returns a length, never the key; the dashboard clears the field after save; the API never echoes secrets |

## Key custody

For the extension, `full-auto` is the only mode that uses its local signing key. Rules, all enforced in
`extension/src/wallet/signer.js`:

- Use a **dedicated keypair** holding grid working capital only. Never your main wallet.
- The 32-byte seed is **AES-GCM** encrypted under a passphrase-derived key (**PBKDF2-SHA256,
  600,000 iterations**), with a fresh 16-byte salt and 12-byte IV per encryption. Identical
  plaintext never produces identical ciphertext — there is a test for that.
- Storage is `chrome.storage.local` or a mode-0600 file. **Never** `chrome.storage.sync`, which would
  upload it to Google.
- Plaintext seed bytes exist only during bounded initialization. The signer retains one
  nonextractable operational key. Seed, PKCS8 and decrypted temporary buffers are zeroed;
  plaintext never crosses a message boundary or enters a log.
- A wrong passphrase fails closed and does not distinguish "wrong passphrase" from "tampered record".
- The wrap key is derived non-extractable, so it cannot be read back out of WebCrypto.

### The three modes are not interchangeable

An injected browser wallet cannot produce a silent signature, and `window.solana` does not exist in a
service worker at all. "Unattended bot" and "wallet approves every trade" are mutually exclusive, so
both are named rather than one being quietly chosen:

| Mode | Signing | Unattended |
| --- | --- | --- |
| `dry-run` (default) | never signs | yes |
| `semi-auto` | you approve each signature | **no** |
| `full-auto` | dedicated session key; Trigger writes require a semantic verifier | writes blocked by bundled adapter |

Raw cryptographic signing does not verify economic intent. The Trigger adapter refuses
automatic deposit/withdrawal signing without a trusted verification bridge; the bundled
signer supplies none. See `docs/jupiter-trigger-contract.md` for the exact boundary.

### Custody fact you cannot change

Trigger V2 deposits land in a **Privy-managed custodial vault**, one per wallet. Funds backing
resting orders sit there, not in your wallet, and recovering them from an unfilled order is a
two-step cancel-and-withdraw.

## Liquidity custody and controls

The separate liquidity component can sign Base transactions. `wallet.py` loads from
an explicitly configured owner-only mode-0600 key file, macOS Keychain, or a legacy
private-key environment fallback. Agents never read, print or copy those key values.
`liquidity/CLAUDE.md` governs the owner's standing live authorization and its limits.

- The RPC chain id, stale head, TWAP, gas/position/total-deployed caps and token allow-list
  are execution boundaries. Do not raise caps or lower `min_net_apr` during a code audit.
- Every sequence goes through a Rebalancer and Runner. Simulation is not a mined receipt;
  a timeout after broadcast does not prove failure. Retain transaction hashes and partial state.
- The daemon reads `AERO_LP_HOME/KILL`. Soltui may create/remove that flag but never imports
  the signing/executor stack. Resuming permits an already-live daemon to act inside its caps.
- `liquidity/scripts/aero-lp-service install` defaults to live operation. Dependency setup
  and offline tests do not require installing or restarting the service.
- Pool labels, remote responses and unsolicited-token metadata are untrusted input.
  Contract addresses are centralized and require the two-source review in component rules.

## The local HTTP API

It can arm the engine and place orders, so it is locked down by default:

- **Loopback only.** Binds `127.0.0.1` unless `--host` is passed explicitly, and warns loudly when
  it is not loopback.
- **Bearer token on every command route.** The caller must export a nonempty
  `SMT_API_TOKEN` before startup; the server refuses a missing token and never prints
  its value. It compares tokens with `timingSafeEqual` after a length check. See
  [local API setup](INSTALLATION.md#optional-the-local-http-surface) for caller-side generation.
- **Browser requests refused.** A token alone is insufficient because a page can post to localhost;
  `Origin` or `Sec-Fetch-Site` on a request means refusal.
- **`GET` is read-only.** Nothing that changes state is reachable from a URL alone, so a link cannot
  arm your grid.
- **Bounded input.** Bodies are capped at 256 KB and must be a JSON object.
- **No stacks in responses.** Errors return a message only.

Do not put this behind a tunnel or reverse proxy without adding transport security and access
control of your own. It has no rate limiting, no audit log, and no multi-user concept.

## Hosted wallet-account website

`website/src/worker.js` is a separate public HTTP trust boundary. Wallet sign-in uses
an expiring, origin-bound Ed25519 challenge consumed by an atomic single-use update.
Session tokens are hashed in D1; cookies use Secure, HttpOnly and SameSite attributes.
State-changing browser routes check the exact origin and reject cross-site metadata.
Bot reads and writes are scoped to the authenticated user. These controls address
spoofing, replay and cross-tenant access; connecting a wallet grants no order authority.

The Worker applies CSP and other response headers. Request bodies and upstream replies
are bounded. Stripe webhook HMAC verification and a canonical subscription fetch gate
entitlement; a Checkout redirect never grants access. `STRIPE_SECRET_KEY`,
`STRIPE_WEBHOOK_SECRET` and `ENGINE_TOKEN` belong in Worker secrets, not the browser,
tracked configuration or bot definitions. The analysis bridge requires a bearer token,
refuses browser Origin headers and exposes only named read-only analysis operations.

Account deletion revokes its sessions and removes tenant-owned definitions. Preserve
billing evidence and provider state when investigating an ambiguous payment outcome;
source rollback does not undo an external subscription. The website's tests and
[deployment limits](../website/README.md) do not certify configured billing, a fresh
analysis engine or live per-user venue execution. Never tunnel the local owner API to
implement those missing capabilities.

## Secrets and git

`.gitignore` excludes `.solmargintrader/`, `journal.json`, `config.json`, `.env*` and the
`jup.ag/` reference dump. Before committing, list the staged paths without printing
their contents:

```bash
git diff --cached --name-only
```

A path list does not prove absence of credentials. Review values privately or use a
secret scanner that emits only a status and affected paths. Never print matching
credential lines, staged secret values or full diffs into shared logs.

## Reporting

This is personal tooling with no support commitment. If you find a defect that could
lose funds, stop the affected owner through its own control and preserve its journal.
A CLI kill affects its selected local state, not the browser or another service.
See [owner-scoped incident handling](OPERATIONS.md#stop-the-selected-owner).


## Manager, Oracle and managed control room

The manager and ecosystem default to paper/disarmed. The Oracle forecast service
observes and records source-labelled evidence; its MCP surface has no signer. The
separate TradingView worker is described below. A ready availability response does not
certify market data, research outcomes or permission to submit orders.

The manager uses same-user Unix IPC, private records, generation-bound ownership
and durable request receipts. The control-room identity binds both ecosystem and
manager homes, its generation, lock and HTTP response. A reused UI for another
manager home refuses adoption. The suite can terminate only actual child handles
it created; an adopted process ID conveys no termination authority.

The ecosystem HTTP service binds loopback and verifies Host, Origin and fetch
metadata. State-changing controls require the session nonce from the local
session endpoint. This differs from the extension HTTP adapter's bearer token.
The native helper authenticates Chrome's origin against the local allowlist. Its
fixed availability protocol accepts no browser-selected command, path, environment
or arbitrary URL. Browser reads never start a component.

Collector liveness, readiness and rich status are separate contracts. Unknown
measurements remain unknown; public errors are fixed and sanitized. Sensitive
records, tokens and keys must never appear in responses or logs. The archived
liquidity service remains disabled; bootstrap and documentation checks do not
activate it.

Authoritative implementation: `botmanager/src/botmanager/transport.py`,
`botmanager/src/botmanager/machine_health.py`, `botmanager/src/botmanager/suite.py`,
`ecosystem/ui_service.py`, `ecosystem/web.py`, `ecosystem/control.py`,
`soltui/native_host.py` and `soltui/native_host_install.py`.

## Oracle TradingView worker

The forecast/MCP service remains read-only. The optional webhook worker is a
separate money-moving path and defaults to dry-run. It authenticates an exact,
bounded JSON payload with a private body secret, limits signal age and durably
deduplicates event IDs. A socket timeout applies before request parsing, and
request-thread admission is capped at16. Excess sockets close before parsing.
Request bodies, secret values and upstream exception text
never enter its HTTP response or access log. A worker failure stops reception.

Coinbase commands use the authenticated official CLI and one explicitly bound
portfolio. GUM signing uses a mode-0600, owner-owned regular file opened with
no-follow/nonblocking flags. The loader verifies the derived public owner. The
adapter constructs and verifies a narrow binary order Action locally; raw
cryptographic signing is not permission to sign arbitrary server-built funding
transactions. KILL, stale-signal and final account checks run before submission.
Each leg is committed before one send; a timeout or absent history entry cannot
authorize a retry. See [the ZEC execution contract](JUPITER-ZEC-WEBHOOK.md).
