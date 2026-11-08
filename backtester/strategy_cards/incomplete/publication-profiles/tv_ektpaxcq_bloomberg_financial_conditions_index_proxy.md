---

id: tv_profile_ektpaxcq

name: "Bloomberg Financial Conditions Index (Proxy)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This Financial Conditions Index is explicitly a simplified proxy rather than a reproduction of Bloomberg’s proprietary series. It combines market-price proxies into a standardized reading intended to distinguish tighter from easier financial conditions. Negative territory is interpreted as deterioration and positive territory as accommodation, with a color gradient reinforcing that convention. The author cites broader financial-conditions literature, but those references do not validate this particular construction. Its financial purpose is macro/regime context; no exact asset-allocation or entry rule is supplied."

registry_key: null

runner: null

evaluation: null

---

# Bloomberg Financial Conditions Index (Proxy)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This Financial Conditions Index is explicitly a simplified proxy rather than a reproduction of Bloomberg’s proprietary series. It combines market-price proxies into a standardized reading intended to distinguish tighter from easier financial conditions. Negative territory is interpreted as deterioration and positive territory as accommodation, with a color gradient reinforcing that convention. The author cites broader financial-conditions literature, but those references do not validate this particular construction. Its financial purpose is macro/regime context; no exact asset-allocation or entry rule is supplied.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Composite component equations, weights and signs are unspecified.

- Composite component equations, weights and signs are unspecified.

## How it works

- Use SPY for equities, TLT for bond conditions, LQD/HYG for credit, VIX for volatility and SHY relative to equities for liquidity.
- Transform component log returns into z-scores, apply approximate weights and aggregate a composite.

## Outputs and intended use

- Zero-centered colored index uses blue for neutral, green for accommodation and red for tightening.
- Read broad direction and unusual conditions rather than exact Bloomberg-equivalent values.

## Parameters and stated settings

- Source says six components but lists five conceptual categories; the category/symbol count is ambiguous.
- No numeric weights, normalization lookback or default settings are given.

## Failure modes and caveats

- TLT is a bond-price ETF, not a direct yield series, and LQD/HYG is not a pure credit-spread measure.
- The missing signs/weights make directional interpretation impossible to verify.
- Literature claims about other indexes do not establish predictive validity of this proxy.

## Missing information and implementation boundary

- Exact component definitions, weights/signs, lookbacks, alignment, missing-feed handling and calibration are absent.

## Data requirements

Required inputs: SPY TLT LQD HYG SHY price histories, VIX history.

Repository input-class support: unavailable or unresolved. Requires synchronized external ETF/index series; coverage and a reproducible weighting specification are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, risks

```text
only six key market components
```

### E2: mechanism, readiness

```text
Each component is transformed into a Z-score based on log returns
```

### E3: required_data

```text
using SPY as a proxy
```

### E4: required_data

```text
using TLT as a proxy
```

### E5: mechanism, required_data

```text
ratio between LQD and HYG
```

### E6: required_data

```text
using VIX directly
```

### E7: mechanism, required_data

```text
using SHY relative to equity prices
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ektpaxcq_bloomberg_financial_conditions_index_proxy](../tv_ektpaxcq_bloomberg_financial_conditions_index_proxy.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)

## Source

https://www.tradingview.com/script/EktpAXcq-Bloomberg-Financial-Conditions-Index-Proxy/

Publication ID: EktpAXcq. Source SHA-256: b3e72a0b38cefd2efa90fe625ce2230edfcdb52b95441dd2d5f7ad01f77206cf. Raw-description SHA-256: 3bad0492ba20379def487290dd37076c1713b41bda76ec24d73c5b7da41932ea.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
