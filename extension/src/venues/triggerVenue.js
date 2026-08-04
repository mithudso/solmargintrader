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

  /**
   * Terminal orders. Deliberately NON-strict per record, unlike `getOpenOrders`.
   *
   * The asymmetry is the point. An unreadable *live* list must abort the tick,
   * because planning against a list known to be incomplete is how a rung
   * double-fires. A skipped *history* record can only delay P&L — it can never
   * place an order — so refusing the whole list would trade a recoverable
   * accounting lag for an engine that never ticks again. Unusable records come
   * back flagged and `ingestFills` rejects them individually.
   *
   * The envelope itself is still strict: an unrecognised shape throws here too,
   * because that is the case where we cannot tell an empty history from a
   * misread one.
   */
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
    return normaliseOrders(res, { strict: false, strictEnvelope: true });
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
 * @param {{strict?: boolean, strictEnvelope?: boolean}} [opts] `strict: false`
 *   returns unusable orders flagged instead of throwing, for inspecting a real
 *   response by hand or for the history path (see `getFills`). `strictEnvelope`
 *   keeps envelope-level refusal on while relaxing per-record refusal, which is
 *   the combination the history path wants: an unreadable *shape* is still fatal
 *   because it hides the difference between an empty history and a misread one.
 */
export function normaliseOrders(res, { strict = true, strictEnvelope = strict } = {}) {
  let list = null;
  if (Array.isArray(res)) {
    list = res;
  } else if (res && typeof res === 'object') {
    const present = ORDER_LIST_KEYS.filter((key) => Array.isArray(res[key]));
    if (present.length > 1 && strictEnvelope) {
      // Taking the first match would let `{orders: [], data: [realOrder]}` read as
      // an empty list — the same "nothing is live, re-place every rung" double-fire
      // this function exists to prevent, arriving through a second door. Two
      // candidate lists means we do not know which one is authoritative.
      throw new OrderEnvelopeError(
        `ambiguous orders envelope: ${present.map((k) => `"${k}"`).join(' and ')} both hold arrays ` +
          `(lengths ${present.map((k) => res[k].length).join(', ')}); cannot tell which is authoritative`,
        { observedKeys: Object.keys(res) },
      );
    }
    if (present.length === 1) list = res[present[0]];
  }

  if (list === null) {
    // An absent or unrecognised body is not an empty order list, and treating it
    // as one is the failure this function exists to stop.
    const observedKeys = res && typeof res === 'object' ? Object.keys(res) : [];
    if (strictEnvelope) {
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

    // A price must be POSITIVE, not merely present and finite. `Number('')` is 0
    // and `Number('0')` is 0, so a blank or zero field would otherwise pass as a
    // valid $0 trigger, get adopted into the journal as a phantom rung at an
    // impossible level, and occupy cap space while never matching anything.
    const missingFields = ORDER_REQUIRED_FIELDS.filter((f) => {
      const v = order[f];
      if (v == null) return true;
      if (f === 'triggerPriceUsd') return !(Number.isFinite(v) && v > 0);
      return typeof v === 'number' && !Number.isFinite(v);
    });
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
