export function freshStrategy(oracle, at = Date.now() / 1000) {
  const strategy = oracle?.status === 'available' ? oracle.topStrategy : null;
  if (!strategy || typeof strategy.expiresAt !== 'number' || !Number.isFinite(strategy.expiresAt) || strategy.expiresAt <= at) return null;
  if (!['up', 'down', 'flat'].includes(strategy.direction)) return null;
  return strategy;
}
