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

`full-auto` is the only mode where a signing key exists on the machine. Rules, all enforced in
`extension/src/wallet/signer.js`:

- Use a **dedicated keypair** holding grid working capital only. Never your main wallet.
- The 32-byte seed is **AES-GCM** encrypted under a passphrase-derived key (**PBKDF2-SHA256,
  600,000 iterations**), with a fresh 16-byte salt and 12-byte IV per encryption. Identical
  plaintext never produces identical ciphertext — there is a test for that.
- Storage is `chrome.storage.local` or a mode-0600 file. **Never** `chrome.storage.sync`, which would
  upload it to Google.
- The decrypted seed exists only inside a signing call. It is never logged, never stringified, and
  never crosses a message boundary. The generated seed buffer is zeroed after use.
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
| `full-auto` | dedicated session key | yes |

### Custody fact you cannot change

Trigger V2 deposits land in a **Privy-managed custodial vault**, one per wallet. Funds backing
resting orders sit there, not in your wallet, and recovering them from an unfilled order is a
two-step cancel-and-withdraw.

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
