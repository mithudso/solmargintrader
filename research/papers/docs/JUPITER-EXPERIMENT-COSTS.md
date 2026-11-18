# Jupiter experiment costs

Spot swaps and perpetual positions are separate products. Do not apply a perps fee to a spot swap.

For a SOL/USDC spot round trip, derive the realized return from the actual quote or fills: `(USDC received after the sell - USDC spent on the buy - separately paid network and priority fees) / USDC spent on the buy`. Include any fees not already reflected in the quoted output, but do not subtract the same route or platform fee twice. Quotes change with size, liquidity and market conditions; a fixed Coinbase fee schedule is not a Jupiter quote. Historical simulations without archived executable quotes must label their assumed slippage and fees.

For a Jupiter JLP SOL perpetual, the published base fee is 6 basis points on position notional both when opening and when closing. A simple closed-position estimate, before liquidation, is:

```
net PnL = signed price PnL - opening base fee - closing base fee
          - price-impact fees - accrued borrow fees - collateral swap costs
          - transaction / priority fees
return on collateral = net PnL / starting collateral
```

For a position of $1,000, the base fees alone are approximately $1.20 round trip, assuming unchanged notional. At 10x leverage on $100 collateral, that is 1.2% of collateral. Entry and exit notional may differ. Borrow rates and price impact change; they cannot be reconstructed honestly from a fixed cost without saved venue observations. A leveraged simulation also needs intraperiod high/low or finer data and a liquidation model, including adverse fills and fees. Missing paths or costs should be marked unknown rather than presented as a precise return.

The supplied Jupiter reference describes linear and additive impact charges, but elsewhere calls standard fills zero-impact. Current Jupiter fee documentation describes both impact components. Treat the charge as venue- and size-dependent and verify the live custody parameters; do not assume zero.

The current paper-experiment default is 6 basis points of fees plus 2 basis points of slippage per side, or 16 basis points round trip. The published Jupiter Perps base fee alone is 12 basis points round trip, a difference of $0.40 on $1,000 notional. That comparison does not establish which total cost is lower: the default includes a slippage assumption, while the 12-basis-point figure excludes impact, borrowing, swaps, and network costs. Existing experiments freeze their selected cost assumptions when started.

Jupiter documents a trader-selectable range of 1.1x to 250x for the JLP SOL, ETH, and wBTC markets. Its 500x protocol parameter is used in its liquidation formula and is not the trader's maximum. Beta markets have separate limits and funding mechanics; check the selected market at order time.

Sources:

- https://docs.jup.ag/user-docs/trade/perps/fees
- https://docs.jup.ag/user-docs/trade/perps/faq
- https://docs.jup.ag/user-docs/trade/perps/liquidation
- https://docs.jup.ag/user-docs/trade/perps/beta-markets
- https://github.com/jup-ag/docs/blob/main/swap/order-and-execute.mdx

This document describes cost modeling. It does not assert that this repository can execute Jupiter perpetual orders or that its paper experiments already use these equations.
