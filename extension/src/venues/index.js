/**
 * Venue layer.
 *
 * The grid engine is venue-agnostic: it emits intents, and a venue adapter
 * turns them into orders. That seam exists because the two candidate venues on
 * Jupiter are in very different states of readiness:
 *
 *   Trigger V2  — REST, returns signable transactions. Live-capable today. SPOT.
 *   Perps       — NO public REST write API as of 2026-08-04. Jupiter's own docs
 *                 say "The Perps API is still a work in progress" and point at
 *                 Anchor IDL parsing of the on-chain program. Read-only here;
 *                 writes throw rather than pretend.
 *
 * VenueAdapter contract:
 *   get capabilities()                  -> {canPlaceLive, supportsLeverage, minOrderUsd, ...}
 *   getPrice()                          -> number (USD)
 *   getDecimals()                       -> {base, quote}
 *   getOpenOrders()                     -> NormalisedOrder[]
 *   getFills()                          -> NormalisedOrder[]
 *   getCarryCosts()                     -> [{tsMs, costUsd}]
 *   placeOrder({intent, slippageBps, ttlMs}) -> {venueOrderId, txSignature, confirmed}
 *   cancelOrder({venueOrderId})         -> unknown
 */

import { TriggerVenue, MARGIN_SOURCE } from './triggerVenue.js';

export { TriggerVenue, MARGIN_SOURCE };

export const MODE = {
  DRY_RUN: 'dry-run', // default: real prices, simulated fills, zero writes
  SEMI_AUTO: 'semi-auto', // real orders, every signature approved by hand
  FULL_AUTO: 'full-auto', // real orders, signed by a dedicated session key
};

/**
 * Wraps any venue so reads stay live but writes are simulated.
 *
 * Fills are modelled pessimistically: a rung fills at its trigger price moved
 * against us by the full slippage allowance, plus a fee. An optimistic
 * simulator is worse than none, because it makes a losing grid look profitable.
 */
export class DryRunVenue {
  constructor({ inner, feeBps = 10, clock = () => Date.now() }) {
    this.inner = inner;
    this.feeBps = feeBps;
    this.clock = clock;
    this.id = `dry-run(${inner.id})`;
    this.kind = inner.kind;
    this.simulated = [];
  }

  get capabilities() {
    return { ...this.inner.capabilities, canPlaceLive: false, dryRun: true };
  }

  getPrice() {
    return this.inner.getPrice();
  }

  getDecimals() {
    return this.inner.getDecimals();
  }

  async getOpenOrders() {
    return this.simulated.filter((o) => o.status === 'active');
  }

  async getFills() {
    return this.simulated.filter((o) => o.status === 'filled');
  }

  async getCarryCosts() {
    return this.inner.getCarryCosts();
  }

  async placeOrder({ intent, slippageBps, ttlMs }) {
    if (ttlMs !== undefined && (!Number.isFinite(ttlMs) || ttlMs <= 0)) throw new RangeError('paper order TTL must be positive');
    const id = `sim-${intent.intentKey}-${this.clock()}`;
    this.simulated.push({
      venueOrderId: id,
      status: 'active',
      expiresAtMs: ttlMs === undefined ? null : this.clock() + ttlMs,
      side: intent.side,
      triggerPriceUsd: intent.level,
      intentKey: intent.intentKey,
      slippageBps,
      // Carried so the fill can report its own quantity and fee. Absent when
      // the intent has no usable size: the fill then reports neither, and the
      // engine falls back to the journal quantity and flags the fee unknown
      // rather than this simulator guessing a number.
      baseQty: Number.isFinite(intent.baseQty) && intent.baseQty > 0 ? intent.baseQty : undefined,
      createdAtMs: this.clock(),
    });
    return { venueOrderId: id, txSignature: null, confirmed: true, simulated: true };
  }

  async cancelOrder({ venueOrderId }) {
    const o = this.simulated.find((x) => x.venueOrderId === venueOrderId);
    if (o) o.status = 'cancelled';
    return { cancelled: Boolean(o), simulated: true };
  }

  /**
   * Advance the simulation against a new price, filling any resting rung the
   * market has crossed.
   */
  markPrice(price) {
    const fills = [];
    for (const o of this.simulated) {
      if (o.status !== 'active') continue;
      if (o.expiresAtMs !== null && Number.isFinite(o.expiresAtMs) && this.clock() >= o.expiresAtMs) { o.status = 'expired'; o.updatedAtMs = this.clock(); continue; }
      const crossed =
        (o.side === 'buy' && price <= o.triggerPriceUsd) ||
        (o.side === 'sell' && price >= o.triggerPriceUsd);
      if (!crossed) continue;

      // Slip against us by the full allowance: buys pay up, sells receive less.
      const slipFactor = 1 + ((o.side === 'buy' ? 1 : -1) * (o.slippageBps ?? 0)) / 10_000;
      const executedPriceUsd = o.triggerPriceUsd * slipFactor;
      o.status = 'filled';
      o.executedPriceUsd = executedPriceUsd;
      if (o.baseQty !== undefined) {
        // Fee on the notional actually traded, at the slipped price. A dry run
        // that fills for free overstates every grid's edge by two fees a round
        // trip, which is exactly the lie this venue exists to avoid.
        o.filledBaseQty = o.baseQty;
        o.feeUsd = (o.baseQty * executedPriceUsd * this.feeBps) / 10_000;
      }
      o.updatedAtMs = this.clock();
      fills.push(o);
    }
    return fills;
  }
}

