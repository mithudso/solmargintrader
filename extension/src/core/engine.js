/**
 * The tick.
 *
 * Order of operations is the whole design: RECONCILE before PLAN, always.
 *
 * A MV3 service worker can be killed at any moment, including between "write
 * the intent" and "the venue accepted the order". So the venue's live order
 * list — not our local records — is the source of truth at the top of every
 * tick. Local state is a cache and a journal, nothing more.
 *
 * Dependencies are injected (venue, store, config, clock) so the whole tick can
 * be driven headless in tests and in tools/dryrun.js without Chrome.
 */

import { planGrid, intentKey } from './grid.js';
import { admitBatch, dayKey, DEFAULT_LIMITS } from './risk.js';
import { snapshot } from './pnl.js';
import { INTENT_STATUS } from '../storage/store.js';

/**
 * Relative tolerance for matching a venue's echoed trigger price to ours.
 *
 * 1 basis point. Exact key equality is NOT safe here: intentKey rounds to
 * level * 1e6, so a level of 69.238424 keys as 69238424 while a venue that
 * echoes `69.2384` keys as 69238400. Those are different keys for the same
 * order, and treating them as different orphans the resting rung AND re-plans
 * it — the double-fire the write-ahead journal exists to prevent.
 */
const PRICE_MATCH_TOLERANCE = 1e-4;

export function pricesMatch(a, b) {
  if (a == null || b == null) return false;
  const scale = Math.max(Math.abs(a), Math.abs(b), 1e-9);
  return Math.abs(a - b) / scale <= PRICE_MATCH_TOLERANCE;
}

/**
 * Match a live venue order back to the intent that created it.
 *
 * Matching is on (side, level-within-tolerance) because that is all the venue
 * echoes back — Solana has no client order ID. Falls back to a derived key so
 * an unrecognised order can still be adopted and occupy cap space.
 */
export function matchIntent({ order, journal }) {
  if (!order.side || order.triggerPriceUsd == null) return null;
  return (
    journal.find(
      (i) => i.side === order.side && i.level != null && pricesMatch(i.level, order.triggerPriceUsd),
    ) ?? null
  );
}

export function keyForLiveOrder({ gridId, order }) {
  if (order.triggerPriceUsd == null || !order.side) return null;
  return intentKey({ gridId, side: order.side, level: order.triggerPriceUsd });
}

/**
 * Reconcile local journal against live venue state.
 *
 * Three outcomes matter:
 *   - an intent we thought was submitting IS live  -> promote to resting
 *   - an intent we thought was submitting is NOT live -> mark unknown, do not
 *     retry. Retrying is how you double-fire a rung after a crash.
 *   - a live order we have no record of -> adopt it, so it counts against caps
 */
export async function reconcile({ venue, store, config, log = () => {} }) {
  const liveOrders = await venue.getOpenOrders();
  const journal = await store.allIntents();

  // Resolve each live order to a journal intent by tolerant price match. A
  // venue-supplied intentKey is trusted when present (the dry-run venue sets
  // one), but real venues never echo it, so the match is what carries live mode.
  const liveByKey = new Map();
  // Each journal intent may back at most one live order. Without consuming
  // matches, two live orders a fraction of a basis point apart would both bind
  // to the same intent and one of them would vanish from the resting set —
  // leaving a real order the engine no longer counts or cancels.
  const unmatched = [...journal];
  const consume = (intent) => {
    const at = unmatched.indexOf(intent);
    if (at !== -1) unmatched.splice(at, 1);
    return intent;
  };

  for (const o of liveOrders) {
    const found = o.intentKey
      ? unmatched.find((i) => i.intentKey === o.intentKey)
      : matchIntent({ order: o, journal: unmatched });
    const matched = found ? consume(found) : null;
    const key = matched?.intentKey ?? o.intentKey ?? keyForLiveOrder({ gridId: config.gridId, order: o });
    if (key) liveByKey.set(key, o);
  }

  const adopted = [];
  const orphaned = [];

  for (const intent of journal) {
    const live = liveByKey.get(intent.intentKey);

    if (intent.status === INTENT_STATUS.SUBMITTING) {
      if (live) {
        await store.updateIntent(intent.intentKey, {
          status: INTENT_STATUS.RESTING,
          venueOrderId: live.venueOrderId,
        });
        adopted.push(intent.intentKey);
      } else {
        // Could be in flight, could be lost, could have already filled. Only a
        // human (or a fill record arriving later) can tell them apart.
        await store.updateIntent(intent.intentKey, { status: INTENT_STATUS.UNKNOWN });
        orphaned.push(intent.intentKey);
        log({ level: 'warn', msg: 'intent submitted but not found live', intentKey: intent.intentKey });
      }
      continue;
    }

    if (intent.status === INTENT_STATUS.RESTING && !live) {
      // Gone from the live list: it filled, expired, or was cancelled elsewhere.
      // Fill ingestion below decides which; assume nothing here.
      await store.updateIntent(intent.intentKey, { status: INTENT_STATUS.UNKNOWN });
      orphaned.push(intent.intentKey);
    }
  }

  // Live orders with no journal entry: adopt so they occupy cap space.
  const journalKeys = new Set(journal.map((i) => i.intentKey));
  for (const [key, order] of liveByKey) {
    if (journalKeys.has(key)) continue;
    await store.putIntent({
      intentKey: key,
      gridId: config.gridId,
      side: order.side,
      level: order.triggerPriceUsd,
      notionalUsd: config.notionalPerRungUsd,
      status: INTENT_STATUS.RESTING,
      venueOrderId: order.venueOrderId,
      adoptedFromVenue: true,
      updatedAtMs: Date.now(),
    });
    adopted.push(key);
  }

  return { liveOrders, restingKeys: [...liveByKey.keys()], adopted, orphaned };
}

