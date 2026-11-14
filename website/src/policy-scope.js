/** Product/leverage scope only. Callers must also validate money, expiry and proof. */
const LEGACY_KEYS = ['venues', 'assets', 'maxTradeUsd', 'maxTotalUsd', 'expiresAt'];
const V2_KEYS = ['version', 'venues', 'assets', 'products', 'maxLeverage', 'maxTradeUsd', 'maxTotalUsd', 'expiresAt'];
const VENUES = ['coinbase', 'jupiter'];
const ASSETS = ['BTC', 'ETH', 'SOL', 'ZEC'];
const PRODUCTS = ['spot', 'perpetual'];
const exact = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) &&
  Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
const collection = (value, allowed) => Array.isArray(value) && value.length > 0 && value.length <= allowed.length &&
  value.every(item => allowed.includes(item)) && new Set(value).size === value.length;

export function validPolicyScope(policy) {
  const legacy = exact(policy, LEGACY_KEYS);
  if (!legacy && !(exact(policy, V2_KEYS) && policy.version === 2)) return false;
  if (!collection(policy.venues, VENUES) || !collection(policy.assets, ASSETS)) return false;
  return legacy || (collection(policy.products, PRODUCTS) && Number.isInteger(policy.maxLeverage) && policy.maxLeverage >= 1 && policy.maxLeverage <= 5);
}

export function tradeWithinPolicyScope(policy, trade) {
  if (!validPolicyScope(policy) || !trade || typeof trade !== 'object' || Array.isArray(trade) ||
      !policy.venues.includes(trade.venue) || !policy.assets.includes(trade.asset)) return false;
  const product = trade.product === undefined ? 'spot' : trade.product;
  const leverage = trade.leverage === undefined ? 1 : trade.leverage;
  if (!PRODUCTS.includes(product) || !Number.isInteger(leverage) || leverage < 1 || leverage > 5 || (product === 'spot' && leverage !== 1)) return false;
  if (policy.version !== 2) return product === 'spot' && leverage === 1;
  return policy.products.includes(product) && leverage <= policy.maxLeverage;
}
