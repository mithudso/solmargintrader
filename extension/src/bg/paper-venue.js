/** Durable simulated venue state. Called inside the command's store lock. */
export async function restorePaperVenue(venue, config, state) {
  const key = `paperVenue:${JSON.stringify([config.venue, config.baseMint, config.quoteMint,
    config.userPubkey, config.gridId])}`;
  const saved = await state.get(key, null);
  if (saved !== null) {
    if (saved.version !== 1 || !Array.isArray(saved.orders) || !saved.orders.every(validOrder)) {
      throw new Error('Paper venue state is unreadable; review it before continuing.');
    }
    venue.simulated = structuredClone(saved.orders);
  }
  const persist = () => state.set(key, { version: 1, orders: structuredClone(venue.simulated) });
  // Persist submissions/cancellations before acknowledging them. Price marking
  // is synchronous; the first reconciliation read flushes its changed fills.
  for (const name of ['placeOrder', 'cancelOrder', 'getOpenOrders', 'getFills']) {
    const original = venue[name].bind(venue);
    venue[name] = async (...args) => {
      const result = await original(...args);
      await persist();
      return result;
    };
  }
  return venue;
}

function validOrder(o) {
  if (!o || typeof o !== 'object' || typeof o.venueOrderId !== 'string' || !o.venueOrderId
      || typeof o.intentKey !== 'string' || !o.intentKey
      || !['buy', 'sell'].includes(o.side) || !['active', 'filled', 'cancelled'].includes(o.status)
      || !Number.isFinite(o.triggerPriceUsd) || o.triggerPriceUsd <= 0
      || !Number.isFinite(o.createdAtMs) || o.createdAtMs < 0) return false;
  for (const k of ['baseQty', 'executedPriceUsd', 'filledBaseQty']) {
    if (o[k] !== undefined && (!Number.isFinite(o[k]) || o[k] <= 0)) return false;
  }
  for (const k of ['feeUsd', 'slippageBps', 'updatedAtMs']) {
    if (o[k] !== undefined && (!Number.isFinite(o[k]) || o[k] < 0)) return false;
  }
  return true;
}
