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
import { admitBatch, capitalExposure, dayKey, DEFAULT_LIMITS } from './risk.js';
import { snapshot } from './pnl.js';
import { INTENT_STATUS } from '../storage/store.js';

// Store identity survives separate IndexedDB connections and FileStore wrappers in
// the same runtime. Memory stores keep their own independent queue.
const engineQueues = new Map();
const storeIdentity = (store) => store.path ? `file:${store.path}` : store.db?.name ? `indexeddb:${store.db.name}` : store;
const queueFor = (store) => {
  const key = storeIdentity(store);
  if (!engineQueues.has(key)) engineQueues.set(key, { tail: Promise.resolve(), stopped: false, stopGeneration: 0, pending: 0 });
  return engineQueues.get(key);
};

export function withStoreLock(store, operation) {
  const queue = queueFor(store);
  // `pending` counts operations queued or running, so an outside observer can
  // tell "nothing is mid-tick" without joining the queue.
  queue.pending++;
  const result = queue.tail.then(operation);
  queue.tail = result.catch(() => {});
  const settled = () => { queue.pending--; };
  result.then(settled, settled);
  return result;
}

/**
 * Count of locked operations (tick, reconcile, submit, cancel, lifecycle
 * write) queued or running; 0 means idle. The auto-reload gate reads this: a reload that
 * lands between an order submit and its reconcile is how a rung double-fires.
 */
export function enginePending(store) {
  return queueFor(store).pending;
}

export const engineIdle = (store) => enginePending(store) === 0;

// A stop request revokes the remainder of a running batch before the lifecycle
// command waits its turn to persist. It cannot undo an already submitted order.
export function stopEngine(store) {
  const queue = queueFor(store);
  queue.stopped = true;
  queue.stopGeneration++;
}
export function engineStopGeneration(store) { return queueFor(store).stopGeneration; }
export function resumeEngine(store, generation) {
  const queue = queueFor(store);
  // An arm queued before a later stop request cannot revoke that request.
  if (generation === queue.stopGeneration) queue.stopped = false;
}

export function occupiedIntentKeys(intents) {
  return [...new Set(intents.filter((i) => [INTENT_STATUS.RESTING, INTENT_STATUS.UNKNOWN, INTENT_STATUS.SUBMITTING].includes(i.status))
    .map((i) => i.occupancyKey ?? i.intentKey))];
}

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
export function reconcile(args) {
  return withStoreLock(args.store, () => reconcileUnlocked(args));
}

