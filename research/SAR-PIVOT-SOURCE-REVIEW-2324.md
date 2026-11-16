# SAR and Pivot Reversal source review checkpoint

Status: provisional source review, not a completed rabbithole or trusted publication. Each built-in has one primary software source organization, TradingView. Neither has met an independent-source floor, a measured two-pass novelty convergence test, completed deduplication, or trusted claim review. Six-pass budgets remain ceilings, not completed passes. No saturation is claimed. The source snapshots are private native research records; their redistribution license was not established. The cards describe derived behavior, not copied source.

## Parabolic SAR

TradingView built-in `STD;Parabolic%1SAR%1Strategy`, version 33.0, snapshot `src:260da27279d3c3e8`, SHA-256 `800f3fe7f02df408f9f144951e6e44744240a67dec2825d0953d5309b0a4bef1`. Defaults are start 0.02, increment 0.02, maximum 0.2. Initialization begins at bar index one, with direction based on consecutive closes. It updates trend, extreme point, acceleration and prior-bar clamps, computes next-bar SAR, submits the opposing stop and cancels the other entry. The independent audit must reconstruct recurrence and initialization, especially early bars and reversals; existing unit tests establish examples and prefix invariance, not full platform parity.

## Pivot Reversal

TradingView built-in `STD;Pivot%1Reversal%1Strategy`, version 33.0, snapshot `src:f1cf879aa1a71c9a`, SHA-256 `cd6def72548fb84e02312f302dd2799f897638d0a2c688aef04ca861b5a5628f`. Defaults are four left and two right bars. Confirmed high and low pivots arm long and short stop entries one instrument tick beyond the pivot. Source disarming does not explicitly cancel a pending entry. Equal-high and equal-low tie semantics for the built-in pivot functions remain unverified. Strict, earliest and latest policies are sensitivities; their agreement on this sample does not prove platform parity.

## Common comparison

The shared input is a previously collected Jupiter ZEC/USD oracle proxy, 2026-10-10 21:00 to 2026-11-08 19:00 UTC, 41,640 contiguous one-minute observations aggregated to complete 10- and 15-minute bars. It is neither Coinbase ZECUSDC.P nor an untouched out-of-sample test. Source quantity is unknown: results below use a research-only $1,000 target notional at completed signal close and $100,000 initial capital. Cost scenarios are zero cost and hypothetical 10 basis points fee plus one basis point slippage per side. Funding, actual spread, margin and liquidation are not modeled. The equal-notional values and fills remain subject to independent batch review.

| Strategy | Bar | Zero cost | Cost sensitivity | Closed trades |
|---|---:|---:|---:|---:|
| SAR | 10m | +0.3847% | -0.4021% | 357 |
| SAR | 15m | +0.5585% | +0.0402% | 235 |
| Pivot, strict tie | 10m | +0.8558% | +0.4542% | 182 |
| Pivot, strict tie | 15m | +0.6813% | +0.4092% | 123 |

Local full result `/Users/mitch/.local/state/zigzag-2333/sar-pivot-proxy-v1.json`, SHA-256 `34500e7e0ea258f2a9c17e15af1095e8f86c4cd9164de0355eef72a32ed5bd2d`, is archived and read back as native `art:7e77109f6437a43ef53e092d36447b52028432b42398b1f957717fdac72ca51f`. Data source is `art:daf887a414eb6078d63bbb2e557fbe6ebfc29433c43feaec69506a884bfda896`. Each scenario checks the current protected-interval ledger before and after execution. The emulator assumes a low-first OHLC path; real intrabar ordering and fills are unknown. The $0.01 tick is a TradingView scanner-derived assumption, not a measured Jupiter execution increment.

## Continuation

Reconcile the full selected-family queue census and leases before concept changes. Bind atomic claims to readable source spans, conduct genuinely distinct six-question research passes with independently qualified sources, and measure novelty and source floors. Run the trusted gate only if it can honor the user's model choice. Resolve Pivot tie semantics and validate SAR recurrence and common fill accounting independently. Keep both existing incomplete frozen cards untouched; these provisional versioned research cards are separate and must not be promoted or registered as verified TradingView implementations until those gates pass. Matching Coinbase data and contract multiplier, costs, funding and liquidation remain open.
