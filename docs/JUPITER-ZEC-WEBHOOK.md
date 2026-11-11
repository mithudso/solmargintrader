# TradingView ZEC → Jupiter Beta perpetuals

Version: 1.0.0. Delta: initial GUM integration contract and activation prerequisites.

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

The previous Coinbase allocation was 75% of available funds. Leverage requires
an explicit allocation basis: 75% collateral at 2x means about 150% notional,
whereas 75% notional at 2x needs about 37.5% collateral, before fees. The service
requires both the leverage and basis; it does not infer them from a TradingView
fill quantity or use the venue's 50x maximum as a default.

GUM holds separate balances. The configured Solana wallet's public identity can
sign GUM Actions, but its Solana balance is not automatically GUM collateral.
The inspected configured wallet has **no GUM perps account and zero GUM balance**.
Jupiter was disconnected in Chrome. No account, deposit or leveraged trade was
created during discovery. A funded, owner-verified cross parent account is
required even for isolated orders. Never send a deposit to a profile public key;
fund only the deposit address and network supplied by the verified account flow.

The former Coinbase listener now runs in inbox-only mode with its KILL file set.
No TradingView alert was created. Jupiter activation requires the owner's account
and leverage/allocation choices, followed by independent installed verification.

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
