/**
 * Jupiter Trigger V2 client.
 *
 * Endpoint shapes below are transcribed from the live docs (verified
 * 2026-08-04):
 *   https://developers.jup.ag/docs/trigger
 *   https://developers.jup.ag/docs/trigger/create-order
 *   https://developers.jup.ag/docs/trigger/authentication
 *   https://developers.jup.ag/docs/trigger/deposit
 *   https://developers.jup.ag/docs/trigger/manage-orders
 *
 * Flow: authenticate -> resolve vault -> craft deposit -> sign deposit ->
 * create order. The deposit `requestId` is single-use and is consumed by the
 * create call.
 *
 * Every authenticated endpoint needs BOTH `x-api-key` and a JWT bearer token.
 */

import { request, headers, JupiterHttpError } from './http.js';

export const TRIGGER_BASE = 'https://api.jup.ag/trigger/v2';

/** Venue constraints, enforced client-side so a bad order never costs a request. */
export const TRIGGER_LIMITS = Object.freeze({
  minOrderUsd: 10,
  slippageBpsMin: 0,
  slippageBpsMax: 10_000,
  trailingBpsMin: 50,
  trailingBpsMax: 9_000,
});

export const ORDER_TYPE = { SINGLE: 'single', OCO: 'oco', OTOCO: 'otoco' };
export const CONDITION = { ABOVE: 'above', BELOW: 'below' };

/* ------------------------------------------------------------------ auth ---- */

/**
 * Step 1 of authentication: fetch the challenge string to sign.
 * @returns {Promise<{challenge:string}>}
 */
export function getChallenge({ walletPubkey, apiKey, budget, fetchImpl }) {
  return request({
    url: `${TRIGGER_BASE}/auth/challenge`,
    init: {
      method: 'POST',
      headers: headers({ apiKey }),
      body: JSON.stringify({ walletPubkey, type: 'message' }),
    },
    budget,
    fetchImpl,
  });
}

/**
 * Step 2: exchange the signed challenge for a JWT (24h lifetime per docs).
 * @param {string} signatureBs58 base58 of the detached Ed25519 signature
 * @returns {Promise<{token:string}>}
 */
export function verifyChallenge({ walletPubkey, signatureBs58, apiKey, budget, fetchImpl }) {
  return request({
    url: `${TRIGGER_BASE}/auth/verify`,
    init: {
      method: 'POST',
      headers: headers({ apiKey }),
      body: JSON.stringify({ type: 'message', walletPubkey, signature: signatureBs58 }),
    },
    budget,
    fetchImpl,
  });
}

/* ----------------------------------------------------------------- vault ---- */

/**
 * Resolve the caller's vault, registering one on first use.
 *
 * The vault is a Privy-managed custodial account, one per wallet, shared by all
 * orders. Its address is derived from the JWT, so it is never passed explicitly.
 */
export async function resolveVault({ apiKey, jwt, budget, fetchImpl }) {
  const h = headers({ apiKey, jwt });
  try {
    return await request({ url: `${TRIGGER_BASE}/vault`, init: { headers: h }, budget, fetchImpl });
  } catch (err) {
    if (!(err instanceof JupiterHttpError)) throw err;
    // No vault yet on this wallet: register once, then it persists.
    return request({
      url: `${TRIGGER_BASE}/vault/register`,
      init: { headers: h },
      budget,
      fetchImpl,
    });
  }
}

/* --------------------------------------------------------------- deposit ---- */

/**
 * Craft the deposit transaction that funds an order.
 *
 * `orderSubType` must match the `orderType` used on the subsequent create call —
 * a mismatch is rejected at create time, after the craft request is spent.
 *
 * @returns {Promise<{requestId:string, transaction:string}>} transaction is a
 *   base64 VersionedTransaction awaiting the wallet's signature.
 */
export function craftDeposit({
  inputMint,
  outputMint,
  userAddress,
  amount, // smallest unit, string
  orderSubType = ORDER_TYPE.SINGLE,
  apiKey,
  jwt,
  budget,
  fetchImpl,
}) {
  return request({
    url: `${TRIGGER_BASE}/deposit/craft`,
    init: {
      method: 'POST',
      headers: headers({ apiKey, jwt }),
      body: JSON.stringify({
        inputMint,
        outputMint,
        userAddress,
        amount: String(amount),
        orderType: 'price', // deposit-level type: 'price' | 'dca'
        orderSubType,
      }),
    },
    budget,
    fetchImpl,
  });
}

/* ---------------------------------------------------------------- orders ---- */

/**
 * Map a planned grid rung to a Trigger V2 `single` price-order body.
 *
 * Direction mapping, matching the doc examples:
 *   buy  rung -> spend quote, receive base, trigger BELOW the level
 *   sell rung -> spend base,  receive quote, trigger ABOVE the level
 * `triggerMint` is the base mint either way: the level is a price of base in USD.
 */
export function rungToOrderBody({
  intent,
  baseMint,
  quoteMint,
  baseDecimals,
  quoteDecimals,
  userPubkey,
  depositRequestId,
  depositSignedTx,
  slippageBps,
  expiresAt,
}) {
  const isBuy = intent.side === 'buy';
  const inputMint = isBuy ? quoteMint : baseMint;
  const outputMint = isBuy ? baseMint : quoteMint;
  const inputAmount = isBuy
    ? toSmallestUnit(intent.notionalUsd, quoteDecimals)
    : toSmallestUnit(intent.baseQty, baseDecimals);

  return {
    orderType: ORDER_TYPE.SINGLE,
    depositRequestId,
    depositSignedTx,
    userPubkey,
    inputMint,
    outputMint,
    inputAmount,
    triggerMint: baseMint,
    triggerCondition: isBuy ? CONDITION.BELOW : CONDITION.ABOVE,
    triggerPriceUsd: intent.level,
    slippageBps,
    expiresAt,
  };
}

