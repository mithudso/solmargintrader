---

id: tv_profile_lxxlkr1w

name: "Recession Warning Traffic Light"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Recession Warning Traffic Light summarizes several macro warning proxies and compares their states with historical recession markers. It combines metal ratios, equity-growth context, yield-curve inversion, output contraction, money supply and leading indicators. Calling the aggregate a recession probability does not make it calibrated: the source gives narrative motivations without a mathematical probability model or point-in-time validation."

registry_key: null

runner: null

evaluation: null

---

# Recession Warning Traffic Light

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Recession Warning Traffic Light summarizes several macro warning proxies and compares their states with historical recession markers. It combines metal ratios, equity-growth context, yield-curve inversion, output contraction, money supply and leading indicators. Calling the aggregate a recession probability does not make it calibrated: the source gives narrative motivations without a mathematical probability model or point-in-time validation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Three-month versus ten-year inversion warning is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Evaluate six component warning states from macro/market series and color each green or red; compare combined warnings with an external recession indicator.
- Components include gold/rhodium relative prices, SPX growth curves, short/long Treasury yields, GDP, M2 and leading-economic factors.
- On supplied synchronized yields flag inversion iff3-month Treasury yield>10-year yield. Equality does not trigger under this strict rule. This is a warning subindicator;composite recession probability,other metrics,revisions and historical calibration remain unqualified.

## Outputs and intended use

- Use the traffic-light panel to investigate broad recession-risk context rather than precise timing or a trade instruction.
- Usable scope: Three-month versus ten-year inversion warning. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Daily chart of SPX/DJI/NDQ is requested. Yield comparison uses three-month and ten-year Treasuries; no full source tickers/threshold defaults are given.

## Failure modes and caveats

- Analytical: revised/delayed macro data and ex-post recession dating can produce lookahead bias; assertions of reliable warning are not verified.

## Missing information and implementation boundary

- Component thresholds, growth-curve equation, aggregation/probability mapping, release lags, revisions and dataset identities are missing.

## Data requirements

Required inputs: gold and rhodium prices, equity index history, Treasury yields, GDP and M2 releases, leading indicators, historical recession markers.

Repository input-class support: unavailable or unresolved. External macro histories with release-time/revision controls are essential; chart OHLCV cannot provide them.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
uses 6 different metrics
```

### E2: parameters, readiness

```text
chart should be on 1d and set to SPX , DJI ,or NDQ
```

### E3: parameters, readiness

```text
3m & 10y treasuries
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
Yield curve: This indicator compares the 3m & 10y treasuries and detects yield curve inversions. Interest rates are controlled by the Federal Reserve and by the purchasers in the Federal Treasury auction markets, which together create the treasury yield curve. This inversion is the most reliable recession indicator. These happen during a flight to quality.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_lxxlkr1w_recession_warning_traffic_light](../tv_lxxlkr1w_recession_warning_traffic_light.md)

## Source

https://www.tradingview.com/script/lxXLkR1w-Recession-Warning-Traffic-Light/

Publication ID: lxXLkR1w. Source SHA-256: 12d8e06f1cd4f56ac8d836f8bed149828a87f96d885ed3cdb647da349001ac95. Raw-description SHA-256: 4fa27dc126b3545cf33dedee8096064ae1913cd082fc7cd8a5dfbedcd5417005.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
