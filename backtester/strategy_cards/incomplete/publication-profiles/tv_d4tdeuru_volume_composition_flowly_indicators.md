---

id: tv_profile_d4tdeuru

name: "Volume composition / Flowly Indicators"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Volume Composition decomposes lower-timeframe candle volume into directional and rising/falling-volume subsets. It aims to reveal whether total attributed pressure agrees with the subset labeled active. Here active means volume increased from the preceding intrabar, not directly observed market-order aggression. Disagreement can flag a context worth inspecting, while volume spikes can be interpreted as continuation or absorption only with additional price evidence. The method supplies a more detailed activity proxy than one signed parent-candle total."

registry_key: null

runner: null

evaluation: null

---

# Volume composition / Flowly Indicators

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Composition decomposes lower-timeframe candle volume into directional and rising/falling-volume subsets. It aims to reveal whether total attributed pressure agrees with the subset labeled active. Here active means volume increased from the preceding intrabar, not directly observed market-order aggression. Disagreement can flag a context worth inspecting, while volume spikes can be interpreted as continuation or absorption only with additional price evidence. The method supplies a more detailed activity proxy than one signed parent-candle total.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Source defines a reproducible parameterized computation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Assign lower-timeframe volume by selected-source change; rising source is buy and falling source sell.
- Split each direction into active/passive according to increasing/decreasing volume versus the previous intrabar.
- Sum directional/active totals, compute dominant shares and highlight threshold breaches or side disagreement.

## Outputs and intended use

- Nested volume nodes, dominant percentages/signs, divergence brackets and optional anomaly bar colors support participation analysis.

## Parameters and stated settings

- Default LTF mapping: ≤30m→1m; ≤3H→5m; ≤8H→15m; ≤1D→1H; ≤3D→2H; above→4H.
- Dominant total/active thresholds default70%; source/timeframes/symbol can change. Optional rounded shares map54%→5 and55%→6.

## Failure modes and caveats

- Active/passive labels are proxies and do not establish actual order types or trapped positions.
- Finer LTF improves detail but reduces coverage and increases loading cost.

## Missing information and implementation boundary

- Equal-price/equal-volume handling, zero totals and intrabar boundary state are absent; central decomposition is parameterized.

## Data requirements

Required inputs: lower-timeframe ohlcv, optional external symbol history.

Repository input-class support: unavailable or unresolved. Requires compatible intrabars; external symbol choice and depth are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Charts <= 30 min: 1 minute timeframe
Charts > 30 min & <= 3 hours : 5 minute timeframe
Charts > 3 hours & <= 8 hours : 15 minute timeframe
Charts > 8 hours & <= 1D: 1 hour timeframe
Charts > 1D & <= 3D : 2 hour timeframe
Charts > 3D: 4 hour timeframe
```

### E2: parameters

```text
70% of total volume by default.
```

### E3: parameters

```text
70% by default.
```

### E4: parameters

```text
54% = 5
```

### E5: parameters

```text
55% = 6
```

### E6: mechanism, readiness

```text
move up with volume higher than previous bar volume = active buy volume
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_d4tdeuru_volume_composition_flowly_indicators](../../tv_d4tdeuru_volume_composition_flowly_indicators.md)
- [tv_method_volume_delta](../../tv_method_volume_delta.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/d4TDeuRU-Volume-composition-Flowly-Indicators/

Publication ID: d4TDeuRU. Source SHA-256: 41b9c6f992c9620ac78da9bbff9feec3e925f6148ef72ab77c4c12297503a333. Raw-description SHA-256: 3426a5fca2c3c09a81060aed7f9427d0671578d0f32ba3ccbf315560e74b2782.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
