# TradingView ZEC → Jupiter Beta perpetuals

Version: 1.0.1. Delta: bind the owner-selected ZEC/USDC2x75%collateral policy and prepared Solana/GUM account.

Jupiter offers ZEC long/short perpetuals through its **GUM Beta market**. This is
a separate execution path from Jupiter Swap and the SOL/ETH/wBTC JLP markets.
The webhook treats `buy` as a target long position and `sell` as a target short
position. It does not apply an Oracle prediction, accuracy or timeframe veto.

## Verified upstream contract

The public GUM SDK revision is `08bc398d78350a49ae047ecbdd3ffc6233c082d3`:

- https://github.com/jupnet/gum-perp-sdk
- https://github.com/jupnet/gum-perp-sdk/blob/08bc398d78350a49ae047ecbdd3ffc6233c082d3/docs/REST_API.md
- https://docs.jup.ag/user-docs/trade/perps/beta-markets
- https://docs.gum.ag/llms.txt

Production read-only checks on 2026-11-11 returned HTTP 200 for
`https://api.gum.ag/perps/market/ZEC` and `/health`. The market reported:

| Property | Observed value |
| --- | --- |
| Market | ZEC; USDC margin |
| Maximum venue leverage | 50x; this is not the configured strategy leverage |
| Taker / maker fee | 3.5 / 0.5 bps per side |
| Quantity / price increment | 0.001 ZEC / $0.01 |
| Market order limit | $5 minimum; 25 ZEC and $20,000 maximum |
| Trading health | Available |

Refresh these values before each order. The chart is a CRYPTO:ZECUSD aggregate;
the execution contract is a USDC-margined ZEC perpetual, not a spot USD token
exchange or an implicit swap of USD into USDC.

Orders sign a locally constructed binary Jupnet `Action`, with program ID
`jtxQHH3ysuWRETjaynai3jowPztq2LBJApVFcEv4Wmg`. They do not use the repository's
Jupiter spot transaction verifier. The API reconstructs this Action from the
request fields and verifies the owner's Ed25519 signature. The adapter must
validate account ownership, subaccount, market, lot conversion, side, reduce-only
flag, collateral, price bound and quantity before loading the signer. Signing
an arbitrary server transaction is outside this path.

`POST /order/create` acknowledges an action; it does not prove a fill.
Deterministic client IDs correlate history but are not a documented uniqueness
guarantee. Commit the exact leg before sending once. After an ambiguous result,
reconcile history, fill transactions, open orders and the net position; never
resend automatically. An empty history result does not prove absence.

An opposite signal closes with `reduceOnly` first. The new side is planned from
fresh balances only after the close is fully filled, the position is flat and
collateral has settled. A partial close, unknown submission, account mismatch,
stale signal or pending order prevents the next open. Same-side signals do not
pyramid. IOC execution can leave a partial fill; it must remain visible rather
than silently retrying to reach the requested amount.

## Capital and account requirements

The owner selected **ZEC/USDC, 2x leverage and 75% of available USDC as collateral**. The configured signer is `/Users/mitch/.ssh/solana.private`. Its guarded loader verified that the derived public owner matches the configured wallet without printing key material or signing a transaction. Percentage units are explicit: `--allocation 75 --allocation-basis collateral --leverage 2`. Opening fees and adverse execution reserve reduce size below the nominal150%notional budget; rounding never increases it.

GUM holds separate balances. Native Solana USDC is not automatically GUM collateral. As of2026-11-11, the selected wallet has **0USDC** and **0.009919081SOL**. A dedicated empty GUM cross parent was created through the documented server-paid account endpoint and verified in the owner's account list. No user transaction was signed and no funds were moved. Its exact public account, creation transaction and owner read-back are in the private setup receipt. The live read-only adapter preflight passed; planning a buy refused with `gum_insufficient_collateral`.

The persistent listener is now configured for this Jupiter account and policy in **dry-run**, with a KILL file beside its new inbox. Coinbase execution remains off. No TradingView alert or leveraged order was created. Funding is required before a verified collateral deposit and live activation. A funded account must pass preflight and independent installed/live acceptance.

The personal GUM funding route is documented at https://docs.gum.ag/trading-api/reference/get-deposit-addresses . Its firstGET **creates personal deposit addresses**, so it is a provisioning action rather than a side-effect-free read. The prepared Solana route specifies chain900, the native USDC mint and a $2minimum. Never send a deposit to the profile public key or use another network. Funding the GUM application balance and depositing collateral into its perps parent are distinct steps. The order Action signer does not authorize arbitrary server-built deposit transactions; those still need a verified funding path.

Private owner selection and setup receipts live under `/Users/mitch/.local/state/soloracle-tradingview/zec-usdc-20261111/`. The persistent configuration is `/Users/mitch/.local/state/soloracle-tradingview/deployment.json`; the explicit selection is `/Users/mitch/.local/state/soloracle-tradingview/jupiter-selected-wallet.json`. Neither file contains key material.

## Strategy evidence

The listed 1-minute Volty chart used zero commission and zero slippage. Jupiter's
observed two-sided taker fee is about 0.07% of notional, before spread, slippage
and funding, compared with the displayed average trade expectancy of about 0.09%.
This is only a scale comparison. Lower fees and native shorting correct two
Coinbase mismatches; they do not establish a profitable leveraged strategy.
The historical held-out losses and source/fill-model limits remain recorded in
[the chart review](VOLTY-TRADINGVIEW-ALERT-REVIEW.md). Leverage magnifies the net
result and introduces liquidation; it does not repair a negative trading edge.

Public source snapshots, account preflight and private deployment receipts live
outside Git under `/Users/mitch/.local/state/soloracle-tradingview/jupiter-review-20261111/`.
`discovery-manifest.json` binds their URLs and SHA-256 checksums. No webhook secret,
signed request or private key belongs in this document or any response body.
