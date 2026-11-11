# Jupiter Trigger contract review

Version: 1.0.0. Delta: record the source contract checked during the 2026-11-06 audit.

This review checked public documentation and offline response fixtures. It did not place,
cancel or sign a live order. The extension still installs disarmed in dry-run mode.

## Verified API shapes

- History uses `GET /trigger/v2/orders/history`, `state=active|past`, and `limit`/`offset`.
  Responses include `orders` and `pagination`. The client follows every page, rejects
  changing totals/repeated identities, and refuses incomplete pagination.
  https://developers.jup.ag/docs/api-reference/trigger/order-history
- Order history describes `initialInputAmount` and `remainingInputAmount`, and fill events
  carry the moved mint and amount. An output amount is not a base quantity for a sell.
  History also includes unrelated wallet orders; the adapter checks the configured pair
  and base trigger mint before reconciliation.
  https://developers.jup.ag/docs/trigger/order-history
- Cancellation uses `/orders/price/cancel/{orderId}` and
  `/orders/price/confirm-cancel/{orderId}`. Confirmation sends `signedTransaction` and
  `cancelRequestId`. The adapter checks terminal history before reporting cancellation.
  https://developers.jup.ag/docs/trigger/manage-orders
- Price order creation uses `/orders/price`. Buy sizing converts the USD budget using a
  measured quote-token USD price and validated mint decimals. Deposit and order amounts
  use the same conversion and floor to atomic units. Missing data refuses sizing.
  https://developers.jup.ag/docs/api-reference/trigger/create-order

## Remaining execution evidence

The documented history schema does not guarantee an execution USD price or USD fee.
The adapter does not reinterpret raw token amounts as USD values or use current prices
to rewrite historical fills. An uncertain execution record holds new planning until
its execution valuation and quantity can be established. Active partial execution also
holds planning instead of treating the unbooked inventory as absent.

Only explicit zero-input/zero-output cancelled or expired history with no fill event
can be ignored as unexecuted. Unknown fees remain flagged in every later tick's P&L.
Unknown fees, missing execution timestamps or unusable carry records also hold
admission because a daily-loss comparison cannot be trusted without known costs and timing.

The transport retries read requests only. A failed or lost write response leaves an
unknown intent for reconciliation and operator review. Authentication refresh does not
replay the full write sequence. No automatic write retry is an execution proof.

Live order/fill acceptance, historical USD valuation, fee completeness and wallet-specific
responses remain unverified. These are integration limits, not passing live-test claims.

## Signing remains closed without transaction intent verification

A valid signer slot and Ed25519 signature do not establish what a transaction does.
The bundled session-key signer deliberately provides no automatic Trigger economic-intent
verifier. The adapter refuses raw signing and reports `live-transaction-verifier-required`.
Dry-run does not use that write path.

A trusted signing bridge must independently verify binary instructions, source/destination
accounts, allowed programs, token amounts, fee/debit ceilings, lookup-table resolutions
and the expected operation before signing. A remote response echo is not proof. The
adapter accepts only explicit `signVerifiedTriggerDeposit` and
`signVerifiedTriggerCancellation` bridge operations for these transactions. No bundled
implementation currently supplies them. This audit did not invent support for an unseen
live transaction template.
