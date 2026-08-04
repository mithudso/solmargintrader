/**
 * Jupiter Trigger V2 venue adapter.
 *
 * This is the only venue that can currently place live orders: Trigger returns
 * a signable transaction over HTTP. A grid is a ladder of resting price orders,
 * which is exactly what this API is for, and V2 keeps pending orders off-chain
 * so the ladder is not a public roadmap for front-runners.
 *
 * Leverage note: Trigger is a SPOT venue. `leverage > 1` cannot be produced
 * here — see `marginSource` below.
 */

import * as trigger from '../jupiter/trigger.js';
import { getPrices, getDecimals } from '../jupiter/price.js';

export const MARGIN_SOURCE = {
  NONE: 'none', // spot, unleveraged
  JUP_LEND: 'jup-lend', // borrow quote/base from Jupiter Lend, then grid the borrowed size
};

export class TriggerVenue {
  /**
   * @param {object} cfg
   * @param {string} cfg.baseMint
   * @param {string} cfg.quoteMint
   * @param {string} cfg.userPubkey
   * @param {object} cfg.signer   see SigningBridge — supplies signMessage/signTransaction
   */
  constructor({ baseMint, quoteMint, userPubkey, apiKey, signer, budget, fetchImpl }) {
    this.id = 'jupiter-trigger-v2';
    this.kind = 'spot';
    this.baseMint = baseMint;
    this.quoteMint = quoteMint;
    this.userPubkey = userPubkey;
    this.apiKey = apiKey;
    this.signer = signer;
    this.budget = budget;
    this.fetchImpl = fetchImpl;
    this.jwt = null;
    this.jwtExpiresAtMs = 0;
    this.decimals = null;
  }

  get capabilities() {
    return {
      canPlaceLive: true,
      supportsLeverage: false, // spot only; leverage requires a borrow source
      supportsUpdateInPlace: true, // trigger price + slippage, no cancel/recreate
      supportsBrackets: true, // OCO / OTOCO
      minOrderUsd: trigger.TRIGGER_LIMITS.minOrderUsd,
      ordersArePrivate: true, // V2 keeps pending orders off-chain
    };
  }

  /* ------------------------------------------------------------- read side -- */

  async getPrice() {
    const prices = await getPrices({
      mints: [this.baseMint],
      apiKey: this.apiKey,
      budget: this.budget,
      fetchImpl: this.fetchImpl,
    });
    const price = prices[this.baseMint];
    if (!price) throw new Error(`no price returned for ${this.baseMint}`);
    return price;
  }

  /**
   * Token decimals, read from the price response rather than hardcoded.
   * Goes through the shared http layer so it inherits retry, timeout and budget.
   */
  async getDecimals() {
    if (this.decimals) return this.decimals;
    const table = await getDecimals({
      mints: [this.baseMint, this.quoteMint],
      apiKey: this.apiKey,
      budget: this.budget,
      fetchImpl: this.fetchImpl,
    });
    // SPL norms as a last resort; a missing mint must not produce `undefined`
    // decimals, which would make toSmallestUnit throw mid-order.
    this.decimals = {
      base: table[this.baseMint] ?? 9,
      quote: table[this.quoteMint] ?? 6,
    };
    return this.decimals;
  }

