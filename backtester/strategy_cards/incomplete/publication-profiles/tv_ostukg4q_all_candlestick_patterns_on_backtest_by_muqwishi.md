---

id: tv_profile_ostukg4q

name: "All Candlestick Patterns on Backtest [By MUQWISHI]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "All Candlestick Patterns on Backtest compares historical return percentages for multiple candle-pattern methods in a table. It is intended as a starting point for research, with configurable execution assumptions and risk/reward geometry. Its native study output and educational framing should not be mistaken for independently reproduced strategy performance; the source supplies no actual measured results in prose."

registry_key: null

runner: null

evaluation: null

---

# All Candlestick Patterns on Backtest [By MUQWISHI]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

All Candlestick Patterns on Backtest compares historical return percentages for multiple candle-pattern methods in a table. It is intended as a starting point for research, with configurable execution assumptions and risk/reward geometry. Its native study output and educational framing should not be mistaken for independently reproduced strategy performance; the source supplies no actual measured results in prose.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Pattern definitions and simulated trade sizing/fill sequencing are unspecified.

- Pattern definitions and simulated trade sizing/fill sequencing are unspecified.

## How it works

- Recognize patterns based on the referenced public pattern indicator, simulate entry at confirmed close or on a subsequent break of the final pattern candle, and cancel stale pending entries when configured.
- Set stop distance from pattern high-low range and target distance from the chosen risk/reward multiple; report pattern-specific historical returns.

## Outputs and intended use

- Compare table results and inspect chart patterns while treating the analysis as exploratory rather than a primary trade decision.

## Parameters and stated settings

- Inputs include start date, initial equity, leverage, entry mode, pending-entry expiry and risk/reward.
- Illustration: range 10 and entry 100 imply stop 90, target 110 at 1:1 or 130 at 1:3; these are examples rather than defaults.

## Failure modes and caveats

- Analytical: many pattern comparisons invite selection bias; missing cost and same-bar fill assumptions can materially change results.

## Missing information and implementation boundary

- Exact pattern definitions, position sizing, fees/slippage, stop/target ordering, overlapping-trade handling and default settings are not disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; source-code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
range 10 points, and entry price is 100.
```

### E2: parameters, readiness

```text
1:1~risk:reward would the stoploss at 90 and takeprofit at 110.
```

### E3: parameters, readiness

```text
1:3~risk:reward would the stoploss at 90 and takeprofit at 130.
```

### E4: mechanism, readiness

```text
as soon as the candle confirmed.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_candlestick_patterns](../tv_method_candlestick_patterns.md)
- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)
- [tv_ostukg4q_all_candlestick_patterns_on_backtest_by_muqwishi](../tv_ostukg4q_all_candlestick_patterns_on_backtest_by_muqwishi.md)

## Source

https://www.tradingview.com/script/OsTuKG4q-All-Candlestick-Patterns-on-Backtest-By-MUQWISHI/

Publication ID: OsTuKG4q. Source SHA-256: cf537ceeed2345f5f20dbd13169ebdc82cfe1b5fa03361f9d30135d8e6a3fb15. Raw-description SHA-256: 816636352758756430e847304b09c97f53e5a62ea0df0addbe1e2d1d712d3aaf.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
