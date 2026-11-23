---

id: tv_profile_hbmp20tn

name: "Volume Profile with a few polylines"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Volume Profile with a few polylines accumulates volume at selected candle prices using maps, then draws the distribution efficiently with connected segments. It aims to display a broad historical profile without requiring one drawing object per price row. Rounding or fixed price steps merge nearby observations, while optional volume-times-price changes the unit from raw volume to a currency-weighted measure. The profile is a candle-source approximation rather than a transaction-level volume-at-price reconstruction. Its prominent levels support discretionary activity-zone analysis, not a disclosed entry system."

registry_key: null

runner: null

evaluation: null

---

# Volume Profile with a few polylines

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Profile with a few polylines accumulates volume at selected candle prices using maps, then draws the distribution efficiently with connected segments. It aims to display a broad historical profile without requiring one drawing object per price row. Rounding or fixed price steps merge nearby observations, while optional volume-times-price changes the unit from raw volume to a currency-weighted measure. The profile is a candle-source approximation rather than a transaction-level volume-at-price reconstruction. Its prominent levels support discretionary activity-zone analysis, not a disclosed entry system.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The default unrounded map path explicitly sums volume at each selected source price and highlights maximum rows; optional price multiplication is also defined. Contradictory optional rounding prose does not block the default profile.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Use chosen price as a map key and add volume when the same key recurs.
- Optionally round/step price keys and multiply volume by price.
- At the last bar, draw horizontal profile segments through polylines and separately highlight the largest volume rows.

## Outputs and intended use

- Profile width is proportional to largest accumulated volume; top three rows receive distinct lines/colors.

## Parameters and stated settings

- Default source is close; amount of bars, rounding/step, offset, maximum width, colors and currency weighting are inputs.
- Curved/closed polylines default off. Source describes 10,000 points per polyline, three points per row and 100 polylines maximum; offset is limited to 500 future bars.

## Failure modes and caveats

- The prose’s Round sign explanation conflicts with its numeric examples; exact rounding semantics need code.
- All candle volume at one chosen price distorts actual traded-price distribution.

## Missing information and implementation boundary

- Rounding implementation, retention, volume-unit conversion and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Selected candle price and volume use OHLCV; no lower-timeframe feed is disclosed.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
default close
```

### E2: parameters, outputs_and_use

```text
The 3 highest volume values
```

### E3: parameters

```text
maximum 10000 points
```

### E4: parameters

```text
each price/volume line takes 3 points.
```

### E5: parameters

```text
maximum of 100 polylines
```

### E6: parameters

```text
maximum 500 bar to the right
```

### E7: parameters

```text
They are default disabled
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hbmp20tn_volume_profile_with_a_few_polylines](../tv_hbmp20tn_volume_profile_with_a_few_polylines.md)

## Source

https://www.tradingview.com/script/HBMP20tn-Volume-Profile-with-a-few-polylines/

Publication ID: HBMP20tn. Source SHA-256: 8fc581c3fca41da534d1846352adee21d6fd539ae1c91554a678358da3a4f70c. Raw-description SHA-256: 220eb506703b1310e16bc1996d4cf6bae2697ed4f9bd445fcbcb46b5909b5b30.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