  /**
   * Live order state. This is the reconciliation source of truth — local
   * records are only a cache, because a service worker can die mid-submit.
   */
  async getOpenOrders() {
    const res = await this.#authed(() =>
      trigger.listOrders({
        apiKey: this.apiKey,
        jwt: this.jwt,
        status: 'active',
        budget: this.budget,
        fetchImpl: this.fetchImpl,
      }),
    );
    return normaliseOrders(res);
  }

  async getFills() {
    const res = await this.#authed(() =>
      trigger.listOrders({
        apiKey: this.apiKey,
        jwt: this.jwt,
        status: 'history',
        budget: this.budget,
        fetchImpl: this.fetchImpl,
      }),
    );
    return normaliseOrders(res);
  }

  /** Trigger charges no carry: a resting spot order has no funding leg. */
  async getCarryCosts() {
    return [];
  }

  /* ------------------------------------------------------------ write side -- */

  /**
   * Place one planned rung. Four calls: auth (cached), vault (cached), craft
   * deposit, create order — with the deposit signed in between.
   *
   * The caller must have already persisted the intent, because the deposit
   * lands on-chain during the create call: a crash after this point leaves real
   * state that reconciliation has to find.
   */
  async placeOrder({ intent, slippageBps, ttlMs }) {
    // Wrapped so a rejected token re-authenticates and retries once. Re-running
    // the whole sequence is safe: craftDeposit only BUILDS a transaction — the
    // deposit does not land until the create call — so a discarded requestId
    // costs nothing on chain.
    return this.#authed(() => this.#placeOrderOnce({ intent, slippageBps, ttlMs }));
  }

  async #placeOrderOnce({ intent, slippageBps, ttlMs }) {
    await this.#ensureVault();
    const dec = await this.getDecimals();

    const isBuy = intent.side === 'buy';
    const inputMint = isBuy ? this.quoteMint : this.baseMint;
    const outputMint = isBuy ? this.baseMint : this.quoteMint;
    const amount = isBuy
      ? trigger.toSmallestUnit(intent.notionalUsd, dec.quote)
      : trigger.toSmallestUnit(intent.baseQty, dec.base);

    const deposit = await trigger.craftDeposit({
      inputMint,
      outputMint,
      userAddress: this.userPubkey,
      amount,
      orderSubType: trigger.ORDER_TYPE.SINGLE,
      apiKey: this.apiKey,
      jwt: this.jwt,
      budget: this.budget,
      fetchImpl: this.fetchImpl,
    });
    if (!deposit?.requestId) {
      throw new Error(`deposit craft returned no requestId: ${JSON.stringify(deposit).slice(0, 200)}`);
    }

    const depositSignedTx = await this.signer.signTransactionBase64(deposit.transaction);

    const body = trigger.rungToOrderBody({
      intent,
      baseMint: this.baseMint,
      quoteMint: this.quoteMint,
      baseDecimals: dec.base,
      quoteDecimals: dec.quote,
      userPubkey: this.userPubkey,
      depositRequestId: deposit.requestId,
      depositSignedTx,
      slippageBps,
      expiresAt: Date.now() + ttlMs,
    });

    const order = await trigger.createPriceOrder({
      body,
      apiKey: this.apiKey,
      jwt: this.jwt,
      budget: this.budget,
      fetchImpl: this.fetchImpl,
    });

    return {
      venueOrderId: order.id,
      txSignature: order.txSignature,
      confirmed: order.depositConfirmed === true,
    };
  }

  async cancelOrder({ venueOrderId }) {
    return this.#authed(() => this.#cancelOrderOnce({ venueOrderId }));
  }

  async #cancelOrderOnce({ venueOrderId }) {
    const initiated = await trigger.initiateCancel({
      orderId: venueOrderId,
      apiKey: this.apiKey,
      jwt: this.jwt,
      budget: this.budget,
      fetchImpl: this.fetchImpl,
    });
    // Withdrawal has to be signed before funds leave the vault.
    if (initiated?.transaction) {
      const signedTx = await this.signer.signTransactionBase64(initiated.transaction);
      return trigger.confirmCancel({
        orderId: venueOrderId,
        signedTx,
        apiKey: this.apiKey,
        jwt: this.jwt,
        budget: this.budget,
        fetchImpl: this.fetchImpl,
      });
    }
    return initiated;
  }

  /* --------------------------------------------------------------- private -- */

  /**
   * Run an authenticated call, re-authenticating once if the token is rejected.
   *
   * The 24h JWT lifetime is an assumption taken from the docs, not something the
   * server tells us. Without this, one stale or server-invalidated token fails
   * every subsequent tick forever: the intent is journalled FAILED, re-planned
   * next tick, and fails again on the same dead token.
   */
  async #authed(fn) {
    await this.#ensureAuth();
    try {
      return await fn();
    } catch (err) {
      if (err?.status !== 401 && err?.status !== 403) throw err;
      this.jwt = null;
      this.jwtExpiresAtMs = 0;
      await this.#ensureAuth();
      return fn();
    }
  }

  async #ensureAuth() {
    // Docs put the JWT at 24h; refresh an hour early rather than on failure.
    if (this.jwt && Date.now() < this.jwtExpiresAtMs - 3_600_000) return;
    const { challenge } = await trigger.getChallenge({
      walletPubkey: this.userPubkey,
      apiKey: this.apiKey,
      budget: this.budget,
      fetchImpl: this.fetchImpl,
    });
    const signatureBs58 = await this.signer.signMessageBs58(challenge);
    const { token } = await trigger.verifyChallenge({
      walletPubkey: this.userPubkey,
      signatureBs58,
      apiKey: this.apiKey,
      budget: this.budget,
      fetchImpl: this.fetchImpl,
    });
    if (!token) throw new Error('auth/verify returned no token');
    this.jwt = token;
    this.jwtExpiresAtMs = Date.now() + 24 * 3_600_000;
  }

  async #ensureVault() {
    if (this.vault) return this.vault;
    this.vault = await trigger.resolveVault({
      apiKey: this.apiKey,
      jwt: this.jwt,
      budget: this.budget,
      fetchImpl: this.fetchImpl,
    });
    return this.vault;
  }
}

/**
 * Raised when the orders endpoint returns a shape this client does not
 * recognise, or an order missing a field reconciliation depends on.
 *
 * Carries the observed key names — never the values — because this error is
 * logged, and an order body can hold wallet addresses.
 */
