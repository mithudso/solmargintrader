/** Local provider-contract stand-in. All quote values are documentation fixtures. */
const http = require('http');
const example = {
  "inputMint": "So11111111111111111111111111111111111111112",
  "inAmount": "100000000",
  "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  "outAmount": "16198753",
  "otherAmountThreshold": "16117760",
  "swapMode": "ExactIn",
  "slippageBps": 50,
  "platformFee": null,
  "priceImpactPct": "0",
  "routePlan": [
    {
      "swapInfo": {
        "ammKey": "5BKxfWMbmYBAEWvyPZS9esPducUba9GqyMjtLCfbaqyF",
        "label": "Meteora DLMM",
        "inputMint": "So11111111111111111111111111111111111111112",
        "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "inAmount": "100000000",
        "outAmount": "16198753",
        "feeAmount": "24825",
        "feeMint": "So11111111111111111111111111111111111111112"
      },
      "percent": 100
    }
  ],
  "contextSlot": 299283763,
  "timeTaken": 0.015257836
};
let mode = 'success';
let quoteRequests = 0;
const modes = new Set(['success', 'rate_limit', 'html_error', 'malformed', 'wrong_mints', 'slow']);
function reply(res, code, body, type = 'application/json') {
  res.writeHead(code, { 'Content-Type': type });
  res.end(type === 'application/json' ? JSON.stringify(body) : body);
}
const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  // Fixture control routes are local test infrastructure, never provider API.
  if (req.method === 'POST' && url.pathname === '/__control') {
    const next = url.searchParams.get('mode');
    if (!modes.has(next)) return reply(res, 400, { error: 'unknown_fixture_mode' });
    mode = next;
    quoteRequests = 0;
    return reply(res, 200, { mode, quoteRequests });
  }
  if (req.method === 'GET' && url.pathname === '/__control') {
    return reply(res, 200, { mode, quoteRequests });
  }
  if (req.method !== 'GET' || url.pathname !== '/swap/v1/quote') {
    return reply(res, 501, { error: 'operation_not_modelled' });
  }
  quoteRequests += 1;
  for (const [key, value] of Object.entries({ inputMint: example.inputMint,
      outputMint: example.outputMint, amount: example.inAmount,
      slippageBps: '50', swapMode: 'ExactIn', onlyDirectRoutes: 'true' })) {
    if (url.searchParams.get(key) !== value) return reply(res, 400, { error: 'fixture_request_mismatch', field: key });
  }
  if (mode === 'rate_limit') {
    res.setHeader('Retry-After', '1');
    return reply(res, 429, { error: 'rate_limited' });
  }
  if (mode === 'html_error') return reply(res, 503, '<html>fixture unavailable</html>', 'text/html');
  if (mode === 'malformed') return reply(res, 200, '{invalid', 'application/json; charset=utf-8');
  if (mode === 'slow') await new Promise(resolve => setTimeout(resolve, 500));
  const response = structuredClone(example);
  if (mode === 'wrong_mints') response.outputMint = example.inputMint;
  return reply(res, 200, response);
});
server.listen(process.env.PORT || 4500);
