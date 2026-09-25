/**
 * Kraken REST and WebSocket venue adapter.
 * Handles live order execution and margin capabilities on Kraken.
 */

export class KrakenVenue {
  constructor({ baseMint, quoteMint, apiKey, apiSecret, fetchImpl = globalThis.fetch }) {
    this.id = 'kraken-live';
    this.kind = 'spot_margin';
    this.base = baseMint; // e.g., 'XBT'
    this.quote = quoteMint; // e.g., 'USD'
    this.pair = `${this.base}${this.quote}`;
    this.apiKey = apiKey;
    this.apiSecret = apiSecret;
    this.fetch = fetchImpl;
    
    this.baseUrl = 'https://api.kraken.com';
    this.wsAuthUrl = 'wss://ws-auth.kraken.com';
  }

  get capabilities() {
    return {
      canPlaceLive: true,
      supportsLeverage: true,
      supportsUpdateInPlace: false,
      supportsBrackets: false,
      minOrderUsd: 5.0, // Typical Kraken minimum
    };
  }

  async _getSignature(path, request, nonce) {
    if (!this.apiSecret) throw new Error('Kraken API secret missing');
    
    // WebCrypto implementation of Kraken's signature
    const message = request;
    const secret_buffer = Uint8Array.from(atob(this.apiSecret), c => c.charCodeAt(0));
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(nonce + message));
    
    const hmacAlgo = { name: 'HMAC', hash: 'SHA-512' };
    const key = await crypto.subtle.importKey('raw', secret_buffer, hmacAlgo, false, ['sign']);
    
    const pathBuffer = new TextEncoder().encode(path);
    const data = new Uint8Array(pathBuffer.length + hash.byteLength);
    data.set(pathBuffer);
    data.set(new Uint8Array(hash), pathBuffer.length);
    
    const signature = await crypto.subtle.sign('HMAC', key, data);
    return btoa(String.fromCharCode(...new Uint8Array(signature)));
  }

  async _privateRequest(endpoint, payload = {}) {
    if (!this.apiKey) throw new Error('Kraken API key missing');
    const nonce = Date.now().toString();
    const body = new URLSearchParams({ nonce, ...payload }).toString();
    
    const signature = await this._getSignature(endpoint, body, nonce);
    
    const res = await this.fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'API-Key': this.apiKey,
        'API-Sign': signature,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body
    });
    const data = await res.json();
    if (data.error && data.error.length > 0) {
      throw new Error(`Kraken API Error: ${data.error.join(', ')}`);
    }
    return data.result;
  }

  async getPrice() {
    const res = await this.fetch(`${this.baseUrl}/0/public/Ticker?pair=${this.pair}`);
    const data = await res.json();
    if (data.error && data.error.length > 0) throw new Error(data.error.join(', '));
    const pairKey = Object.keys(data.result)[0];
    return parseFloat(data.result[pairKey].c[0]);
  }

  async getDecimals() {
    return { base: 8, quote: 2 };
  }

  async getOpenOrders() {
    const result = await this._privateRequest('/0/private/OpenOrders');
    if (!result || !result.open) return [];
    
    return Object.entries(result.open).map(([id, order]) => ({
      venueOrderId: id,
      status: 'active',
      side: order.descr.type,
      triggerPriceUsd: parseFloat(order.descr.price),
      intentKey: order.userref?.toString(),
      createdAtMs: parseInt(order.opentm * 1000)
    }));
  }

  async getFills() {
    const result = await this._privateRequest('/0/private/TradesHistory');
    if (!result || !result.trades) return [];
    
    return Object.entries(result.trades).map(([id, trade]) => ({
      venueOrderId: trade.ordertxid,
      status: 'filled',
      side: trade.type,
      executedPriceUsd: parseFloat(trade.price),
      intentKey: null,
      updatedAtMs: parseInt(trade.time * 1000)
    }));
  }

  async getCarryCosts() {
    // Requires parsing OpenPositions to find rollover fees
    const result = await this._privateRequest('/0/private/OpenPositions');
    if (!result) return [];
    
    let totalCost = 0;
    for (const pos of Object.values(result)) {
      totalCost += parseFloat(pos.fee);
      totalCost += parseFloat(pos.rollover); // Margin rollover costs
    }
    return [{ tsMs: Date.now(), costUsd: totalCost }];
  }

  async placeOrder({ intent, slippageBps, leverage = 1 }) {
    const payload = {
      pair: this.pair,
      type: intent.side, // 'buy' or 'sell'
      ordertype: 'limit',
      price: intent.level.toString(),
      volume: intent.size.toString(),
      userref: intent.intentKey
    };
    
    if (leverage > 1) {
      payload.leverage = leverage.toString();
    }
    
    const result = await this._privateRequest('/0/private/AddOrder', payload);
    return {
      venueOrderId: result.txid[0],
      txSignature: null,
      confirmed: true
    };
  }

  async cancelOrder({ venueOrderId }) {
    const result = await this._privateRequest('/0/private/CancelOrder', { txid: venueOrderId });
    return { cancelled: result.count > 0 };
  }
}
