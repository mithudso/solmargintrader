---

id: tv_profile_5qth3kyd

name: "Multi-Layer Volume Profile [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Multi-Layer Volume Profile compares where candle volume accumulates across nested historical windows. It aims to show accepted price regions, sparse-volume areas and overlapping points of control, giving discretionary support/resistance analysis a volume dimension. The distinct windows help a trader see whether a dominant level persists across longer and shorter contexts. The author suggests using profile shape for position-building or stop/entry consideration and signed volume as breakout confirmation. Those are qualitative applications; no exact trigger or trade-management system follows from them."

registry_key: null

runner: null

evaluation: null

---

# Multi-Layer Volume Profile [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Multi-Layer Volume Profile compares where candle volume accumulates across nested historical windows. It aims to show accepted price regions, sparse-volume areas and overlapping points of control, giving discretionary support/resistance analysis a volume dimension. The distinct windows help a trader see whether a dominant level persists across longer and shorter contexts. The author suggests using profile shape for position-building or stop/entry consideration and signed volume as breakout confirmation. Those are qualitative applications; no exact trigger or trade-management system follows from them.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Equal-range bins, close-location volume assignment, maximum-bin POC and signed candle-volume sums define the principal profile. Boundary/tie conventions remain implementation caveats.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Find each window’s high/low, divide that range into equal price bins, and allocate each candle’s volume to the bin containing its close.
- Aggregate bin totals, identify the largest-volume bin as POC, and sum overall volume.
- Calculate delta by signing candle volume positive for bullish closes and negative for bearish closes.

## Outputs and intended use

- Profile polylines, thick blue POC lines, high/low references and total/delta labels expose volume structure.
- Overlapping POCs suggest confluence; sparse regions and signed delta provide discretionary context.

## Parameters and stated settings

- Up to four profiles use full, half, quarter and one-eighth of selected length.
- Bin count is configurable, trading granularity against smoothness; numeric defaults are absent.

## Failure modes and caveats

- Assigning an entire candle’s volume to its close is an approximation of traded volume by price.
- Candle-signed delta is not actual aggressor-side order flow, and a high-volume node does not guarantee support.

## Missing information and implementation boundary

- Rounding of nested windows, doji treatment, bin-edge rules, update timing and actionable entry/exit conditions are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The author explicitly derives bins and delta from candle highs/lows/closes and volumes; no tick-level feed is required by this description.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Profile 1: Full period
   - Profile 2: Half-length
   - Profile 3: Quarter-length
   - Profile 4: One-eighth-length
```

### E2: mechanism, readiness

```text
Assigns volume into bins based on candle close location
```

### E3: mechanism

```text
positive for bullish, negative for bearish closes
```

### E4: outputs_and_use

```text
maximum traded volume
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_5qth3kyd_multi_layer_volume_profile_bigbeluga](../tv_5qth3kyd_multi_layer_volume_profile_bigbeluga.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/5QtH3KYD-Multi-Layer-Volume-Profile-BigBeluga/

Publication ID: 5QtH3KYD. Source SHA-256: e9cd74655f180e464b9273754195cade82820d66f9b7d28ebc723920dc0feb52. Raw-description SHA-256: 26f73b486f2044ab0f47ea29e0a982a9e00dde2499ab10bbf881e8071eee06bc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
