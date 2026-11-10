# Jupiter Swap v1 quote simulation

Version: 1.0.0

This local stand-in exercises the real shared Oracle HTTP collector. It serves the provider documentation example for an ExactIn quote of 100000000 raw SOL to USDC, with 50 bps slippage and the manager's explicit `onlyDirectRoutes=true` policy. All prices, sizes, routes and slots are fixture values. They cannot establish current liquidity, complete costs, execution compatibility, fills or profitability. No swap, signer or submission endpoint exists.

The contract example is maintained in /Users/mitch/dev/solmargintrader/postman/collections/botmanager-swap-v1.postman_collection.json. The manually maintained handler adds strict request validation and failure controls; regeneration would overwrite those controls. Source contract: https://dev.jup.ag/docs/swap/get-quote

Start the local simulation with the installed Postman CLI 1.87.0:

```sh
postman simulation run /Users/mitch/dev/solmargintrader/postman/simulations/botmanager-swap-v1/botmanager-swap-v1.sim.yaml --port auto --no-history --output ndjson
```

The listening event reports its loopback port. The quote endpoint is /jupiter/swap/v1/quote under that loopback base. The collector accepts a loopback endpoint only with its internal explicit test override. Use a temporary quote-budget path; never touch the production shared budget during a fixture run. No Postman login, cloud workspace or provider credential is required. A literal fixture-only key exercises header serialization; never pass a real key to the stand-in.

POST /jupiter/__control?mode=success|rate_limit|html_error|malformed|wrong_mints|slow selects one failure at a time and resets the request counter. GET /jupiter/__control exposes the counter so acceptance can establish that a failure was not retried. These controls belong only to the test server. Other routes return 501 rather than pretending the provider supports them.

Source acceptance on 2026-11-10 passed nine cases through the actual urllib HTTP client: one valid reply stored as uncertified; 429, 503 HTML, invalid JSON, wrong mint, excessive latency and timeout each refused after one GET with no extra observation; disabled collection made zero GETs; another coin archive could not bypass a filled shared budget. This is simulated HTTP behavior. Installed code identity and actual source readiness remain separate acceptance gates. The final release handoff holds those receipts.
