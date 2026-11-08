---

id: tv_profile_eis1vcdx

name: "'Golden ratio' Cubes - 'GoRaC'"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Project golden-ratio-based cube geometry from a selected price interval to inspect potential support and resistance regions."

registry_key: null

runner: null

evaluation: null

---

# 'Golden ratio' Cubes - 'GoRaC'

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Project golden-ratio-based cube geometry from a selected price interval to inspect potential support and resistance regions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact cube construction, golden-ratio subdivision, higher-timeframe handling and signal rules are omitted.

- Exact cube construction, golden-ratio subdivision, higher-timeframe handling and signal rules are omitted.

## How it works

- Use either high/low or candle-body extremes as the two reference prices, optionally from a higher timeframe. Draw cube-style proportions from their difference and extend selected lines.

## Outputs and intended use

- Reverse or mirror the geometry and extend lines left or right for visual reference. The source does not establish a tested reaction probability or entry rule.

## Parameters and stated settings

- Bars-back selects a prior period; zero uses the developing period. The example uses weekly data on a daily chart. High/low versus max(open,close)/min(open,close) is selectable.

## Failure modes and caveats

- The author explicitly warns that a developing higher-timeframe period can change and repaint. Its example also equates one weekly bar with seven daily bars, which should not be assumed for all sessions.

## Missing information and implementation boundary

- Exact cube construction, golden-ratio subdivision, higher-timeframe handling and signal rules are omitted.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary price history supports the disclosed input class; source code and historical data parity have not been validated.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The 2 points can be 'high/low' or 'max(open/close)/min(open/close)'
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
if you set '0', and it is Friday, the week isn't finished yet!
Everything still can change (= repaint)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_eis1vcdx_golden_ratio_cubes_gorac](../tv_eis1vcdx_golden_ratio_cubes_gorac.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/eIs1vcDX-Golden-ratio-Cubes-GoRaC/

Publication ID: eIs1vcDX. Source SHA-256: 240109bf1fd9aa995a49f67589d8c00aa119b7791446be1c20aa94c5fcc29002. Raw-description SHA-256: 6e838d1448fd1be1a5889e61c77aa6ac41f144ae1cf20fad59b9ec8d7c8afb30.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