/**
 * Integer amount in the token's smallest unit.
 *
 * Built as a string via rounding on a scaled integer: `1e9 * 0.1` in float math
 * lands on 100000000.00000001, and Solana rejects a non-integer amount.
 */
export function toSmallestUnit(amount, decimals) {
  if (!Number.isFinite(amount) || amount < 0) {
    throw new RangeError(`amount must be a non-negative finite number, got ${amount}`);
  }
  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 18) {
    throw new RangeError(`decimals must be an integer 0-18, got ${decimals}`);
  }
  const scaled = Math.round(amount * 10 ** decimals);
  if (!Number.isSafeInteger(scaled)) {
    throw new RangeError(`amount ${amount} at ${decimals} decimals exceeds safe integer range`);
  }
  return String(scaled);
}

/** Client-side validation mirroring the documented server rules. */
export function validateOrderBody(body) {
  const problems = [];
  if (body.inputMint === body.outputMint) problems.push('inputMint and outputMint must differ');
  if (!(body.expiresAt > Date.now())) problems.push('expiresAt must be a future timestamp in ms');
  if (
    body.slippageBps != null &&
    (body.slippageBps < TRIGGER_LIMITS.slippageBpsMin || body.slippageBps > TRIGGER_LIMITS.slippageBpsMax)
  ) {
    problems.push(`slippageBps must be ${TRIGGER_LIMITS.slippageBpsMin}-${TRIGGER_LIMITS.slippageBpsMax}`);
  }
  const hasStatic = body.triggerPriceUsd != null;
  const hasTrailing = body.trailingBps != null;
  if (hasStatic === hasTrailing) {
    problems.push('set exactly one of triggerPriceUsd or trailingBps');
  }
  if (hasTrailing) {
    if (body.trailingBps < TRIGGER_LIMITS.trailingBpsMin || body.trailingBps > TRIGGER_LIMITS.trailingBpsMax) {
      problems.push(`trailingBps must be ${TRIGGER_LIMITS.trailingBpsMin}-${TRIGGER_LIMITS.trailingBpsMax}`);
    }
    // Documented trailing-only rule: triggerMint must be the inputMint for a
    // 'below' trail and the outputMint for 'above'. Checked here so the failure
    // costs no request.
    const expected = body.triggerCondition === CONDITION.BELOW ? body.inputMint : body.outputMint;
    if (body.triggerMint !== expected) {
      problems.push(
        `for a trailing ${body.triggerCondition} order triggerMint must be the ${
          body.triggerCondition === CONDITION.BELOW ? 'inputMint' : 'outputMint'
        }`,
      );
    }
  }
  if (body.orderType === ORDER_TYPE.OCO || body.orderType === ORDER_TYPE.OTOCO) {
    if (!(body.tpPriceUsd > body.slPriceUsd)) {
      problems.push('take-profit price must exceed stop-loss price');
    }
  }
  return problems;
}

/**
 * Create a price order.
 * @returns {Promise<{id:string, txSignature:string, depositConfirmed:boolean}>}
 */
export function createPriceOrder({ body, apiKey, jwt, budget, fetchImpl }) {
  const problems = validateOrderBody(body);
  if (problems.length) {
    throw new RangeError(`invalid trigger order: ${problems.join('; ')}`);
  }
  return request({
    url: `${TRIGGER_BASE}/orders/price`,
    init: { method: 'POST', headers: headers({ apiKey, jwt }), body: JSON.stringify(body) },
    budget,
    fetchImpl,
  });
}

/** Open/historical orders — the reconciliation and fill source. */
export function listOrders({ apiKey, jwt, status, budget, fetchImpl }) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : '';
  return request({
    url: `${TRIGGER_BASE}/orders${qs}`,
    init: { headers: headers({ apiKey, jwt }) },
    budget,
    fetchImpl,
  });
}

/** Update a resting order in place (trigger price and slippage only). */
export function updateOrder({ orderId, triggerPriceUsd, slippageBps, trailingBps, apiKey, jwt, budget, fetchImpl }) {
  const patch = {};
  if (triggerPriceUsd != null) patch.triggerPriceUsd = triggerPriceUsd;
  if (slippageBps != null) patch.slippageBps = slippageBps;
  if (trailingBps != null) patch.trailingBps = trailingBps;
  return request({
    url: `${TRIGGER_BASE}/orders/${encodeURIComponent(orderId)}`,
    init: { method: 'PATCH', headers: headers({ apiKey, jwt }), body: JSON.stringify(patch) },
    budget,
    fetchImpl,
  });
}

/**
 * Cancellation is a two-step flow: initiate, sign the returned withdrawal, then
 * confirm. Funds stay in the vault until the confirm lands.
 */
export function initiateCancel({ orderId, apiKey, jwt, budget, fetchImpl }) {
  return request({
    url: `${TRIGGER_BASE}/orders/${encodeURIComponent(orderId)}/cancel`,
    init: { method: 'POST', headers: headers({ apiKey, jwt }) },
    budget,
    fetchImpl,
  });
}

export function confirmCancel({ orderId, signedTx, apiKey, jwt, budget, fetchImpl }) {
  return request({
    url: `${TRIGGER_BASE}/orders/${encodeURIComponent(orderId)}/cancel/confirm`,
    init: { method: 'POST', headers: headers({ apiKey, jwt }), body: JSON.stringify({ signedTx }) },
    budget,
    fetchImpl,
  });
}
