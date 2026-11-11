# Security model

This repository contains software that can move real money. Two assets matter: **signing keys** and
the **Jupiter API key**.

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
- **Bearer token on every command route.** Generated at startup and printed, or pinned with
  `SMT_API_TOKEN`. Compared with `timingSafeEqual` after a length check.
- **Browser requests refused.** A token alone is insufficient because a page can post to localhost;
  `Origin` or `Sec-Fetch-Site` on a request means refusal.
- **`GET` is read-only.** Nothing that changes state is reachable from a URL alone, so a link cannot
  arm your grid.
- **Bounded input.** Bodies are capped at 256 KB and must be a JSON object.
- **No stacks in responses.** Errors return a message only.

Do not put this behind a tunnel or reverse proxy without adding transport security and access
control of your own. It has no rate limiting, no audit log, and no multi-user concept.

## Secrets and git

`.gitignore` excludes `.solmargintrader/`, `journal.json`, `config.json`, `.env*` and the
`jup.ag/` reference dump. Before committing, confirm no key material is staged:

```bash
git diff --cached | grep -iE 'BS58_PRIVATE_KEY|x-api-key|SMT_API_TOKEN|passphrase|seed'
```

## Reporting

This is personal tooling with no support commitment. If you find a defect that could lose funds, stop
trading with it first (`node tools/cli.js kill`), then fix it.
