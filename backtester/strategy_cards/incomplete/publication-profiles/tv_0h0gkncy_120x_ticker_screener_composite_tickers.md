---

id: tv_profile_0h0gkncy

name: "120x ticker screener (composite tickers)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This screener demonstrates packing multiple market prices into a synthetic composite ticker and decoding them after a shared data request. Its financial purpose is to display a wider set of ticker metrics under the request constraints discussed in the publication. The central contribution is a fragile encoding technique, not an independent trading strategy or a current guarantee about platform limits. Manually chosen decimal spacing preserves distinguishable price components only while the selected symbols remain within anticipated ranges."

registry_key: null

runner: null

evaluation: null

---

# 120x ticker screener (composite tickers)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This screener demonstrates packing multiple market prices into a synthetic composite ticker and decoding them after a shared data request. Its financial purpose is to display a wider set of ticker metrics under the request constraints discussed in the publication. The central contribution is a fragile encoding technique, not an independent trading strategy or a current guarantee about platform limits. Manually chosen decimal spacing preserves distinguishable price components only while the selected symbols remain within anticipated ranges.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The worked scaling, rounding and subtraction example defines reproducible composite-close encoding/decoding with caller-selected symbols and scales; RMA/RSI extras are explicitly unreliable.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Scale component ticker prices by selected powers of ten, add them into a composite expression, request that expression and split it through rounding and subtraction.
- Use reconstructed close histories to calculate percentage change, SMA, RMA and RSI for a sorted table; debugging can compare components against ordinary ticker prices.

## Outputs and intended use

- Inspect multi-ticker metrics and use unsorted debug output to check price decoding; tickers and their scaling/rounding settings must be edited in source.

## Parameters and stated settings

- The method composes three tickers per composite; higher timeframe defaults to Daily. Metric length, table sorting, exchange labels and colors are configurable.
- The author identifies roughly 15–16 significant digits as a practical encoding limit and recommends one or two zero separators.

## Failure modes and caveats

- Mixed market hours can break composites; large price changes require rescaling. The author reports RMA/RSI differences on lower chart timeframes.
- Analytical: composite highs/lows and finite precision cannot be assumed to preserve independent asset observations. Historical platform-limit wording is not a current API fact.

## Missing information and implementation boundary

- The full symbol universe, exact safe scaling bounds, missing-feed behavior and resolution-correct RMA/RSI reconstruction are unresolved.

## Data requirements

Required inputs: selected multi-symbol price histories, composite ticker calculation support.

Repository input-class support: unavailable or unresolved. Requires a selected external symbol set and platform composite data behavior; no point-in-time universe is established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
compose_3_()[/i] will make a composite ticker of 3 tickers
```

### E2: parameters, readiness

```text
HTF[/i]: Higher TimeFrame (default Daily)
```

### E3: parameters, risks, readiness

```text
the limit lays around 15-16 digits.
```

### E4: parameters, readiness

```text
Make sure the numbers are close to each other as possible, with 1 zero (or 2) in between:
```

### E5: risks, readiness

```text
1h TF and lower is quite different.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_round_number_levels](../tv_method_round_number_levels.md)

## Source

https://www.tradingview.com/script/0h0gKNcy-120x-ticker-screener-composite-tickers/

Publication ID: 0h0gKNcy. Source SHA-256: e965291514b7f73dc3b14a8cd7b87252fea3a926c65e6d24eda5c0f6a6725e42. Raw-description SHA-256: eb8d89d5fe0ce450742bd30097013710e069f54ed5ba875ba8404c5d2d737f18.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
