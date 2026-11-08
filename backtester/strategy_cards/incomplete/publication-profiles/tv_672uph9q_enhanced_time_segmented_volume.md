---

id: tv_profile_672uph9q

name: "Enhanced Time Segmented Volume"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Make Time Segmented Volume easier to interpret by translating its sign and relationship to an average into directional and possible-exhaustion annotations."

registry_key: null

runner: null

evaluation: null

---

# Enhanced Time Segmented Volume

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Make Time Segmented Volume easier to interpret by translating its sign and relationship to an average into directional and possible-exhaustion annotations.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The described computation retains a blocking specification gap: The exact TSV formula, averaging rule, bar-close confirmation and order-management rules are omitted.

- The exact TSV formula, averaging rule, bar-close confirmation and order-management rules are omitted.

## How it works

- The underlying TSV compares segments of price and volume. This version follows the correction attributed to vitelot and adds direction markers.
- Positive TSV above its average produces a green long-context box; positive TSV falling below its average produces a long-failure mark. Negative TSV below its average produces a red short-context box, while negative TSV rising above its average produces a short-failure mark.

## Outputs and intended use

- Read boxes as directional context and black crosses as possible loss of directional strength. When TSV and its average have opposite signs, the description says direction follows TSV's sign.

## Parameters and stated settings

- The text refers to a TSV histogram and moving average but gives neither lookback defaults nor average type.

## Failure modes and caveats

- The author warns that opposite-sign situations can mark a forming trend or low-volume consolidation. A zero-line oscillation can therefore generate misleading directional changes.

## Missing information and implementation boundary

- The exact TSV formula, averaging rule, bar-close confirmation and order-management rules are omitted.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described feature can use ordinary chart price/volume history; this is input-class availability, not verified code or market-history coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
If the histogram (TSV) is greater than zero and greater than the moving average, price should be moving long and there will be a green box below the chart.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
If TSV rises above the moving average while still being less than zero, the trend may be exhausting and has been coded to read Price Action Short - FAILURE with a black x below the chart.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
In these situations the chart will indicate long or short based on whether or not TSV is greater or less than zero.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_672uph9q_enhanced_time_segmented_volume](../tv_672uph9q_enhanced_time_segmented_volume.md)

## Source

https://www.tradingview.com/script/672uPH9q-Enhanced-Time-Segmented-Volume/

Publication ID: 672uPH9q. Source SHA-256: c9d2b5872a15575d2acbc9367af621ef77f099255f64d756879fb4bb9882cfd0. Raw-description SHA-256: dc1a42d7a0ef19fa3dfb36a82bfc07fa6025e61c76ed6342dc1758f5c9fb26ca.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
