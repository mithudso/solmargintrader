---

id: tv_profile_cjnk8au1

name: "Volume Bubbles [QuantAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Highlight unusually large total-volume or estimated directional-delta events using percentile agreement across several history windows."

registry_key: null

runner: null

evaluation: null

---

# Volume Bubbles [QuantAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Highlight unusually large total-volume or estimated directional-delta events using percentile agreement across several history windows.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Source code excerpts define percentile thresholds and consensus; mode/direction contracts are explicitly described and configurable, sufficient for the principal event detector.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Calculate interpolated volume/absolute-delta percentiles independently over short/medium/long windows. Require any, majority or all windows to pass, combine volume/delta through selected AND/OR mode, then label direction using candle sign, delta sign or their agreement.

## Outputs and intended use

- Small/medium/big bubbles, diagnostic tooltips and tier alerts explain the event. Conflicting direction sources become Mixed. Missing delta can fall back to volume-only with an explicit tooltip; missing volume produces warning/no signals.

## Parameters and stated settings

- Default tier percentiles are75/90/97. Auto lower intervals are1second/subminute,1minute/intraday,5minutes/daily and60minutes/higher. Window lengths, consensus, detection/classification and colors/text are configurable.

## Failure modes and caveats

- Percentile events are relative to selected history, not proof of institutions or future reversal. Lower-timeframe delta is an estimate and fallback changes the detection contract.

## Missing information and implementation boundary

- Actual window defaults, library delta details and tier-overlap priority are not fully specified; the main percentile, consensus and mode rules are explicit and parameterized.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the input class; code behavior and cache coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
75th percentile (top 25%), a Medium cluster the 90th percentile (top 10%), and a Big cluster the 97th percentile (top 3%)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
"Any Window"               => hits >= 1
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
"Majority (2 of 3)"       => hits >= 2
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
"All Windows (strictest)" => hits >= 3
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
taLib.requestVolumeDelta(lowerTimeframe)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cjnk8au1_volume_bubbles_quantalgo](../tv_cjnk8au1_volume_bubbles_quantalgo.md)
- [tv_method_volume_delta](../../tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/CjNK8au1-Volume-Bubbles-QuantAlgo/

Publication ID: CjNK8au1. Source SHA-256: c10901dcb62c164693a942be6aaa0166d3e18cfe24ff901c373999015bd7b58c. Raw-description SHA-256: afe447e51de1d48c29da4aaa900d4199c913a23264f1d4bc670f8b8c89524d74.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
