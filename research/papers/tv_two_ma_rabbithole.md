# TradingView two moving averages: research draft

Version: 0.1.0. Delta: record source, adapter and proxy sensitivity. This is
not a qualified rabbithole or registered strategy card.

## Source-specific contract

Official built-in `STD;MovingAvg%1Cross2%1Strategy`, version 31.0, is pinned
as `src:bcf0c7a7cb59abb1`, SHA-256
`811195bd717c8c71ca341240884bdcc367f7a5d59f2c652270cffe24538aa678`.
It computes two simple averages of close, default lengths 9 and 18, and calls
`ta.crossover` and `ta.crossunder` to issue long `MA2CrossLE` and short
`MA2CrossSE` market entries. The source does not specify quantity. The
historical versions 29.0 and 30.0 have identical source SHA-256
`ee859af730d538290c5bdf3dd91307113c68cf37243be7ccc90fc5ceec56b811`;
changing only their strategy declaration reproduces version 31 source. The
version active on the user's chart remains unknown.

The draft adapter uses current strict inequality and previous non-strict
comparison for crossover events. Its tests cover first-defined averages,
equality, direction changes, missing-data refusal, and causal prefixes. Exact
Pine v6 crossover and missing-value behavior still require authoritative
reference verification and an independent trace. The existing `ma_crossover`
uses 20/50 defaults and persistent exposure; do not change its historical
behavior or assume its coverage mapping establishes equivalence.

Use a distinct source-specific 9/18 event-crossover identity and card after
independent contract review. Reconcile the existing coverage mapping through
its owning checksum-aware helper. Preserve the generic 20/50 implementation
and its historical results. Register only after card defaults, shared order
engine, schema and traces agree.

## Retrospective proxy sensitivity

The shared prior Jupiter ZEC/USD oracle window contains 41,640 contiguous
minutes from 2026-10-10 21:00 UTC through 2026-11-08 19:00 UTC exclusive.
The comparator uses $100,000 initial cash and $1,000 target notional based on
the signal close. The next-open fill notional can differ. A $1,000 unlevered
buy-and-hold position gained $33.31 before costs over the same window. Fresh
ZEC and BTC reservation checks surrounded each simulation. Open positions
are marked at the last close, not forcibly liquidated.

| Bars | Assumed cost per side | P&L | Closed trades | Max drawdown |
| --- | --- | ---: | ---: | ---: |
| 10 minutes | zero | +$545.33 | 257 | 0.157% |
| 10 minutes | 10 bp fee + 1 bp slippage | -$21.26 | 257 | 0.351% |
| 15 minutes | zero | +$588.84 | 163 | 0.166% |
| 15 minutes | 10 bp fee + 1 bp slippage | +$229.07 | 163 | 0.196% |

The 10-minute test has one unfilled final market intent. These results reuse a
historical oracle series and are not Coinbase perpetual or TradingView
replication, out-of-sample evaluation, or live-net results. Funding, spread
beyond the slippage scenario, margin, liquidation, and actual account settings
are unknown. Native result:
`art:2225ec8c5c1d8e66f04a862acdac83d73ca315fff991f356a380f90066d165fc`.

Mongo run `run:ecf1f26797059dc6f5505d5343fd0a1e18692e837a29892489578c0b5317ecf2`
remains unqualified. Complete exact-source dedup, independent negation,
atomic claims, measured depth passes and trusted gate before a final verdict.
