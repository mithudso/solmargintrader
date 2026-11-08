---

id: tv_profile_hg385dby

name: "Ichimoku Kinkō hyō 目均衡表"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "This Ichimoku extension aims to make a complex multi-component framework easier to interpret while exposing extensive filtering and display options. It combines configurable Ichimoku relationships with volume and volatility context, then summarizes selected conditions through a help panel, colored bars and support/resistance drawings. The description calls its feature list options to implement, so it does not independently establish that every advertised option is present in executable code."

registry_key: null

runner: null

evaluation: null

---

# Ichimoku Kinkō hyō 目均衡表

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

This Ichimoku extension aims to make a complex multi-component framework easier to interpret while exposing extensive filtering and display options. It combines configurable Ichimoku relationships with volume and volatility context, then summarizes selected conditions through a help panel, colored bars and support/resistance drawings. The description calls its feature list options to implement, so it does not independently establish that every advertised option is present in executable code.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Adaptive lengths and filter aggregation into panel/alert states are absent.

- Adaptive lengths and filter aggregation into panel/alert states are absent.

## How it works

- Configure Ichimoku component lengths and alternative sources, optionally applying weighted smoothing and Heikin Ashi volume.
- Combine filters involving Tenkan/Kijun, Chikou versus price, cloud location, momentum, volume and volatility; summarize selected conditions into panel and bar states.

## Outputs and intended use

- Read the panel for selected condition status, inspect automatic support/resistance and use alerts for labels, level crosses or panel direction.

## Parameters and stated settings

- Volume-oscillator selector lists five families; relative-volume strength lists three families. Length, peak, EMA, volatility fast/slow lengths and display settings are configurable without stated numeric defaults.

## Failure modes and caveats

- Analytical: combining many adjustable filters increases interpretation and fitting complexity; planned-feature wording requires code verification.

## Missing information and implementation boundary

- Adaptive-length formulas, condition aggregation, alert confirmation, defaults and which listed options are implemented are not established.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: missing_information, readiness

```text
Here is the complete list of options to implement
```

### E2: parameters, readiness

```text
5 types of oscillators available
```

### E3: parameters, readiness

```text
3 Oscillators available
```

### E4: outputs_and_use, readiness

```text
Alerts available for: Labels Detection, Support/Resistance Line Cross, Panel Trend Status Direction.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [ichimoku_cloud](../../ichimoku_cloud.md)
- [tv_method_heikin_ashi](../../../strategy_research/tv_method_heikin_ashi.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/HG385dBY-Ichimoku-Kinkō-hyō-目均衡表/

Publication ID: HG385dBY. Source SHA-256: 780a8d65e04e096a06f9cdfe795bee57bab68160396874a8dfb81f21138709aa. Raw-description SHA-256: 9b5d57996bf01f68da91e6d4af31c94725ab86ef5b2b6bac9b1af9aa844e13c8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
