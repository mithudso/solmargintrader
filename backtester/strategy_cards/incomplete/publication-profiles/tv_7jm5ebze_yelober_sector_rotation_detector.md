---

id: tv_profile_7jm5ebze

name: "Yelober - Sector Rotation Detector"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Yelober Sector Rotation Detector monitors a fixed sector-ETF panel to highlight relative daily leadership, defensive conditions and unusual volume. It interprets a large spread between the strongest and weakest sectors as rotation and offers associated stock ideas. The risk-off label is more specific: defensive staples and utilities must be positive while technology is negative. This is a market-context dashboard with qualitative suggestions, not evidence that money actually flowed between funds or a complete long/short strategy. Its daily focus matters because configurable intraday or weekly sampling may change how the advertised daily comparisons behave."

registry_key: null

runner: null

evaluation: null

---

# Yelober - Sector Rotation Detector

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Yelober Sector Rotation Detector monitors a fixed sector-ETF panel to highlight relative daily leadership, defensive conditions and unusual volume. It interprets a large spread between the strongest and weakest sectors as rotation and offers associated stock ideas. The risk-off label is more specific: defensive staples and utilities must be positive while technology is negative. This is a market-context dashboard with qualitative suggestions, not evidence that money actually flowed between funds or a complete long/short strategy. Its daily focus matters because configurable intraday or weekly sampling may change how the advertised daily comparisons behave.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Daily sector diagnostics are reproducible from the named ETF set, daily close comparisons, RSI period, relative-volume lookback and explicit rotation/risk-off thresholds. Stock recommendations and alternate-timeframe alignment remain outside that usable scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Request sector ETF and SPY data; compute percentage change, RSI and volume relative to its lookback average.
- Compare strongest/weakest sector performance and test the defensive-sector/technology sign pattern.
- Describe trend by current versus previous close and attach stock suggestions to sector strength/weakness.

## Outputs and intended use

- Table shows performance, RSI, volume ratio and directional icons.
- Summary flags rotation, risk-off and strong volume, then suggests stocks for further long/short consideration.

## Parameters and stated settings

- Universe: XLE, XLF, XLK, XLP, XLU, XLY and SPY.
- Rotation gap exceeds 2%; RSI uses 70/30 extremes and abnormal-volume threshold is 1.5x.
- Lookback defaults to 20 and RSI to 14; timeframes include 60/240-minute, daily and weekly. A refresh counter requests manual refresh.

## Failure modes and caveats

- Relative returns alone do not measure capital flows.
- Stock suggestions are not a point-in-time stock-selection rule and may not track the sector proxy.
- Partial-session volume versus a full-period average can distort volume ratios.

## Missing information and implementation boundary

- Exact daily change base under alternate timeframes, stock-mapping rules, update behavior and portfolio risk rules are not disclosed.

## Data requirements

Required inputs: sector ETF and SPY OHLCV histories, stock recommendation mapping.

Repository input-class support: unavailable or unresolved. Requires aligned histories for the specified external ETF universe; the recommendation mapping and actual feed coverage are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, required_data

```text
Energy (XLE)
- Financial (XLF)
```

### E2: parameters, required_data

```text
Technology (XLK)
- Consumer Staples (XLP)
- Utilities (XLU)
- Consumer Discretionary (XLY)
- S&P 500 (SPY)
```

### E3: parameters, mechanism, readiness

```text
performance gap (>2%)
```

### E4: parameters

```text
Values above 70
```

### E5: parameters

```text
Values below 30
```

### E6: parameters

```text
Values above 1.5x
```

### E7: parameters

```text
(default: 20)
```

### E8: parameters

```text
(default: 14)
```

### E9: parameters

```text
60 or 240 minutes
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_7jm5ebze_yelober_sector_rotation_detector](../../../strategy_research/tv_7jm5ebze_yelober_sector_rotation_detector.md)
- [xs_momentum](../../../strategy_research/xs_momentum.md)

## Source

https://www.tradingview.com/script/7jm5ebze-Yelober-Sector-Rotation-Detector/

Publication ID: 7jm5ebze. Source SHA-256: b6771f3df4f52029042c6ab152ddeb4d460d08a8ff6f038ab980553dd1ed2cfa. Raw-description SHA-256: 255178bb516b0e959af1ad95aa87ca16cd187b7bf8f8fa0c812be434fc4ca0e4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