/** Pull venue fills into the local log, idempotently. */
export async function ingestFills({ venue, store, config, log = () => {} }) {
  const venueFills = await venue.getFills();
  const known = new Set((await store.allFills()).map((f) => f.id));
  const journal = await store.allIntents();
  const added = [];
  const rejected = [];
  const feeUnknown = [];

  for (const f of venueFills) {
    const id = f.venueOrderId;
    if (!id || known.has(id)) continue;

    const priceUsd = f.executedPriceUsd ?? f.triggerPriceUsd;
    // Quantity must come from the fill or from the intent that created it —
    // never from current config, which would let editing notionalPerRungUsd
    // retroactively rewrite historical fill sizes.
    const matched = f.intentKey
      ? journal.find((i) => i.intentKey === f.intentKey)
      : matchIntent({ order: f, journal });
    const baseQty = f.filledBaseQty ?? matched?.baseQty ?? null;

    if (!(priceUsd > 0) || !(baseQty > 0)) {
      // Guessing here would silently corrupt P&L. Refuse and surface it.
      rejected.push({ id, reason: 'no reliable price or quantity on the fill' });
      log({ level: 'warn', msg: 'fill ingested without usable price/qty — skipped', id });
      continue;
    }

    // A real fill must be recorded even when the venue did not report its fee —
    // dropping it would lose inventory the wallet actually holds. But booking an
    // unreported fee as 0 states a cost we do not know, and zero fees make a grid
    // look better than it is. Record 0 so the arithmetic stays finite, flag the
    // fill, and surface the count so P&L is never read as fee-complete.
    const feeKnown = Number.isFinite(f.feeUsd);
    const fill = {
      id,
      gridId: config.gridId,
      side: f.side,
      baseQty,
      priceUsd,
      feeUsd: feeKnown ? f.feeUsd : 0,
      feeUnknown: !feeKnown,
      tsMs: f.updatedAtMs ?? f.createdAtMs ?? Date.now(),
      level: f.triggerPriceUsd ?? null,
    };
    await store.putFill(fill);
    added.push(fill);
    if (!feeKnown) {
      feeUnknown.push(id);
      log({ level: 'warn', msg: 'fill recorded with an unreported fee — P&L understates costs', id });
    }

    const key = matched?.intentKey ?? f.intentKey ?? keyForLiveOrder({ gridId: config.gridId, order: f });
    if (key) await store.updateIntent(key, { status: INTENT_STATUS.FILLED, fillId: id });
  }

  return { added, rejected, feeUnknown };
}

/**
 * One full tick.
 *
 * @returns a summary the popup and dashboard render directly.
 */
