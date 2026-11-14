/** Coinbase Advanced Trade transport. Provider origins, order shape and account are fixed. */
import { at, base64url, boundedJSON, cents, opaque, refuse, uuid } from './common.js';

const ORIGIN = 'https://api.coinbase.com';
const PREFIX = '/api/v3/brokerage';
const SCALE = 10n ** 18n;
const TERMINAL = new Set(['FILLED', 'CANCELLED', 'EXPIRED', 'FAILED']);
export function decimal(value, positive = false) {
  if (typeof value !== 'string' || !/^\d{1,18}(?:\.\d{1,18})?$/.test(value)) refuse('provider_economics_invalid', 502);
  const [whole, fraction = ''] = value.split('.'); const number = BigInt(whole) * SCALE + BigInt(fraction.padEnd(18, '0'));
  if (positive && number <= 0n) refuse('provider_economics_invalid', 502);
  return number;
}
export function decimalText(value) {
  const whole = value / SCALE; const fraction = String(value % SCALE).padStart(18, '0').replace(/0+$/, '');
  return String(whole) + (fraction ? `.${fraction}` : '');
}
const ceil = (x, unit) => (x + unit - 1n) / unit * unit;
const USD_CENT = SCALE / 100n;
function encodedLength(n) { return n < 128 ? [n] : n < 256 ? [0x81, n] : [0x82, n >> 8, n & 255]; }
function der(tag, data) { return new Uint8Array([tag, ...encodedLength(data.length), ...data]); }
export async function importSigningKey(pem) {
  if (typeof pem !== 'string' || pem.length > 4096) refuse('invalid_credential');
  const match = /^-----BEGIN (EC PRIVATE KEY|PRIVATE KEY)-----\s+([A-Za-z0-9+/=\s]+)-----END \1-----\s*$/.exec(pem.replaceAll('\\n', '\n'));
  if (!match) refuse('invalid_credential');
  let bytes; try { bytes = Uint8Array.from(atob(match[2].replace(/\s/g, '')), c => c.charCodeAt(0)); } catch { refuse('invalid_credential'); }
  // CDP commonly exports SEC1; wrap it in the standard P-256 PKCS8 algorithm envelope.
  if (match[1] === 'EC PRIVATE KEY') {
    const algorithm = [0x30, 0x13, 0x06, 0x07, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x02, 0x01, 0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01, 0x07];
    bytes = der(0x30, new Uint8Array([0x02, 0x01, 0x00, ...algorithm, ...der(0x04, bytes)]));
  }
  try { return await crypto.subtle.importKey('pkcs8', bytes, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']); }
  catch { refuse('invalid_credential'); }
}
export function credentialShape(value) {
  if (!value || typeof value.apiKeyName !== 'string' || !/^organizations\/[A-Za-z0-9-]{1,64}\/apiKeys\/[A-Za-z0-9-]{1,64}$/.test(value.apiKeyName) || typeof value.privateKey !== 'string') refuse('invalid_credential');
  return { apiKeyName: value.apiKeyName, privateKey: value.privateKey };
}
export async function jwt(credentials, method, path, issued = at()) {
  const key = await importSigningKey(credentials.privateKey);
  const header = base64url(new TextEncoder().encode(JSON.stringify({ alg: 'ES256', typ: 'JWT', kid: credentials.apiKeyName, nonce: [...crypto.getRandomValues(new Uint8Array(16))].map(x => x.toString(16).padStart(2, '0')).join('') })));
  const payload = base64url(new TextEncoder().encode(JSON.stringify({ iss: 'cdp', sub: credentials.apiKeyName, nbf: issued, exp: issued + 120, uri: `${method} api.coinbase.com${path}` })));
  const text = `${header}.${payload}`;
  const signature = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, key, new TextEncoder().encode(text));
  return `${text}.${base64url(signature)}`;
}
export class Coinbase {
  constructor(credentials, transport = fetch) { this.credentials = credentialShape(credentials); this.transport = transport; }
  async signedRequest(method, path, body = null) {
    if (!path.startsWith(`${PREFIX}/`) || !['GET', 'POST'].includes(method)) refuse('provider_route_invalid');
    const url = new URL(path, ORIGIN);
    if (url.origin !== ORIGIN || url.username || url.password || url.hash) refuse('provider_route_invalid');
    return new Request(url, { method, headers: { Authorization: `Bearer ${await jwt(this.credentials, method, url.pathname)}`, Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}) }, body: body ? JSON.stringify(body) : undefined, redirect: 'manual', signal: AbortSignal.timeout(8000) });
  }
  async response(request) {
    let response; try { response = await this.transport(request); } catch { refuse('provider_outcome_unknown', 503); }
    if (!response.ok || !response.headers.get('Content-Type')?.toLowerCase().startsWith('application/json')) refuse('provider_unavailable', 503);
    return boundedJSON(response);
  }
  async call(method, path, body = null) { return this.response(await this.signedRequest(method, path, body)); }
  async permissions(portfolioId = null) {
    const value = await this.call('GET', `${PREFIX}/key_permissions`);
    if (value?.can_view !== true || value.can_trade !== true || value.can_transfer !== false || !uuid(value.portfolio_uuid) || (portfolioId && value.portfolio_uuid !== portfolioId) || value.portfolio_type === 'INTX') refuse('trade_only_portfolio_required', 403);
    return value.portfolio_uuid;
  }
  async orders(portfolioId) {
    const rows = []; const cursors = new Set(); let cursor = null;
    for (let page = 0; page < 5; page++) {
      const params = new URLSearchParams({ limit: '100', retail_portfolio_id: portfolioId }); if (cursor) params.set('cursor', cursor);
      const value = await this.call('GET', `${PREFIX}/orders/historical/batch?${params}`);
      if (!Array.isArray(value?.orders) || typeof value.has_next !== 'boolean' || value.orders.length > 100) refuse('reconciliation_unavailable', 503);
      for (const row of value.orders) {
        if (!uuid(row.order_id) || typeof row.client_order_id !== 'string' || row.client_order_id.length > 128 || row.retail_portfolio_id !== portfolioId || typeof row.status !== 'string') refuse('reconciliation_unavailable', 503);
        rows.push(row);
      }
      if (!value.has_next) return rows;
      if (!opaque(value.cursor) || cursors.has(value.cursor)) refuse('reconciliation_unavailable', 503);
      cursor = value.cursor; cursors.add(cursor);
    }
    refuse('reconciliation_bound_exceeded', 503);
  }
  async accounts(portfolioId) {
    const rows = []; const cursors = new Set(); let cursor = null;
    for (let page = 0; page < 5; page++) {
      const params = new URLSearchParams({ limit: '100', retail_portfolio_id: portfolioId }); if (cursor) params.set('cursor', cursor);
      const value = await this.call('GET', `${PREFIX}/accounts?${params}`);
      if (!Array.isArray(value?.accounts) || typeof value.has_next !== 'boolean' || value.accounts.length > 100) refuse('account_unavailable', 503);
      for (const row of value.accounts) {
        if (row.retail_portfolio_id !== portfolioId) refuse('account_binding_invalid', 403);
        if (!row.available_balance || row.available_balance.currency !== row.currency) refuse('account_unavailable', 503);
        decimal(row.available_balance.value); rows.push(row);
      }
      if (!value.has_next) return rows;
      if (!opaque(value.cursor) || cursors.has(value.cursor)) refuse('account_unavailable', 503);
      cursor = value.cursor; cursors.add(cursor);
    }
    refuse('account_bound_exceeded', 503);
  }
  async preview(order, feeCap) {
    const value = await this.call('POST', `${PREFIX}/orders/preview`, order);
    if (!opaque(value?.preview_id) || !Array.isArray(value.errs) || value.errs.length || decimal(value.base_size, true) !== decimal(order.order_configuration.sor_limit_ioc.base_size, true) || decimal(value.commission_total) > feeCap) refuse('quote_unavailable', 503);
    const limit = decimal(order.order_configuration.sor_limit_ioc.limit_price, true);
    const quoteSize = decimal(value.quote_size, true);
    if (quoteSize > limit * decimal(value.base_size, true) / SCALE + USD_CENT) refuse('quote_unavailable', 503);
    return value;
  }
  available(accounts, order, feeCap, minimumBaseBalance = null) {
    const sell = order.side === 'SELL';
    if (!sell && order.side !== 'BUY') refuse('venue_product_unavailable', 409);
    const currency = sell ? order.product_id.split('-')[0] : 'USD';
    const quantity = decimal(order.order_configuration.sor_limit_ioc.base_size, true);
    const price = decimal(order.order_configuration.sor_limit_ioc.limit_price, true);
    let required = sell ? quantity : ceil(price * quantity / SCALE, USD_CENT) + decimal(feeCap);
    if (minimumBaseBalance !== null) {
      if (!sell) refuse('managed_allocation_invalid');
      const floor = decimal(minimumBaseBalance); if (required < floor) required = floor;
    }
    const balances = accounts.filter(row => row.currency === currency && row.active === true && row.ready === true);
    if (balances.length !== 1 || decimal(balances[0].available_balance.value) < required) refuse('insufficient_available_balance', 409);
  }
  async prepare(trade, portfolioId, minimumBaseBalance = null) {
    if (trade.venue !== 'coinbase' || trade.product !== 'spot' || trade.leverage !== 1 || !['SOL', 'BTC', 'ETH', 'ZEC'].includes(trade.asset) || !['buy', 'sell'].includes(trade.side)) refuse('venue_product_unavailable', 409);
    await this.permissions(portfolioId);
    const orders = await this.orders(portfolioId);
    if (orders.some(row => !TERMINAL.has(row.status))) refuse('venue_orders_open', 409);
    const accounts = await this.accounts(portfolioId);
    const productId = `${trade.asset}-USD`;
    const product = await this.call('GET', `${PREFIX}/products/${productId}`);
    if (product?.product_id !== productId || product.base_currency_id !== trade.asset || product.quote_currency_id !== 'USD' || product.product_type !== 'SPOT' || ['trading_disabled', 'cancel_only', 'limit_only', 'post_only', 'auction_mode'].some(key => product[key] !== false)) refuse('product_unavailable', 409);
    const book = await this.call('GET', `${PREFIX}/best_bid_ask?${new URLSearchParams({ product_ids: productId })}`);
    if (!Array.isArray(book?.pricebooks) || book.pricebooks.length !== 1 || book.pricebooks[0].product_id !== productId) refuse('quote_unavailable', 503);
    const pricebook = book.pricebooks[0]; const timestamp = Date.parse(pricebook.time) / 1000;
    if (!Number.isFinite(timestamp) || timestamp > at() + 5 || timestamp < at() - 15) refuse('stale_quote', 409);
    const level = (trade.side === 'buy' ? pricebook.asks : pricebook.bids)?.[0];
    const rawPrice = decimal(level?.price, true); const priceStep = decimal(product.quote_increment, true); const baseStep = decimal(product.base_increment, true);
    const price = trade.side === 'buy' ? ceil(rawPrice, priceStep) : rawPrice / priceStep * priceStep;
    const summary = await this.call('GET', `${PREFIX}/transaction_summary`);
    const rate = decimal(summary?.fee_tier?.taker_fee_rate); if (rate > SCALE) refuse('fee_unavailable', 503);
    const budget = BigInt(cents(trade.budgetUsd)) * USD_CENT;
    // Leave the proven maximum two-cent rounding envelope unused. Both gross
    // notional and fees round upward to cents; no market price or fee is guessed.
    const sizingBudget = budget - 2n * USD_CENT;
    if (sizingBudget <= 0n) refuse('order_below_minimum', 409);
    let quantity = (sizingBudget * SCALE / (price * (SCALE + rate) / SCALE)) / baseStep * baseStep;
    if (trade.maxBaseQuantity !== undefined) {
      if (trade.reduceOnly !== true || trade.side !== 'sell') refuse('invalid_trade');
      const cap = decimal(trade.maxBaseQuantity, true) / baseStep * baseStep;
      if (quantity > cap) quantity = cap;
    }
    if (quantity <= 0n || quantity < decimal(product.base_min_size, true) || price * quantity / SCALE < decimal(product.quote_min_size, true)) refuse('order_below_minimum', 409);
    const gross = ceil(price * quantity / SCALE, USD_CENT); const fees = ceil(gross * rate / SCALE, USD_CENT);
    if (gross + fees > budget) refuse('budget_exceeded', 403);
    const order = { product_id: productId, side: trade.side.toUpperCase(), order_configuration: { sor_limit_ioc: { base_size: decimalText(quantity), limit_price: decimalText(price) } }, retail_portfolio_id: portfolioId };
    this.available(accounts, order, decimalText(fees), minimumBaseBalance);
    const preview = await this.preview(order, fees);
    return { order, previewId: preview.preview_id, feeCap: decimalText(fees), takerRate: decimalText(rate),
      quote: { id: preview.preview_id, priceUsd: Number(decimalText(price)), quantity: Number(decimalText(quantity)), feesUsd: Number(decimalText(fees)), maxSpendUsd: Number(decimalText(gross + fees)), quotedAt: at(), expiresAt: at() + 20 } };
  }
  async submitRequest(plan, portfolioId, clientOrderId, minimumBaseBalance = null) {
    await this.permissions(portfolioId);
    const orders = await this.orders(portfolioId);
    if (orders.some(row => row.client_order_id === clientOrderId)) refuse('client_order_already_exists', 409);
    if (orders.some(row => !TERMINAL.has(row.status))) refuse('venue_orders_open', 409);
    const summary = await this.call('GET', `${PREFIX}/transaction_summary`);
    if (decimal(summary?.fee_tier?.taker_fee_rate) > decimal(plan.takerRate)) refuse('fee_changed', 409);
    const preview = await this.preview(plan.order, decimal(plan.feeCap));
    // Fresh, portfolio-bound available balances prevent borrowing or selling
    // inventory already consumed elsewhere, including reduce-only recovery.
    this.available(await this.accounts(portfolioId), plan.order, plan.feeCap, minimumBaseBalance);
    // Construct/sign before the final DB grant check. Caller starts fetch without another await.
    return this.signedRequest('POST', `${PREFIX}/orders`, { ...plan.order, client_order_id: clientOrderId, preview_id: preview.preview_id });
  }
  async send(request, clientOrderId) {
    const value = await this.response(request);
    if (value?.success !== true || !uuid(value.success_response?.order_id) || value.success_response.client_order_id !== clientOrderId) refuse('provider_outcome_unknown', 503);
    return value.success_response.order_id;
  }
  async reconcile(plan, portfolioId, clientOrderId, orderId = null) {
    let order;
    if (orderId) {
      if (!uuid(orderId)) refuse('reconciliation_unavailable', 503);
      order = (await this.call('GET', `${PREFIX}/orders/historical/${orderId}`))?.order;
    } else {
      const found = (await this.orders(portfolioId)).filter(row => row.client_order_id === clientOrderId);
      if (found.length > 1) refuse('reconciliation_unavailable', 503);
      if (!found.length) return { status: 'unknown', orderId: null, filled: null };
      [order] = found;
    }
    const config = order?.order_configuration?.sor_limit_ioc;
    if (!uuid(order?.order_id) || order.client_order_id !== clientOrderId || order.retail_portfolio_id !== portfolioId || order.product_id !== plan.order.product_id || order.side !== plan.order.side || !config || decimal(config.base_size, true) !== decimal(plan.order.order_configuration.sor_limit_ioc.base_size, true) || decimal(config.limit_price, true) !== decimal(plan.order.order_configuration.sor_limit_ioc.limit_price, true)) refuse('reconciliation_binding_invalid', 503);
    const allowed = new Set(['PENDING', 'OPEN', 'FILLED', 'CANCELLED', 'EXPIRED', 'FAILED', 'QUEUED', 'CANCEL_QUEUED', 'EDIT_QUEUED']);
    if (!allowed.has(order.status)) return { status: 'unknown', orderId: order.order_id, filled: null };
    if (!TERMINAL.has(order.status)) return { status: 'submitted', orderId: order.order_id, filled: null };
    const quantity = decimal(order.filled_size); const value = decimal(order.filled_value); const fees = decimal(order.total_fees);
    if (quantity > decimal(plan.order.order_configuration.sor_limit_ioc.base_size) || (quantity === 0n) !== (value === 0n) || (order.status === 'FILLED' && quantity === 0n)) refuse('reconciliation_economics_invalid', 503);
    return { status: order.status === 'FILLED' ? 'filled' : order.status === 'FAILED' ? 'failed' : 'canceled', orderId: order.order_id,
      filled: { quantity: decimalText(quantity), valueUsd: decimalText(value), feesUsd: decimalText(fees), venueStatus: order.status, asOf: at() } };
  }
}
