---
id: tv_hocpm5uy_alculation_a_position_size_based_on_risk
name: "Сalculation a position size based on risk"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Show how a chosen risk budget and stop-loss distance can determine position size; it is a risk overlay rather than a market forecast."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Сalculation a position size based on risk

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** sizing-example. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Show how a chosen risk budget and stop-loss distance can determine position size; it is a risk overlay rather than a market forecast.

## How it works

- The entire saved description only says that this is an educational example of sizing from risk and stop loss. It does not disclose a formula, units or an executable rule.
- For an eventual implementation, cash risk, stop distance, instrument value and trade quantity must be dimensionally consistent. That is analytical context, not recovered source code.

## Documented rules and trade lifecycle

- Documented inputs in principle: risk and a stop loss.
- No buy/sell condition, stop placement rule, sizing formula or exit sequence is specified.

## Parameters and stated settings

- No risk percentage, cash budget, stop distance, size cap or defaults are stated.

## Failure modes and caveats

- A vanishing stop distance can imply an excessive position if quantity is not capped.
- Gaps, slippage and contract-value mistakes can make the realized loss exceed a nominal risk budget.

## Missing information and implementation boundary

- The source is insufficient to recover exact math. Do not insert a conventional sizing equation and call it the author's implementation.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: scope

> This is an example how to calculate position size based on risk and stop loss for educational purpose.

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> This is an example how to calculate position size based on risk and stop loss for educational purpose.

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/hoCPm5UY-Сalculation-a-position-size-based-on-risk/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