export async function tick({
  venue,
  store,
  configStore,
  limits = DEFAULT_LIMITS,
  clock = () => Date.now(),
  log = () => {},
}) {
  const config = await configStore.getConfig();
  const runtime = await configStore.getRuntime();
  const now = clock();

  // Record actual wake spacing: Chrome silently clamps short alarm periods, and
  // a clamp that goes unnoticed makes a live run behave unlike its dry run.
  const lastTickDeltaMs = runtime.lastTickMs ? now - runtime.lastTickMs : null;

  const today = dayKey(now);
  const isNewDay = runtime.dayKey !== today;

  const effectiveLimits = { ...limits, killSwitch: limits.killSwitch || runtime.killSwitch };

  const result = {
    tsMs: now,
    mode: config.mode,
    lastTickDeltaMs,
    price: null,
    placed: [],
    rejected: [],
    skipped: [],
    orphaned: [],
    errors: [],
    pnl: null,
    // Stays 0 when a tick aborts early, so the field's absence never has to be
    // distinguished from "no unknown fees".
    feeUnknownFills: 0,
  };

  try {
    const price = await venue.getPrice();
    // A NaN or non-positive price would flow into P&L, get persisted as the
    // daily realized figure, and permanently poison the daily-loss rail. Stop
    // here instead.
    if (!Number.isFinite(price) || price <= 0) {
      throw new RangeError(`venue returned an unusable price: ${price}`);
    }
    result.price = price;

    // Dry-run venues fill resting rungs off the new mark before reconciling.
    if (typeof venue.markPrice === 'function') venue.markPrice(price);

    const rec = await reconcile({ venue, store, config, log });
    result.orphaned = rec.orphaned;

    const ingested = await ingestFills({ venue, store, config, log });
    if (ingested.rejected.length) result.errors.push(...ingested.rejected.map((r) => ({ error: `fill ${r.id}: ${r.reason}` })));
    // Not an error — the fills are real — but the P&L below understates costs by
    // however much these fees were, so the count travels with the result.
    result.feeUnknownFills = ingested.feeUnknown.length;

    const fills = await store.allFills();
    const carry = await store.allCarry();
    const pnl = snapshot({ fills, markPriceUsd: price, carryEntries: carry });
    result.pnl = pnl;

    // TODAY's realized P&L, not lifetime. snapshot() reports cumulative
    // realized, so the daily-loss rail needs a day-start baseline — comparing
    // a lifetime figure against a daily limit either never fires or fires
    // forever, depending on which way the grid has run since inception.
    const dayStartRealizedUsd = isNewDay
      ? pnl.realizedNetUsd
      : (runtime.dayStartRealizedUsd ?? pnl.realizedNetUsd);
    const realizedPnlUsdToday = pnl.realizedNetUsd - dayStartRealizedUsd;
    result.realizedPnlUsdToday = realizedPnlUsdToday;

    const persistRuntime = () =>
      configStore.setRuntime({
        lastTickMs: now,
        lastTickDeltaMs,
        dayKey: today,
        dayStartRealizedUsd,
        realizedPnlUsdToday,
      });

    if (!runtime.armed) {
      result.skipped.push({ reason: 'not-armed' });
      await persistRuntime();
      return result;
    }

    // A short grid on a spot venue plans nothing at all. Without this the UI
    // just shows an idle grid with no explanation.
    if (config.direction === 'short' && venue.kind !== 'perps') {
      result.errors.push({
        error:
          'direction "short" cannot be expressed on a spot venue — there is nothing to sell short. Use "neutral" or "long", or a perps venue.',
      });
      await persistRuntime();
      return result;
    }

    // Exits are derived from the open lots, so each sell rests one rung above
    // the specific buy it closes.
    const plan = planGrid({
      config,
      price,
      openIntentKeys: rec.restingKeys,
      openLots: pnl.openLots,
    });
    result.skipped.push(...plan.skipped);

    const state = {
      openNotionalUsd: rec.restingKeys.length * config.notionalPerRungUsd,
      openOrderCount: rec.restingKeys.length,
      realizedPnlUsdToday,
      leverage: config.leverage,
      liquidationDistancePct: null,
    };

    const { admitted, rejected } = admitBatch({
      intents: plan.intents,
      state,
      limits: effectiveLimits,
      slippageBps: config.slippageBps,
    });
    result.rejected = rejected;

    for (const intent of admitted) {
      // WRITE-AHEAD: the journal entry must exist before the network call, or a
      // crash mid-submit is invisible to the next tick.
      await store.putIntent({
        ...intent,
        status: INTENT_STATUS.SUBMITTING,
        submittedAtMs: clock(),
        updatedAtMs: clock(),
      });

      try {
        const placed = await venue.placeOrder({
          intent,
          slippageBps: config.slippageBps,
          ttlMs: config.ttlMs,
        });
        await store.updateIntent(intent.intentKey, {
          status: INTENT_STATUS.RESTING,
          venueOrderId: placed.venueOrderId,
          txSignature: placed.txSignature ?? null,
          simulated: placed.simulated === true,
        });
        result.placed.push({ intentKey: intent.intentKey, ...placed });
      } catch (err) {
        // A failed submit is safe to retry; an ambiguous one is not, and
        // reconcile() is what decides that on the next tick.
        await store.updateIntent(intent.intentKey, {
          status: INTENT_STATUS.FAILED,
          error: String(err.message ?? err).slice(0, 300),
        });
        result.errors.push({ intentKey: intent.intentKey, error: String(err.message ?? err) });
        log({ level: 'error', msg: 'placeOrder failed', intentKey: intent.intentKey, error: String(err) });
      }
    }

    await persistRuntime();
  } catch (err) {
    result.errors.push({ error: String(err.message ?? err) });
    log({ level: 'error', msg: 'tick failed', error: String(err) });
  }

  await store.logEvent({ type: 'tick', summary: summarise(result) });
  return result;
}

export function summarise(r) {
  return {
    tsMs: r.tsMs,
    mode: r.mode,
    price: r.price,
    placed: r.placed.length,
    rejected: r.rejected.length,
    orphaned: r.orphaned.length,
    errors: r.errors.length,
    netUsd: r.pnl?.totalNetUsd ?? null,
  };
}
