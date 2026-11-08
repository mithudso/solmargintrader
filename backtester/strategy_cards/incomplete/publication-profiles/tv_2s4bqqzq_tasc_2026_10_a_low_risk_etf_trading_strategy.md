---

id: tv_profile_2s4bqqzq

name: "TASC 2026.10 A Low-Risk ETF-Trading Strategy"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "This ETF scanner expresses Katsanos’s short-term relative-strength method as screener columns and chart annotations. It seeks comparatively strong non-leveraged ETFs that have recovered from a recent oversold pullback without becoming excessively stretched. Benchmark correlation changes the market-risk gate, so a falling benchmark favors sufficiently negatively correlated candidates. The aim is improved downside behavior relative to buy-and-hold, an objective rather than demonstrated performance here. Although the publication describes explicit position conditions, its native implementation is an indicator for scanning a watchlist, not a broker-executed strategy."

registry_key: null

runner: null

evaluation: null

---

# TASC 2026.10 A Low-Risk ETF-Trading Strategy

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

This ETF scanner expresses Katsanos’s short-term relative-strength method as screener columns and chart annotations. It seeks comparatively strong non-leveraged ETFs that have recovered from a recent oversold pullback without becoming excessively stretched. Benchmark correlation changes the market-risk gate, so a falling benchmark favors sufficiently negatively correlated candidates. The aim is improved downside behavior relative to buy-and-hold, an objective rather than demonstrated performance here. Although the publication describes explicit position conditions, its native implementation is an indicator for scanning a watchlist, not a broker-executed strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the independently displayed RSMK series: explicit log-ratio change and four-period EMA define it for a chosen lookback and benchmark. Missing correlation/volume gates limit full screener reproduction, not RSMK.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For each selected ETF and benchmark, let R_t=ln(C_t/SEC2_t). Calculate RS1_t=R_t-R_(t-RSBARS), then RSMK_t=100×EMA(RS1,4). RSBARS is the chosen relative-strength lookback; the source baseline is 35 days.
- Require relative-strength, recent oversold recovery, overbought protection, short-term trend, benchmark-regime/correlation and volume conditions together.
- End the displayed position when relative strength deteriorates with strong benchmark correlation, a holding-time limit is reached, or the profit target is reached.

## Outputs and intended use

- Screener columns identify entry/exit events and maintain entry-price and position-performance readings while active.
- Chart triangles, an entry line, profit/loss fill and exit marks accompany a separate RSMK/average pane.

## Parameters and stated settings

- Source baseline: RSMK lookback 35, smoothing EMA 4, strength average 50, entry above +3 at a four-day high and below 25.
- RSI length 10 must have visited below 35 within 20 days and risen for three days; EMA 5 exceeds the SMA 15 value from five days earlier.
- SPY six-day change threshold is -6%; volume uses a five-day average. Exit examples are RSMK crossing below -3, 30 days or 25% profit.
- Lengths, thresholds, correlation, volume floor, rebalance period and benchmark are inputs; the published screener version fixes SPY.

## Failure modes and caveats

- ETF selection and benchmark choice can introduce selection bias; the linked demonstration universe is not point-in-time evidence.
- The author excludes leveraged ETFs from intended applicability. Indicator performance columns do not establish achievable fills or net returns.

## Missing information and implementation boundary

- Numeric minimum-correlation and volume thresholds, exact correlation window, fill convention and daily/bar alignment are not disclosed here.
- No portfolio weights, concurrent-position constraints or transaction-cost model are specified.

## Data requirements

Required inputs: caller-selected ETF OHLCV histories, benchmark price history, fixed caller-selected ETF watchlist.

Repository input-class support: unavailable or unresolved. The selected ETF and benchmark histories require external aligned multi-symbol inputs. The described fixed watchlist does not require a dynamic historical-membership feed; historical selection bias remains a research caveat.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
RSMK = EMA(RS1, 4) * 100
```

### E2: parameters, mechanism

```text
The 35-day RSMK is above its 50-day moving average.
```

### E3: parameters

```text
The RSMK is greater than +3.
```

### E4: parameters

```text
The RSMK is at a new four-day high.
```

### E5: parameters

```text
The 10-length RSI was below 35 at least once over the last 20 days.
```

### E6: parameters

```text
The RSI is rising over the last three days.
```

### E7: parameters

```text
The RSMK is less than 25.
```

### E8: parameters

```text
The 5-length EMA is above the 15-day SMA from five days ago.
```

### E9: parameters

```text
The six-day rate of change in the SPY price is greater than -6%
```

### E10: parameters

```text
The five-day SMA of volume is above the minimum threshold.
```

### E11: parameters

```text
the RSMK crosses below -3.
```

### E12: parameters

```text
The position has remained open for 30 days (six weeks).
```

### E13: parameters

```text
The position reaches a profit of 25%.
```

### E14: risks

```text
non-leveraged
```

### E15: purpose

```text
indicator designed for scanning
```

### E16: mechanism, readiness

```text
RS1 = ln(C / SEC2) – ln(C / SEC2)[RSBARS]
RSMK = EMA(RS1, 4) * 100
```

### E17: required_data

```text
apply it to a selected watchlist.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_2s4bqqzq_tasc_2026_10_a_low_risk_etf_trading_strategy](../tv_2s4bqqzq_tasc_2026_10_a_low_risk_etf_trading_strategy.md)
- [xs_momentum](../../xs_momentum.md)

## Source

https://www.tradingview.com/script/2S4BqQzQ-TASC-2026-10-A-Low-Risk-ETF-Trading-Strategy/

Publication ID: 2S4BqQzQ. Source SHA-256: d2562fd801aec6c8aec9b71f8b42ba0d93c1c0adaf61942951f594ddf4fdf3f6. Raw-description SHA-256: dc5f6fea989f120f59c0bf6f79f90ea198f84ac0e69f300dccf02187aa10e885.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
