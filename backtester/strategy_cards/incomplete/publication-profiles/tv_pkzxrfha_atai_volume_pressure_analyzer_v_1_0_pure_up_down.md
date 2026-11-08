---

id: tv_profile_pkzxrfha

name: "ATAI Volume Pressure Analyzer V 1.0 — Pure Up/Down"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Summarize lower-timeframe estimated buying/selling pressure over a shared window, its older/newer halves and several optional geometric/oscillator views."

registry_key: null

runner: null

evaluation: null

---

# ATAI Volume Pressure Analyzer V 1.0 — Pure Up/Down

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Summarize lower-timeframe estimated buying/selling pressure over a shared window, its older/newer halves and several optional geometric/oscillator views.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The basic totals are explicit, but central advanced-wing/spike/vote outputs and their library/input contracts are incompletely specified.

- Up/down split and odd-window handling
- Wing/angle formulas and ATR settings
- Spike/vote thresholds and defaults

## How it works

- Request up/down volume from a named library, take absolute side magnitudes, compute total/delta and their simple averages. Compare half-window sums; add ATR-normalized wings, oriented midpoint angles, oscillator-voted spikes and top buy/sell volume peaks.

## Outputs and intended use

- A last-bar HUD shows side volumes, deltas, segment comparisons and advanced modules. Highest buy-volume high is labeled resistance and highest sell-volume low support as discretionary reference zones.

## Parameters and stated settings

- Global window defaults55. Auto intervals are1second for second charts,1minute intraday,5minutes daily,60minutes otherwise. Near-flat angle defaults about3degrees; alpha=360-beta with180degree imbalance references. Seven oscillator types contribute votes.

## Failure modes and caveats

- Up/down volume is estimated candle-direction participation, not guaranteed aggressor flow. Odd window splitting, fine-data history limits and custom wing geometry can alter comparisons; a pressure imbalance need not imply reversal.

## Missing information and implementation boundary

- Library split/equal-price behavior, half rounding, wing endpoints/ATR period, spike thresholds and oscillator-vote settings are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary price history supports the stated input class; missing algorithms are specification gaps rather than missing raw data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Default: 55.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
TF_buy = |Up volume|
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
TF_sell = |Down volume|
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
TF_delta = TF_buy − TF_sell
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
default ~3°
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
α = 360° − β
```

### E7: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
RSI, Stoch, %R, CCI, MFI, DeMarker, StochRSI
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_pkzxrfha_atai_volume_pressure_analyzer_v_1_0_pure_up_down](../tv_pkzxrfha_atai_volume_pressure_analyzer_v_1_0_pure_up_down.md)

## Source

https://www.tradingview.com/script/PkzxrfhA-ATAI-Volume-Pressure-Analyzer-V-1-0-Pure-Up-Down/

Publication ID: PkzxrfhA. Source SHA-256: 175e022a233e103a57b0587a24c0b2f26147dab94ce15ea174106b4ebcb0b5f2. Raw-description SHA-256: ab7d7b8b98dc2451cc12b0f64c74da15929b63bcf197e33bb3d036b0d6c19127.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
