---

id: tv_profile_ks2qgulb

name: "Initial Balance Auction Intelligence by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Initial Balance Auction Intelligence follows how price behaves after an opening range, separating tentative probes from completed-window acceptance or failure. It layers retest continuation/rejection, session character and cumulative directional pressure over the basic IB references. The goal is auction context, explicitly not standalone signals or actual order-flow measurement."

registry_key: null

runner: null

evaluation: null

---

# Initial Balance Auction Intelligence by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Initial Balance Auction Intelligence follows how price behaves after an opening range, separating tentative probes from completed-window acceptance or failure. It layers retest continuation/rejection, session character and cumulative directional pressure over the basic IB references. The goal is auction context, explicitly not standalone signals or actual order-flow measurement.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** IB references and basic acceptance/failure is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Establish opening-session high/low/midpoint, then evaluate each completed post-IB window against those boundaries.
- Classify outside closes as accepted and beyond-boundary extensions closing inside as failed; track subsequent retest holds/failures and two-sided rejection.
- Accumulate bounded session pressure and grade event quality/maturity with additional price-structure criteria.
- Over caller initial-balance window take H=max(high),L=min(low),R=H-L,M=(H+L)/2. Project H+kR and L-kR for k=0.5,1,1.5. After completed IB,close outside H/L indicates acceptance;an outside excursion/extension followed by close back inside indicates failure under the source rule. Caller defines observation window/boundaries;pressure,quality,retest and advanced states excluded.

## Outputs and intended use

- Read dashboard regime/bias/phase/state/pressure/quality and invalidation together; confirmed state transitions support alerts, while live decision candles remain provisional.
- Usable scope: IB references and basic acceptance/failure. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Post-IB windows include 5/10/15/30 minutes; extension references use 0.5/1/1.5 times IB range. Pressure spans -100 to +100.
- Engine operates on intraday charts at most thirty minutes and uses one-minute data on larger intraday bars. Session/timezone are configurable.

## Failure modes and caveats

- Analytical: acceptance is a configured completed-window rule, not proof of durable market acceptance; projected extensions are expressly not guaranteed targets.

## Missing information and implementation boundary

- Quality/pressure/maturity formulas, retest tolerances, IB schedule defaults, regime transitions and invalidation calculations are not fully specified.

## Data requirements

Required inputs: one-minute OHLCV, caller IB session/timezone and duration.

Repository input-class support: available. Ordinary historical OHLCV/price inputs for caller-selected symbols are a supported data class. Exact selected-symbol cache coverage, synchronization and adjustments remain unverified; no dynamic point-in-time universe is required by the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
5/10/15/30 min
```

### E2: parameters, readiness

```text
0.5×, 1.0×, and 1.5× the IB range
```

### E3: parameters, readiness

```text
bounded −100..+100
```

### E4: parameters, readiness

```text
intraday timeframes ≤ 30 minutes
```

### E5: parameters, readiness

```text
1-minute lower-timeframe data
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
[b]Initial Balance Projections[/b] (optional) extend reference levels above IBH and below IBL at [b]0.5×, 1.0×, and 1.5× the IB range[/b]. These are reference levels for evaluating potential range extension - [b]not predicted or guaranteed targets[/b].[image]https://www.tradingview.com/x/KxegeHBY/[/image][/quote]
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
[b]Initial Balance Projections[/b] (optional) extend reference levels above IBH and below IBL at [b]0.5×, 1.0×, and 1.5× the IB range[/b]. These are reference levels for evaluating potential range extension - [b]not predicted or guaranteed targets[/b].[image]https://www.tradingview.com/x/KxegeHBY/[/image][/quote]
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
[b]Acceptance · Failed Auction · Retest / Continuation · Rejection · Two-Sided Auction[/b]
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
[quote][b]Conviction/Quality[/b] combines close strength, IB-relative extension, and retest behavior to grade confirmed events - Acceptance/Continuation use acceptance criteria, while Failed/Rejection/Two-Sided use failure criteria. [b]Maturity[/b] tracks how long a state has held (Early → Developing → Mature → Exhausted).
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ks2qgulb_initial_balance_auction_intelligence_by_dgt](../tv_ks2qgulb_initial_balance_auction_intelligence_by_dgt.md)
- [tv_method_opening_range](../tv_method_opening_range.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/ks2QGulb-Initial-Balance-Auction-Intelligence-by-DGT/

Publication ID: ks2QGulb. Source SHA-256: b8b52a068b9b3cecb406d8f614d527b154c7e53228f7ecd6fa7e877f30d5bdf5. Raw-description SHA-256: a5b598e486246ac641794735503d0d4dd4733677556fa6865a18ced2776f94c2.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
