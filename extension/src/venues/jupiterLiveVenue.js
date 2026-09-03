/**
 * Live Jupiter execution venue (standard Swaps).
 */
import { request } from './http.js';

export class JupiterLiveVenue {
  constructor({ baseMint, quoteMint, userPubkey, signer, budget, fetchImpl }) {
    this.id = 'jupiter-live';
    this.kind = 'spot';
    this.baseMint = baseMint;
    this.quoteMint = quoteMint;
    this.userPubkey = userPubkey;
    this.signer = signer;
    this.budget = budget;
    this.fetchImpl = fetchImpl;
  }

  get capabilities() {
    return {
      canPlaceLive: true,
      supportsLeverage: false,
      supportsUpdateInPlace: false,
      supportsBrackets: false,
      minOrderUsd: 1.0,
    };
  }

  async getPrice() {
    // Fetch price from Jupiter Price API
    const res = await this.fetchImpl(`https://price.jup.ag/v6/price?ids=${this.baseMint}&vsToken=${this.quoteMint}`);
    const data = await res.json();
    return data.data[this.baseMint].price;
  }

  async getDecimals() {
    return { base: 9, quote: 6 }; // Assuming standard SPL tokens (SOL=9, USDC=6)
  }

  async getOpenOrders() {
    return []; // Standard swaps don't have "open orders" in the same way limit/trigger orders do.
  }

  async getFills() {
    return []; // Managed via websocket event listeners
  }

  async getCarryCosts() {
    return []; // Spot trades have no carry costs
  }

  async placeOrder({ intent, slippageBps }) {
    // 1. Get Quote
    const amountStr = intent.size.toString(); // Would need decimal conversion in production
    const sideParams = intent.side === 'buy'
      ? `inputMint=${this.quoteMint}&outputMint=${this.baseMint}&amount=${amountStr}`
      : `inputMint=${this.baseMint}&outputMint=${this.quoteMint}&amount=${amountStr}`;
    
    const quoteUrl = `https://quote-api.jup.ag/v6/quote?${sideParams}&slippageBps=${slippageBps}`;
    const quoteRes = await this.fetchImpl(quoteUrl);
    const quoteData = await quoteRes.json();

    // 2. Build Transaction
    const swapReq = {
      quoteResponse: quoteData,
      userPublicKey: this.userPubkey,
      wrapAndUnwrapSol: true
    };
    
    const txData = await request('/swap', 'POST', swapReq, { budget: this.budget, fetchImpl: this.fetchImpl });
    
    // 3. Sign & Send (Delegated to signer)
    if (!this.signer) throw new Error('No signer provided for live execution');
    const signature = await this.signer.signAndSend(txData.swapTransaction);
    
    return {
      venueOrderId: signature,
      txSignature: signature,
      confirmed: true
    };
  }

  async cancelOrder() {
    throw new Error('Cannot cancel a market swap order');
  }
}
