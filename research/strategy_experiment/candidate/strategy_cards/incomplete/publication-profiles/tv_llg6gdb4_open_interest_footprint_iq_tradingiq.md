---

id: tv_profile_llg6gdb4

name: "Open Interest Footprint IQ [TradingIQ]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Visualize cryptocurrency open-interest changes by intrabar price level. The footprint labels opening/closing behavior inferred from price direction and OI change, making it a positioning proxy rather than direct observation of which participant initiated a trade."

registry_key: null

runner: null

evaluation: null

---

# Open Interest Footprint IQ [TradingIQ]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Visualize cryptocurrency open-interest changes by intrabar price level. The footprint labels opening/closing behavior inferred from price direction and OI change, making it a positioning proxy rather than direct observation of which participant initiated a trade.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Four nonzero price/OI sign labels is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Retrieve lower-timeframe price ranges, direction and OI changes. Rising price with rising OI is labeled longs opening; rising price/falling OI shorts closing; falling price/rising OI shorts opening; falling price/falling OI longs closing.
- Aggregate categories into footprint price levels, either resetting each bar or accumulating until a selected reset boundary. Delta and percentage overlays summarize net change.
- A value-area/POC view highlights concentration. Level delta exceeding a selected imbalance percentage produces markers; consecutive imbalanced levels trigger an alert.
- Given synchronized nonzero price/OI changes classify(+,+)=UU longs opening,(+,-)=UD shorts closing,(-,+)=DU shorts opening,(-,-)=DD longs closing. These reproduce heuristic labels,not true participant identification. Zero cases,footprint rows,delta percentages/value area remain outside scope;external OI is still required.

## Outputs and intended use

- Boxes display delta, delta percentage and inferred long/short opening/closing categories, with category or simple up/down colors.
- The author suggests absorption/exhaustion and entry-context use; chart data does not verify those causal interpretations.
- Usable scope: Four nonzero price/OI sign labels. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- One-minute, one-second or one-tick granularity; manual tick spacing or zero for ATR-based automatic spacing.
- Cumulative/reset timeframe, value-area percentage, imbalance threshold/count and visibility/colors.

## Failure modes and caveats

- An OI increase creates both a long and short contract; direction-based attribution cannot uniquely identify longs or shorts opening.
- Tick/second histories and OI timestamps may have different coverage. Signed changes also make a percentage-containing value area ambiguous.

## Missing information and implementation boundary

- Price-level allocation, ATR spacing formula, delta denominator, value-area/POC calculation and zero-price-change handling are absent.

## Data requirements

Required inputs: lower-timeframe crypto price bars or ticks, exchange-specific synchronized open interest history, instrument tick size.

Repository input-class support: unavailable or unresolved. Exchange-specific synchronized lower-timeframe open interest is required and is not established as available.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, readiness

```text
Options: 1-Minute, 1-Second, 1-Tick
```

### E2: purpose, mechanism, parameters, outputs_and_use, readiness

```text
If 0, the script uses an automatic calculation based on ATR to adapt to volatility.
```

### E3: purpose, mechanism, parameters, outputs_and_use, readiness

```text
OI data must be available from the exchange
```

### E4: purpose, mechanism, parameters, outputs_and_use, readiness

```text
If the number of consecutive imbalance levels meets this count, a “Stacked Imbalance” alert will trigger.
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
[*]If price is moving up and open interest is increasing, it suggests that long positions are being opened. This is considered a "Longs Opening" event, labeled as UU (Up/Up).
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
[*]If price is moving up but open interest is decreasing, it indicates that short positions are being closed. This is referred to as UD (Up/Down), or "Shorts Closing."
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
[*]If price is moving down and open interest is increasing, it signals that short positions are being opened. This is known as DU (Down/Up), or "Shorts Opening."
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
[*]If price is moving down while open interest is also decreasing, it means that long positions are being closed. This is labeled as DD (Down/Down), or "Longs Closing."
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_llg6gdb4_open_interest_footprint_iq_tradingiq](../tv_llg6gdb4_open_interest_footprint_iq_tradingiq.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/lLG6gDb4-Open-Interest-Footprint-IQ-TradingIQ/

Publication ID: lLG6gDb4. Source SHA-256: c52ef4f86e18a8b2f3ea17ebc9e2c34415370873b4e3c7040ae74b718cdabd48. Raw-description SHA-256: 1676d03c2776a14c96d1143e3bd43be30af2d941e36db82a8912a3e5c0a89596.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
