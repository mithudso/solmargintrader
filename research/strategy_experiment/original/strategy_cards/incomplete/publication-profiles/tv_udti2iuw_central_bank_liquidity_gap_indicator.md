---

id: tv_profile_udti2iuw

name: "Central Bank Liquidity Gap Indicator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Central Bank Liquidity Gap compares growth in a global liquidity aggregate with growth in the S&P 500. The author interprets positive divergence as potential long-term accumulation context, particularly when liquidity growth materially exceeds market growth. It is expressly aimed at daily/weekly investment analysis rather than precise bottoms or day trading. Claims that liquidity must eventually flow into stocks or that historical buy zones are effective are hypotheses, not validated findings in this source."

registry_key: null

runner: null

evaluation: null

---

# Central Bank Liquidity Gap Indicator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Central Bank Liquidity Gap compares growth in a global liquidity aggregate with growth in the S&P 500. The author interprets positive divergence as potential long-term accumulation context, particularly when liquidity growth materially exceeds market growth. It is expressly aimed at daily/weekly investment analysis rather than precise bottoms or day trading. Claims that liquidity must eventually flow into stocks or that historical buy zones are effective are hypotheses, not validated findings in this source.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core definitions remain missing.

- Growth window, aggregate/blend formula and lead/correlation calculations are undefined.
- Point-in-time macro-release and FX input contracts are absent.

## How it works

- Convert selected countries' M2 balances to USD and aggregate them with a reduced China contribution.
- Optionally blend Fed net liquidity, defined as balance sheet minus Treasury General Account minus reverse repos.
- Subtract S&P 500 growth percentage from liquidity growth percentage and display sign plus a buy-zone threshold.

## Outputs and intended use

- Read the divergence histogram, background zone and table of component weights, correlation, lead statistic and signal.
- Use as macro context; the text mentions leveraged ETFs but provides no leverage-specific risk sizing or exit rules.

## Parameters and stated settings

- China M2 is discounted by 50%. Divergence above +5% marks the buy zone.
- Countries and Fed-liquidity blend are selectable; growth and correlation window defaults are absent.

## Failure modes and caveats

- Publication lags, revisions and FX conversions can create lookahead bias.
- Correlation or a positive lead statistic does not prove causal predictive power.

## Missing information and implementation boundary

- Exact feed symbols, growth horizon, blend weights, release alignment and correlation/lead estimation are unspecified.

## Data requirements

Required inputs: country M2 releases, FX rates, Fed balance sheet, TGA, reverse repo, S&P 500 prices.

Repository input-class support: unavailable or unresolved. The selected external series and their point-in-time history are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
Divergence = Liquidity Growth % − S&P 500 Growth %
```

### E2: parameters

```text
China's M2 weight is reduced by 50%
```

### E3: mechanism, required_data

```text
Net Liquidity = Fed Balance Sheet − Treasury General Account − Reverse Repo
```

### E4: parameters

```text
divergence exceeds +5%
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_udti2iuw_central_bank_liquidity_gap_indicator](../../../strategy_research/tv_udti2iuw_central_bank_liquidity_gap_indicator.md)

## Source

https://www.tradingview.com/script/udTI2IUw-Central-Bank-Liquidity-Gap-Indicator/

Publication ID: udTI2IUw. Source SHA-256: 029d3c4d5663a78cc48b3ca1b18d969f5065d8f8660ee33c424468335cbfe7ea. Raw-description SHA-256: 4ce2e526efd2d579360666daf020855ea4f7207f77420fa1ba50d5ea679fc63f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