async function reconcileUnlocked({ venue, store, config, log = () => {} }) {
  const liveOrders = await venue.getOpenOrders();
  const journal = await store.allIntents();

  const liveByKey = new Map();
  const occupancyKeys = new Set();
  const unmatched = [...journal];
  for (const order of liveOrders) {
    if (!order.venueOrderId) throw new Error('live order has no venue identity');
    const candidates = unmatched.filter((i) => !i.venueOrderId || i.venueOrderId === order.venueOrderId);
    const matched = candidates.find((i) => i.venueOrderId === order.venueOrderId)
      ?? (order.intentKey ? candidates.find((i) => i.intentKey === order.intentKey)
        : matchIntent({ order, journal: candidates }));
    if (matched) unmatched.splice(unmatched.indexOf(matched), 1);
    const occupancyKey = matched?.occupancyKey ?? matched?.intentKey
      ?? order.intentKey ?? keyForLiveOrder({ gridId: config.gridId, order });
    if (!occupancyKey) throw new Error('live order has no usable rung identity');
    let key = matched?.intentKey ?? occupancyKey;
    // Two distinct orders may occupy exactly the same rung. Keep the journal
    // identity separate from planner occupancy so neither order disappears.
    if (liveByKey.has(key) || (!matched && journal.some((i) => i.intentKey === key))) {
      key = `${occupancyKey}:venue:${order.venueOrderId}`;
    }
    if (liveByKey.has(key)) throw new Error('duplicate venue order identity');
    liveByKey.set(key, { order, occupancyKey, matched });
    occupancyKeys.add(occupancyKey);
  }

  const adopted = [];
  const orphaned = [];

  for (const intent of journal) {
    const live = liveByKey.get(intent.intentKey)?.order;

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

  // Missing size stays unknown. A configured rung size says nothing about an
  // order another client placed, and cannot establish remaining cap headroom.
  for (const [key, { order, occupancyKey, matched }] of liveByKey) {
    if (matched) {
      if (matched.status !== INTENT_STATUS.SUBMITTING) {
        await store.updateIntent(key, { status: INTENT_STATUS.RESTING, venueOrderId: order.venueOrderId, occupancyKey });
      }
      continue;
    }
    await store.putIntent({
      intentKey: key, occupancyKey, gridId: config.gridId,
      side: order.side, level: order.triggerPriceUsd,
      notionalUsd: Number.isFinite(order.notionalUsd) && order.notionalUsd > 0 ? order.notionalUsd : null,
      status: INTENT_STATUS.RESTING, venueOrderId: order.venueOrderId,
      adoptedFromVenue: true, updatedAtMs: Date.now(),
    });
    adopted.push(key);
  }

  return { liveOrders, restingKeys: [...liveByKey.keys()], occupiedKeys: [...occupancyKeys], adopted, orphaned };
}

/** Pull venue fills into the local log, idempotently. */
export function ingestFills(args) {
  return withStoreLock(args.store, () => ingestFillsUnlocked(args));
}

async function ingestFillsUnlocked({ venue, store, config, log = () => {} }) {
  const venueFills = await venue.getFills();
  const known = new Set((await store.allFills()).map((f) => f.id));
  const journal = await store.allIntents();
  const added = [];
  const rejected = [];
  const feeUnknown = [];

  for (const f of venueFills) {
    const id = f.venueOrderId;
    if (id && known.has(id)) continue;
    // Only the adapter can prove that terminal history represents zero
    // execution. A cancelled status alone may still contain a partial fill.
    if (f.executionAbsent === true && !(f.filledBaseQty > 0) && !(f.executedPriceUsd > 0)) {
      log({ level: 'info', msg: 'terminal order ignored — verified no execution', id });
      continue;
    }
    const candidates = journal.filter((i) => !i.venueOrderId || i.venueOrderId === id);
    const matched = candidates.find((i) => id && i.venueOrderId === id)
      ?? (f.intentKey ? candidates.find((i) => i.intentKey === f.intentKey) : matchIntent({ order: f, journal: candidates }));
    const validExecution = id && !f.unusable && ['buy', 'sell'].includes(f.side)
      && Number.isFinite(f.executedPriceUsd) && f.executedPriceUsd > 0
      && Number.isFinite(f.filledBaseQty) && f.filledBaseQty > 0
      && Number.isFinite(f.updatedAtMs ?? f.createdAtMs) && (f.updatedAtMs ?? f.createdAtMs) >= 0;
    if (!validExecution) {
      rejected.push({ id: id ?? 'unidentified', reason: 'history record unusable: no reliable execution price, quantity or timestamp' });
      if (matched) await store.updateIntent(matched.intentKey, { status: INTENT_STATUS.UNKNOWN });
      log({ level: 'warn', msg: 'execution history incomplete; trading held for review', id: id ?? null });
      continue;
    }
    // A trigger is a condition, and planned quantity is an intention. Neither
    // establishes the amount or price that the wallet actually exchanged.
    const priceUsd = f.executedPriceUsd;
    const baseQty = f.filledBaseQty;

    // A real fill must be recorded even when the venue did not report its fee —
    // dropping it would lose inventory the wallet actually holds. But booking an
    // unreported fee as 0 states a cost we do not know, and zero fees make a grid
    // look better than it is. Record 0 so the arithmetic stays finite, flag the
    // fill, and surface the count so P&L is never read as fee-complete.
    const feeKnown = Number.isFinite(f.feeUsd) && f.feeUsd >= 0;
    const fill = {
      id,
      gridId: config.gridId,
      side: f.side,
      baseQty,
      priceUsd,
      feeUsd: feeKnown ? f.feeUsd : 0,
      feeUnknown: !feeKnown,
      tsMs: f.updatedAtMs ?? f.createdAtMs,
      level: f.triggerPriceUsd ?? null,
    };
    // Link a sell to the lots its intent was paired with, so P&L closes the
    // inventory actually sold. Absent for legacy intents and for sells matched to
    // no intent; pnl.js then falls back to FIFO, which is the old behaviour.
    if (f.side === 'sell' && Array.isArray(matched?.lots) && matched.lots.length > 0) {
      fill.closesLots = matched.lots.map((l) => ({ priceUsd: l.priceUsd, baseQty: l.baseQty }));
    }
    await store.putFill(fill);
    added.push(fill);
    if (!feeKnown) {
      feeUnknown.push(id);
      log({ level: 'warn', msg: 'fill recorded with an unreported fee — P&L understates costs', id });
    }

    if (matched) await store.updateIntent(matched.intentKey, { status: INTENT_STATUS.FILLED, fillId: id });
  }

  return { added, rejected, feeUnknown, blocked: rejected.length > 0 };
}

/**
 * One full tick.
 *
 * @returns a summary the popup and dashboard render directly.
 */
const DIAGNOSTIC_KINDS = new Set(['Error', 'TypeError', 'RangeError', 'SyntaxError',
  'HttpError', 'TimeoutError', 'AbortError', 'CommandError']);

function diagnosticError(error, stage) {
  // Error messages and response bodies can contain credentials. Persist the
  // operation, a known error class and an HTTP status instead of those strings.
  const detail = { stage, kind: DIAGNOSTIC_KINDS.has(error?.name) ? error.name : 'Error' };
  if (Number.isInteger(error?.status) && error.status >= 100 && error.status <= 599) detail.status = error.status;
  return detail;
}

export function tick(args) {
  return withStoreLock(args.store, async () => {
    let result, stage = 'prepare-venue';
    try {
      const venue = args.buildVenue ? await args.buildVenue() : args.venue;
      stage = 'prepare-limits';
      const limits = args.readLimits ? await args.readLimits() : args.limits;
      stage = 'tick-state';
      result = await tickUnlocked({ ...args, venue, limits });
    } catch (error) {
      await args.store.logEvent({ type: 'tick', summary: summarise({
        tsMs: Date.now(), mode: null, price: null, placed: [], rejected: [], orphaned: [],
        errors: [{}], errorDetails: [diagnosticError(error, stage)],
      }) });
      throw error;
    }
    // Early safety holds must leave the same durable history as completed ticks.
    await args.store.logEvent({ type: 'tick', summary: summarise(result) });
    return result;
  });
}

async function tickUnlocked({
  venue,
  store,
  configStore,
  limits = DEFAULT_LIMITS,
  clock = () => Date.now(),
  log = () => {},
}) {
  let config = await configStore.getConfig();
  const runtime = await configStore.getRuntime();
  const now = clock();

  // Record actual wake spacing: Chrome silently clamps short alarm periods, and
  // a clamp that goes unnoticed makes a live run behave unlike its dry run.
  const lastTickDeltaMs = runtime.lastTickMs ? now - runtime.lastTickMs : null;

  const today = dayKey(now);

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
    // Intent keys held out of planning pending a human decision (resolveIntent).
    unknownIntents: [],
    errors: [],
    errorDetails: [],
    pnl: null,
    // Stays 0 when a tick aborts early, so the field's absence never has to be
    // distinguished from "no unknown fees".
    feeUnknownFills: 0,
  };

  let stage = 'price';
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

    stage = 'reconcile';
    const rec = await reconcileUnlocked({ venue, store, config, log });
    result.orphaned = rec.orphaned;

    stage = 'fills';
    const ingested = await ingestFillsUnlocked({ venue, store, config, log });
    if (ingested.rejected.length) result.errors.push(...ingested.rejected.map((r) => ({ error: `fill ${r.id}: ${r.reason}` })));
    // Not an error — the fills are real — but the P&L below understates costs by
    // however much these fees were, so the count travels with the result.

    stage = 'accounting';
    const fills = await store.allFills();
    result.feeUnknownFills = fills.filter((f) => f.feeUnknown === true).length;
    const carry = await store.allCarry();
    const accountingUnknown = result.feeUnknownFills > 0 ||
      fills.some((f) => !Number.isFinite(f.tsMs) || f.tsMs < 0 || !Number.isFinite(f.feeUsd) || f.feeUsd < 0 ||
        !Number.isFinite(f.priceUsd) || f.priceUsd <= 0 || !Number.isFinite(f.baseQty) || f.baseQty <= 0 ||
        !['buy', 'sell'].includes(f.side)) ||
      carry.some((c) => !Number.isFinite(c.tsMs) || c.tsMs < 0 || !Number.isFinite(c.costUsd));
    const pnl = snapshot({ fills, markPriceUsd: price, carryEntries: carry });
    result.pnl = pnl;

    // Rebuild midnight's realized balance with all earlier fills so a lot
    // opened yesterday retains its cost basis when it closes before this wake.
    // Rebuilding also attributes history that arrived late to its actual day.
    const midnight = Date.parse(`${today}T00:00:00Z`);
    const dayStartRealizedUsd = snapshot({
      fills: fills.filter((f) => f.tsMs < midnight),
      markPriceUsd: price,
      carryEntries: carry.filter((c) => c.tsMs < midnight),
    }).realizedNetUsd;
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

    if (ingested.blocked) {
      result.skipped.push({ reason: 'execution-history-needs-review' });
      await persistRuntime();
      return result;
    }

    if (accountingUnknown || !Number.isFinite(pnl.unmatchedSellQty) || pnl.unmatchedSellQty > 0) {
      result.skipped.push({ reason: 'accounting-evidence-needs-review' });
      log({ level: 'warn', msg: 'unknown accounting costs or timing; trading held for review' });
      await persistRuntime();
      return result;
    }

    if (!runtime.armed || queueFor(store).stopped) {
      result.skipped.push({ reason: 'not-armed' });
      await persistRuntime();
      return result;
    }

    if (venue.executionBlockedReason) {
      result.skipped.push({ reason: venue.executionBlockedReason });
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
    //
    // The occupied set is wider than the live order list. An UNKNOWN intent was
    // submitted and then not found on the venue: it may have filled, been lost,
    // or still be in flight, and `reconcile()` cannot tell which. Treating it as
    // merely "not resting" would let planGrid re-emit the same intentKey and
    // place the rung a second time — the crash double-fire this journal exists to
    // prevent. A SUBMITTING record can only be left over from a prior tick (this
    // tick's reconcile already resolved it), so it is held for the same reason.
    // Read AFTER ingestFills: a fill that just arrived flips UNKNOWN to FILLED,
    // and that rung is legitimately free again.
    stage = 'planning';
    const journal = await store.allIntents();
    const held = journal.filter(
      (i) => i.status === INTENT_STATUS.UNKNOWN || i.status === INTENT_STATUS.SUBMITTING,
    );
    const heldKeys = held.map((i) => i.intentKey);
    if (heldKeys.length) {
      result.unknownIntents = heldKeys;
      result.skipped.push({ reason: 'unknown-intent-needs-review', intentKeys: heldKeys });
      log({ level: 'warn', msg: 'unresolved intents hold their rungs', intentKeys: heldKeys });
    }
    const occupiedKeys = [...new Set([...rec.occupiedKeys, ...held.map((i) => i.occupancyKey ?? i.intentKey)])];

    const plan = planGrid({
      config,
      price,
      openIntentKeys: occupiedKeys,
      openLots: pnl.openLots,
    });
    result.skipped.push(...plan.skipped);
    result.recentre = plan.recentre;

    // WRITE-AHEAD, same reasoning as the intent journal below: planGrid is pure,
    // so a re-centre it computes exists only in `plan` until it is stored. If an
    // order were placed on the moved ladder while config still held the old
    // bounds, the next tick would see those orders resting, refuse to re-centre,
    // fall back to the OLD bounds and place a second ladder at the levels this
    // tick just abandoned — capital committed to two ladders at once. Persisting
    // first also means a crash mid-submit leaves config describing the ladder the
    // orders actually belong to.
    if (plan.recentre.applied) {
      config = await configStore.setConfig({
        lower: plan.recentre.to.lower,
        upper: plan.recentre.to.upper,
      });
      log({
        level: 'warn',
        msg: 'grid re-centred',
        from: plan.recentre.from,
        to: plan.recentre.to,
        reason: plan.recentre.reason,
      });
    }

    const liveKeys = new Set(rec.restingKeys);
    const outstanding = journal.filter((i) => liveKeys.has(i.intentKey)
      || i.status === INTENT_STATUS.UNKNOWN || i.status === INTENT_STATUS.SUBMITTING);
    const exposure = capitalExposure({ openLots: pnl.openLots, outstanding, markPriceUsd: price });
    const state = {
      // Owned lots stay at risk after the entry order fills. Covered exits
      // reserve that inventory without adding a second copy of its value.
      openNotionalUsd: exposure.openNotionalUsd,
      openOrderCount: exposure.openOrderCount,
      realizedPnlUsdToday,
      leverage: config.leverage,
      liquidationDistancePct: null,
    };

    const { admitted, rejected, limitProblems } = admitBatch({
      intents: plan.intents,
      state,
      limits: effectiveLimits,
      slippageBps: config.slippageBps,
      openLots: exposure.unreservedLots,
    });
    result.rejected = rejected;
    // A limit that was unusable and fell back to its default: surface it so the
    // bad setLimits value gets fixed instead of silently running on defaults.
    result.limitProblems = limitProblems;

    stage = 'submit';
    for (const intent of admitted) {
      const currentRuntime = await configStore.getRuntime();
      if (queueFor(store).stopped || !currentRuntime.armed || currentRuntime.killSwitch) {
        result.skipped.push({ reason: 'execution-stopped' });
        break;
      }
      // WRITE-AHEAD: the journal entry must exist before the network call, or a
      // crash mid-submit is invisible to the next tick.
      await store.putIntent({
        ...intent,
        status: INTENT_STATUS.SUBMITTING,
        submittedAtMs: clock(),
        updatedAtMs: clock(),
      });

      // Persistence yields to the event loop. An immediate kill/disarm request
      // may arrive during that await, before any venue submission has started.
      if (queueFor(store).stopped) {
        await store.updateIntent(intent.intentKey, { status: INTENT_STATUS.FAILED,
          error: 'execution stopped before venue submission', definitelyNotSubmitted: true });
        result.skipped.push({ reason: 'execution-stopped' });
        break;
      }

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
        // A thrown call may have reached the venue. A local persistence error
        // after acceptance is equally ambiguous. Neither permits an auto-retry.
        await store.updateIntent(intent.intentKey, {
          status: INTENT_STATUS.UNKNOWN,
          error: String(err.message ?? err).slice(0, 300),
        });
        result.errors.push({ intentKey: intent.intentKey, error: String(err.message ?? err) });
        result.errorDetails.push(diagnosticError(err, 'submit'));
        log({ level: 'error', msg: 'placeOrder failed', intentKey: intent.intentKey, error: String(err) });
      }
    }

    await persistRuntime();
  } catch (err) {
    result.errors.push({ error: String(err.message ?? err) });
    result.errorDetails.push(diagnosticError(err, stage));
    log({ level: 'error', msg: 'tick failed', error: String(err) });
  }

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
    ...(r.errorDetails?.length ? { errorDetails: r.errorDetails.slice(0, 20) } : {}),
    ...(r.skipped?.length ? { holds: r.skipped.slice(0, 20).map((entry) =>
      /^[a-z0-9-]{1,80}$/.test(entry.reason) ? entry.reason : 'execution-held') } : {}),
    ...(r.unknownIntents?.length ? { unknownIntents: r.unknownIntents.slice(0, 20)
      .map((key) => String(key).slice(0, 200)) } : {}),
    netUsd: r.pnl?.totalNetUsd ?? null,
    // A fee the venue never reported is booked as 0 so the arithmetic stays
    // finite, which means the fee total reads as complete when it is not. The
    // count belongs in the event log, or the safeguard is invisible.
    feeUnknownFills: r.feeUnknownFills ?? 0,
  };
}