export class OrderEnvelopeError extends Error {
  constructor(message, { observedKeys = [], missingFields = [], index = null } = {}) {
    super(message);
    this.name = 'OrderEnvelopeError';
    this.observedKeys = observedKeys;
    this.missingFields = missingFields;
    this.index = index;
  }
}

/** The only list envelopes this client accepts. Anything else is refused. */
export const ORDER_LIST_KEYS = ['orders', 'data'];

/**
 * Fields reconciliation cannot work without.
 *
 * `matchIntent` and `keyForLiveOrder` both bail on a null side or trigger price,
 * so an order missing either is invisible to reconciliation — and an invisible
 * live order is one the planner will happily place a second time.
 */
export const ORDER_REQUIRED_FIELDS = ['venueOrderId', 'side', 'triggerPriceUsd'];

/**
 * Map the orders endpoint's response onto the shape the engine consumes.
 *
 * The envelope is still the least-verified part of this client (see
 * README "Not verified" #2), which is exactly why this refuses rather than
 * shrugs. Two failure modes used to be silent and are now loud:
 *
 *   - An unrecognised envelope produced `[]`, which reconciliation reads as
 *     "nothing is live" — so every resting rung looks orphaned and gets
 *     re-planned. That is the double-fire path CLAUDE.md non-negotiable #4
 *     exists to prevent, arrived at from the read side.
 *   - A missing fee became `0`. Zero fees make a grid look better than it is,
 *     so the fee stays `null` with `feeUnknown` set, and the caller decides.
 *
 * Throwing is safe here: `tick()` wraps its whole body, so an envelope it cannot
 * read aborts the tick before anything is planned or placed. Failing closed on a
 * shape change is the whole point.
 *
 * @param {unknown} res raw response body
 * @param {{strict?: boolean}} [opts] `strict: false` returns unusable orders
 *   flagged instead of throwing, for inspecting a real response by hand.
 */
export function normaliseOrders(res, { strict = true } = {}) {
  let list = null;
  if (Array.isArray(res)) {
    list = res;
  } else if (res && typeof res === 'object') {
    for (const key of ORDER_LIST_KEYS) {
      if (Array.isArray(res[key])) {
        list = res[key];
        break;
      }
    }
  }

  if (list === null) {
    // An absent or unrecognised body is not an empty order list, and treating it
    // as one is the failure this function exists to stop.
    const observedKeys = res && typeof res === 'object' ? Object.keys(res) : [];
    if (strict) {
      throw new OrderEnvelopeError(
        `unrecognised orders envelope: expected an array or one of ` +
          `${ORDER_LIST_KEYS.map((k) => `"${k}"`).join(', ')}, got ` +
          (observedKeys.length ? `keys [${observedKeys.join(', ')}]` : typeof res),
        { observedKeys },
      );
    }
    return [];
  }

  return list.map((o, index) => {
    const order = {
      venueOrderId: o?.id ?? o?.orderId ?? null,
      status: o?.status ?? null,
      // null, not a default of 'sell': guessing a side would let reconcile adopt
      // an order as the wrong direction, and a wrong-side adoption is worse than
      // an unmatched one.
      side:
        o?.triggerCondition === 'below' ? 'buy' : o?.triggerCondition === 'above' ? 'sell' : null,
      triggerPriceUsd: num(o?.triggerPriceUsd),
      inputMint: o?.inputMint,
      outputMint: o?.outputMint,
      inputAmount: o?.inputAmount,
      filledBaseQty: num(o?.filledOutputAmount ?? o?.filledAmount),
      executedPriceUsd: num(o?.executedPriceUsd ?? o?.avgPriceUsd),
      feeUsd: num(o?.feeUsd ?? o?.totalFeeUsd),
      createdAtMs: toMs(o?.createdAt),
      updatedAtMs: toMs(o?.updatedAt ?? o?.filledAt),
      raw: o,
    };
    order.feeUnknown = !Number.isFinite(order.feeUsd);

    const missingFields = ORDER_REQUIRED_FIELDS.filter(
      (f) => order[f] == null || (typeof order[f] === 'number' && !Number.isFinite(order[f])),
    );
    if (missingFields.length) {
      const observedKeys = o && typeof o === 'object' ? Object.keys(o) : [];
      if (strict) {
        throw new OrderEnvelopeError(
          `order at index ${index} is missing ${missingFields.join(', ')}; ` +
            `reconciliation cannot match it, so planning would risk re-placing a ` +
            `live rung. Observed keys: [${observedKeys.join(', ')}]`,
          { observedKeys, missingFields, index },
        );
      }
      order.unusable = true;
      order.missingFields = missingFields;
    }
    return order;
  });
}

const num = (v) => (v == null ? null : Number(v));
const toMs = (v) => {
  if (v == null) return null;
  if (typeof v === 'number') return v;
  const t = Date.parse(v);
  return Number.isFinite(t) ? t : null;
};
