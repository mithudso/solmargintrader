/**
 * Jupiter / Solana native RPC WebSocket integration.
 * Subscribes to account/log events for real-time trade data and execution feedback
 * without polling.
 */

export class JupiterWebsocket {
  constructor({ rpcWsUrl, userPubkey, onTrade, onError }) {
    this.url = rpcWsUrl; // Must be wss://
    this.userPubkey = userPubkey;
    this.onTrade = onTrade;
    this.onError = onError;
    this.ws = null;
    this.subscriptionId = null;
    this.reconnectAttempts = 0;
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this._subscribe();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this._handleMessage(data);
      } catch (err) {
        if (this.onError) this.onError(err);
      }
    };

    this.ws.onclose = () => {
      this.subscriptionId = null;
      this._reconnect();
    };

    this.ws.onerror = (err) => {
      if (this.onError) this.onError(err);
    };
  }

  _subscribe() {
    // Subscribe to logs for the user's public key to detect any swap transactions
    const req = {
      jsonrpc: '2.0',
      id: 1,
      method: 'logsSubscribe',
      params: [
        { mentions: [this.userPubkey] },
        { commitment: 'confirmed' }
      ]
    };
    this.ws.send(JSON.stringify(req));
  }

  _handleMessage(data) {
    // Handle subscription confirmation
    if (data.id === 1 && data.result) {
      this.subscriptionId = data.result;
      return;
    }

    // Handle incoming logs
    if (data.method === 'logsNotification') {
      const logs = data.params.result.value.logs;
      const signature = data.params.result.value.signature;
      
      // Basic heuristic to detect a Jupiter swap in the logs
      const isJupiterSwap = logs.some(log => log.includes('Program JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4 invoke'));
      
      if (isJupiterSwap && this.onTrade) {
        this.onTrade({ signature, logs, timestamp: Date.now() });
      }
    }
  }

  _reconnect() {
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;
    setTimeout(() => this.connect(), delay);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