/**
 * Read-only Perps venue.
 *
 * Deliberately incomplete. Position reads can be added by decoding the perps
 * program's position accounts over RPC (see the Anchor IDL parsing repo Jupiter
 * links from its Perps docs). Writes are NOT implementable over REST today, so
 * they throw a message that says exactly why instead of failing obscurely at
 * submit time.
 */
export class PerpsVenueReadOnly {
  constructor({ baseMint, quoteMint, rpcUrl } = {}) {
    this.id = 'jupiter-perps-readonly';
    this.kind = 'perps';
    this.baseMint = baseMint;
    this.quoteMint = quoteMint;
    this.rpcUrl = rpcUrl;
  }

  get capabilities() {
    return {
      canPlaceLive: false,
      supportsLeverage: true,
      supportsUpdateInPlace: false,
      supportsBrackets: true,
      minOrderUsd: null,
      readOnlyReason:
        'Jupiter Perps has no public REST write API (docs, 2026-08-04: "The Perps API is still a work in progress"). Opening or closing a position requires building Anchor instructions against the perps program and going through its keeper request/fulfil flow.',
    };
  }

  async getPrice() {
    throw new NotImplemented('getPrice', 'wire an oracle or the Price API mark for the perps market');
  }

  async getDecimals() {
    return { base: 9, quote: 6 };
  }

  async getOpenOrders() {
    throw new NotImplemented(
      'getOpenOrders',
      'decode perps position accounts via RPC getProgramAccounts + the perps IDL',
    );
  }

  async getFills() {
    throw new NotImplemented('getFills', 'parse position-change events from transaction logs');
  }

  async getCarryCosts() {
    throw new NotImplemented(
      'getCarryCosts',
      'read the borrow rate from the perps custody account — do NOT assume a symmetric CEX-style funding rate',
    );
  }

  async placeOrder() {
    throw new NotImplemented('placeOrder', this.capabilities.readOnlyReason);
  }

  async cancelOrder() {
    throw new NotImplemented('cancelOrder', this.capabilities.readOnlyReason);
  }
}

export class NotImplemented extends Error {
  constructor(op, how) {
    super(`${op} is not implemented for this venue. To finish it: ${how}`);
    this.name = 'NotImplemented';
    this.operation = op;
  }
}

/**
 * Build the venue stack for a config.
 *
 * DRY_RUN wraps the real adapter rather than replacing it, so a dry run
 * exercises the same price and decimals code paths that a live run would.
 */
export function buildVenue({ config, signer, apiKey, budget, fetchImpl }) {
  const { venue = 'trigger', mode = MODE.DRY_RUN, baseMint, quoteMint, userPubkey, rpcUrl } = config;

  let inner;
  if (venue === 'perps') {
    inner = new PerpsVenueReadOnly({ baseMint, quoteMint, rpcUrl });
  } else if (venue === 'trigger') {
    inner = new TriggerVenue({ baseMint, quoteMint, userPubkey, apiKey, signer, budget, fetchImpl });
  } else {
    // An unrecognised name must not fall through to a live-capable venue: a
    // config that says "kraken" and silently trades on Jupiter is a wrong-venue
    // order with real money.
    throw new Error(`unknown venue "${venue}": expected "trigger" or "perps"`);
  }

  if (mode === MODE.DRY_RUN) return new DryRunVenue({ inner });

  if (!inner.capabilities.canPlaceLive) {
    throw new Error(
      `venue "${venue}" cannot place live orders: ${inner.capabilities.readOnlyReason ?? 'unsupported'}`,
    );
  }
  return inner;
}

/**
 * Whether a requested leverage is actually achievable on this venue.
 * Returns a reason string when it is not, so the UI can explain the refusal
 * instead of silently trading unleveraged while the config claims 3x.
 */
export function leverageFeasibility({ venue, leverage, marginSource }) {
  if (leverage <= 1) return { ok: true };
  if (venue.capabilities.supportsLeverage) return { ok: true };
  if (marginSource === MARGIN_SOURCE.JUP_LEND) {
    return {
      ok: false,
      reason:
        'Leverage via Jupiter Lend is not wired up yet: the grid would need to borrow against collateral before placing rungs, and track the borrow rate as a carry cost. Not implemented — see README "Leverage".',
    };
  }
  return {
    ok: false,
    reason: `${venue.id} is a spot venue with no borrow source, so leverage ${leverage}x is unreachable. Set leverage to 1, or supply marginSource.`,
  };
}
