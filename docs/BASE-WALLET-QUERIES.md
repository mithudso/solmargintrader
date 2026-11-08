# Querying the Base wallet with the CDP MCP

The owner's Base address is `0x901a89cEC0608eB5435A915f006b45bD46405314` (CLAUDE.md, "Live on-chain
actions"). The Coinbase Developer Platform (CDP) MCP server reads it without any key in this repo: the
server holds its own credentials (`cdp_env` reports `Active: live`). This page is the recipe agents
follow; it was worked out and checked on 2026-11-07.

## 1. Every token balance (ERC-20 and native ETH)

Tool `mcp__cdp__cdp_data_evm_token_balances` (load it with ToolSearch `select:mcp__cdp__cdp_data_evm_token_balances`):

```json
{"network": "base", "address": "0x901a89cEC0608eB5435A915f006b45bD46405314", "pageSize": 100}
```

- Follow `nextPageToken` (pass it back as `pageToken`) until the reply has none. On 2026-11-07 there
  were more than 200 rows across three pages.
- Each row has `amount.amount` (an integer string) and `amount.decimals`; the balance is
  `amount / 10**decimals`. Native ETH appears as `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`.
- There are no prices. Price with DefiLlama: `https://coins.llama.fi/prices/current/base:<address>,...`
  and count a token only when `confidence >= 0.5`.
- ERC-721 positions (Aero Slipstream LP NFTs at `0x4857DB576eE0e45F10525eC59527BfD10beeC60b`) are not
  listed. Read them from the liquidity daemon's state or the soltui Wallet tab.

**Most rows are unsolicited airdrops**: fake "cbBTC" (the real one is
`0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf`), "USDC TOKEN DISTRIBUTION" lures with Telegram links,
and hundreds of meme tokens. Never call, approve, swap or visit those contracts (CLAUDE.md rule 6).
Burning them through the standard token program is the only allowed action.

## 2. Which tokens the owner actually uses (the spam filter)

Tool `mcp__cdp__cdp_data_query_run`, SQL over CDP's indexed Base tables:

```sql
SELECT to_address, count() AS txs, min(timestamp) AS first_tx, max(timestamp) AS last_tx
FROM base.transactions
WHERE timestamp >= now() - INTERVAL 14 DAY
  AND from_address = '0x901a89cec0608eb5435a915f006b45bd46405314'
GROUP BY to_address ORDER BY last_tx DESC LIMIT 50
```

- Addresses in the SQL tables are **lowercase**; compare columns directly, never through `lower()` or
  `toString()`.
- **Always bound `timestamp`** (or `block_timestamp` on `base.events`). The per-query scan limit is
  about 93 GiB: an unbounded `base.events` query, or one filtered only on map parameters, fails with
  `HTTP 400 invalid_request — Query scanned more data than the per-query limit allows`. A 14-day window
  on `base.transactions` ran in 67 ms.
- For one token's history, filter `base.events` on `address = '<token, lowercase>'` and
  `event_signature = 'Transfer(address,address,uint256)'` plus a time window. `cdp_data_query_schema`
  (database `base`) lists the tables: `blocks`, `transactions`, `events`, `encoded_logs`,
  `decoded_user_operations`, `transaction_attributions`.

## What the 2026-11-07 query found

| token | contract | balance | note |
| --- | --- | --- | --- |
| ETH | native | 0.000558 | gas |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 1.0 | |
| gtUSDCp | `0xeE8F4eC5672F09119b96Ab6fB59C27E1b7e44b61` | 77.44 shares x $1.1188 = about $86.64 | Gauntlet USDC Prime (Morpho vault); deposited 2026-11-06. Added to soltui's built-in Base list because Blockscout is often blocked |
| ZORA | `0x1111111111166b7FE7bd91427724B487980aFc69` | 0.1085 (about $0.0006) | dust |
| FLOCK | `0x5aB3D4c385B400F3aBB49e80DE2fAF6a88A7B691` | 12 (about $0.49) | unsolicited; not added |
| USDC-Maxi-PT / -YT | `0xdaa2…341a` / `0x3bAD…c246` | 3,159.73 each | DefiLlama has no price; unverified, not counted |
| sAERO | `0xBF7977E1521e9a3032bf7243Ee4712f311f13915` | 4 wei | dust |

Contracts the owner's own transactions touched in the 14 days to 2026-11-07 include USDC, WETH, the real
cbBTC, AERO (`0x9401…8631`), gtUSDCp, the Aero NonfungiblePositionManager (`0x4857…C60b`) and
SwapRouter (`0x9Ee3…D418`): the liquidity daemon's work.

## SolTUI runtime integration (2026-11-08)

The Wallet tab now uses the same CDP balance endpoint through the locally configured `cdp` CLI.
`soltui/wallet.py:HttpFetcher.base_token_balances` invokes only the fixed read command:

```bash
cdp data evm token-balances base 0x901a89cEC0608eB5435A915f006b45bD46405314 pageSize==100
```

The scanner passes each `nextPageToken` back as `pageToken==...`. It bounds every subprocess by the
scan deadline and stops after 25 pages. The CLI owns authentication; SolTUI never opens its credential
files and never displays its stderr. If the CLI is missing or fails, the summary explains that failure
and the scanner tries paginated Blockscout plus the trusted RPC list. Earlier pages survive a later failure.

Base's current documentation specifies `eth_getBalance(address, "latest")` for native ETH and
`eth_call` to `balanceOf(address)` for a known token. JSON-RPC does not enumerate ERC-20 holdings.
Sources checked live:

- https://docs.base.org/llms-full.txt
- https://docs.base.org/base-chain/api-reference/ethereum-json-rpc-api/eth_getBalance
- https://docs.base.org/build-on-base/issue-rwa/cancel-blocked-units

Trusted and explicitly requested tokens receive RPC checks. Other tokens use indexed balances only,
carry `verified_onchain=false`, and stay excluded until explicitly requested or trusted. This runtime
filter is conservative; the time-bounded SQL recipe above remains useful for investigating which
contracts the owner actually used. Native ETH's indexed sentinel is never called as an ERC-20.
The AERO entry now uses `0x940181a94A35A4569E4529A3CDfB74e38FD98631`, consistent with the owner-query
record above, rather than the unrelated `0x3f5b...` address formerly copied into the wallet list.
