# Jupiter1000x public contract observed2026-11-16

The current official application matches program
`yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA` and service
https://yolo-api.jup.ag

Its public frontend uses JSON POST requests without an API-key or login header.
This is an observed application contract, not a published compatibility promise.
The pinned community SDK is `jupiter-sdk`0.6.0.

| Route | Contract used by the integration |
| --- | --- |
| GET `/markets` | paused, minMargin, fees and market symbols/addresses/status |
| GET `/users/{owner}` | open positions, unpaid-profit queued amount and claims |
| POST `/transactions/build` | open: action,owner,market symbol,leverage,long,margin decimal microJupUSD,transactionVersion0; close: action,owner,market,position,transactionVersion0 |
| POST `/transactions/execute` | serializedTxBase64 signed by owner and original buildToken |
| GET `/requests/{txid}` | execution-request status; separate from unpaid profits |

The build returns serializedTxBase64, buildToken, optional positionId and
txMetadata containing blockhash and lastValidBlockHeight. The app requires
v0/v1 message version, an owner fee payer, exactly two signer accounts and a
matching blockhash. After signing it requires unchanged message bytes and
extracts the owner's first signature as the transaction ID. This integration
requests v0 and additionally checks the trade with generated SDK parsers and
builders, verifies on-chain owner/keeper/market accounts, and restricts extra
instructions before allowing the existing CLI wallet to sign.

Execution replies contain txid, status Processing/Completed/Failed, nullable
error execution_failed/execution_window_elapsed and optional queuePosition.
An execution response does not replace chain and current-position checks.
The server's close guard is15seconds; its frontend adds a3second display buffer.

The live public markets response contained these open markets:

| Asset | Market address |
| --- | --- |
| BTC | BXQQo2VTJV2upjdA6qFMGBY3uMyTMnRmaZjPCB5ZVmr7 |
| ZEC | 4ohWGDrmqdiEHinL5Kf2BYzM9UVSe3RJ1bzoveHehiwj |

Observed minMargin was5000000 microJupUSD, closeFeePpm20 and winFeePpm30000.
The adapter fetches current limits instead of treating these values as permanent.

Public source bindings:

https://jup.ag/assets/vendor-tanstack-runtime-CpSF4QMt.js

SHA256 `c453cb92d95310eb8b1ad44d21f11cd2c49b3cb761045ff13bf9114513de05eb`

https://jup.ag/assets/DegenWatchMobile-C4q5Qzmh.js

SHA256 `2ec31117b7727c9d589c3ad557d775d29d531c63d0807298c2ea03ba94d96b01`

An independent GET-only review extracted14 exact source spans and the complete
client schemas. It did not sign or submit transactions. Offline service tests
use deterministic fixture signers; they do not certify a funded fill.
