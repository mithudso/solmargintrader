---

id: tv_profile_l2lxyays

name: "Zig-Zag Volume Profile (Bull vs. Bear) [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Compare estimated bullish and bearish volume-at-price distributions within individual zigzag-defined market legs."

registry_key: null

runner: null

evaluation: null

---

# Zig-Zag Volume Profile (Bull vs. Bear) [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare estimated bullish and bearish volume-at-price distributions within individual zigzag-defined market legs.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Volume-sign classification, distribution within candles, value-area percentage, pivot confirmation and delta calculation are absent.

- Volume-sign classification, distribution within candles, value-area percentage, pivot confirmation and delta calculation are absent.

## How it works

- Anchor profiles to configurable zigzag swings, separate bull/bear volume, calculate combined and separate POCs/value areas, and display per-price-block and aggregate leg delta. Polylines enable fine profile rendering.

## Outputs and intended use

- View the profiles together or on opposing sides and inspect key levels for the current or completed trend. The interpretation is participation context rather than a complete trade rule.

## Parameters and stated settings

- The script supports up to 9999 profile rows per zigzag trend. Swing configuration, profile shape, side placement, colors and transparency are customizable.

## Failure modes and caveats

- Fine rows increase display granularity without proving the underlying volume allocation is precise. Developing zigzags can reassign leg boundaries; buy/sell labels are not verified aggressor-volume observations.

## Missing information and implementation boundary

- Volume-sign classification, distribution within candles, value-area percentage, pivot confirmation and delta calculation are absent.

## Data requirements

Required inputs: price/volume observations, bull/bear volume allocation inputs.

Repository input-class support: unavailable or unresolved. The required volume classification/allocation is undisclosed; a precise delta profile cannot be established from ordinary OHLCV alone.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Up to 9999 profile rows per zigzag trend
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Profiles are generated for each trend identified by the zigzag indicator.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Aggregate volume delta for the identified trend is displayed over the profile!
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_l2lxyays_zig_zag_volume_profile_bull_vs_bear_kioseff_trading](../tv_l2lxyays_zig_zag_volume_profile_bull_vs_bear_kioseff_trading.md)
- [tv_method_volume_delta](../../tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/L2LxYayS-Zig-Zag-Volume-Profile-Bull-vs-Bear-Kioseff-Trading/

Publication ID: L2LxYayS. Source SHA-256: 56952c2fc66e8847c32ac8eb325c3fc941bff06199944eeaefb43ca3c84ce554. Raw-description SHA-256: 2e47e261bfd8be6a0e5764a99e9441b536e47a15252b4b0ab4cb258afc35f2da.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
