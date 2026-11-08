---

id: tv_profile_5js51rsp

name: "Multitimeframe Fair Value Gap – FVG (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Track unmitigated fair-value gaps from a selected timeframe and add approximate volume pressure and a smoothed directional context. The indicator organizes candidate reaction zones rather than proving that institutions caused the price move."

registry_key: null

runner: null

evaluation: null

---

# Multitimeframe Fair Value Gap – FVG (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Track unmitigated fair-value gaps from a selected timeframe and add approximate volume pressure and a smoothed directional context. The indicator organizes candidate reaction zones rather than proving that institutions caused the price move.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Wick averaging and strength equations, exact Butterworth coefficients and the average-gap input definition are absent.

- Wick averaging and strength equations, exact Butterworth coefficients and the average-gap input definition are absent.

## How it works

- A gap is the wick separation between the first and third candles of a three-candle sequence. Selected-timeframe OHLCV supplies the pattern; wick size relative to a running average filters weak candidates.
- Extending boxes persist until midpoint touch or full closure, according to the mitigation setting. Close position within the high-low range apportions volume into estimated buying and selling effort.
- A two-pole Butterworth filter smooths average gap values into a trendline, used to distinguish aligned and countertrend zones.

## Outputs and intended use

- Gap boxes, proportional volume sub-bars and an active-gap table with formation timestamps support zone tracking.
- The author favors bullish gaps with rising trend and bearish gaps with falling trend, using volume overlays as discretionary confirmation.

## Parameters and stated settings

- FVG source timeframe, wick sensitivity, midpoint/full-fill mitigation, table placement and gap styling.
- Trend smoothing exposes passband ripple and cutoff frequency from 0 to 0.5.

## Failure modes and caveats

- Close-location volume is a proxy for actual aggressor flow. Institutional origin and predictive validity are unverified interpretations.
- Higher/lower timeframe sampling and unconfirmed source candles could change live behavior; confirmation policy is not disclosed.

## Missing information and implementation boundary

- Wick averaging and strength equations, exact Butterworth coefficients and the average-gap input definition are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV is sufficient as a raw data class, without asserting algorithm parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, readiness

```text
A Fair Value Gap (FVG) forms when there's a three-candle sequence
```

### E2: purpose, mechanism, parameters, outputs_and_use, readiness

```text
Only FVGs with wick sizes above a certain sensitivity threshold (user-controlled) are plotted.
```

### E3: purpose, mechanism, parameters, outputs_and_use, readiness

```text
[*][b]Cutoff Frequency (0–0.5):[/b] Sets how quickly the trendline reacts
```

### E4: purpose, mechanism, parameters, outputs_and_use, readiness

```text
[*]Buy Volume % ≈ effort from low to close
[*]Sell Volume % ≈ effort from high to close
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_5js51rsp_multitimeframe_fair_value_gap_fvg_zeiierman](../tv_5js51rsp_multitimeframe_fair_value_gap_fvg_zeiierman.md)
- [tv_method_fair_value_gap](../../../strategy_research/tv_method_fair_value_gap.md)
- [tv_method_liquidity_sweep](../../../strategy_research/tv_method_liquidity_sweep.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/5jS51RsP-Multitimeframe-Fair-Value-Gap-FVG-Zeiierman/

Publication ID: 5jS51RsP. Source SHA-256: b40ccef93cef291523817e367a6e8426307c67fb8e4e455a797bafc900430b0b. Raw-description SHA-256: 8e7ca9ca0070a8a61a8d6841bfb02f27951a61fcf9a2416a2e267b9ef9647c1e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
