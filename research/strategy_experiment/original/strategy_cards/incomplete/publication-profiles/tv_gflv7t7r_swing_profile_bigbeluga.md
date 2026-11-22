---

id: tv_profile_gflv7t7r

name: "Swing Profile [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Swing Profile profiles volume within directional swing legs instead of fixed sessions. It updates the active leg as structure develops, then freezes the profile when direction flips, preserving a sequence of completed-swing activity maps. The intended use is comparing participation through trends and retracements; its buy/sell labels are explicitly candle-direction classifications rather than actual trade-side identification."

registry_key: null

runner: null

evaluation: null

---

# Swing Profile [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Swing Profile profiles volume within directional swing legs instead of fixed sessions. It updates the active leg as structure develops, then freezes the profile when direction flips, preserving a sequence of completed-swing activity maps. The intended use is comparing participation through trends and retracements; its buy/sell labels are explicitly candle-direction classifications rather than actual trade-side identification.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Swing confirmation, ATR-bin scaling, volume allocation, delta denominator, PoC tie rule and finalization timing are unspecified.

- Swing confirmation, ATR-bin scaling, volume allocation, delta denominator, PoC tie rule and finalization timing are unspecified.

## How it works

- Confirm swing highs/lows using Swing Length, aggregate volume between anchors and choose ATR-adaptive bin size.
- Separate bullish/bearish candle volume, calculate percentage delta, highlight PoC and render outline/heatmap options; finalize when direction reverses.

## Outputs and intended use

- Inspect swing-specific concentration, PoC and delta for pullback/continuation context, with T/B/S/D labels for total/bull/bear/delta.

## Parameters and stated settings

- Swing Length controls anchor detection; ATR bins, heatmap and label size are described without numeric defaults or formulas.

## Failure modes and caveats

- Analytical: the active profile is provisional and confirmed swing anchors can be recognized late; candle volume split is not aggressor volume. The text also describes volume-PoC as time spent inconsistently.

## Missing information and implementation boundary

- Swing confirmation, ATR-bin scaling, volume allocation, delta denominator, PoC tie rule and finalization timing are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
profile continuously recalculates and redraws.
```

### E2: mechanism, readiness

```text
Buy volume (bullish candles).
```

### E3: mechanism, readiness

```text
Sell volume (bearish candles).
```

### E4: mechanism, readiness

```text
bin size is automatically scaled using ATR
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_gflv7t7r_swing_profile_bigbeluga](../tv_gflv7t7r_swing_profile_bigbeluga.md)

## Source

https://www.tradingview.com/script/gFlv7t7R-Swing-Profile-BigBeluga/

Publication ID: gFlv7t7R. Source SHA-256: 66d89519d74d4b53a19ede0d84b3dd63dbc28aa700c95cb842a69223b11e953d. Raw-description SHA-256: 0e62200457bc5be69211c1dbc639b1a6e1c6bed436687ed8f9ab2215392e39ea.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
