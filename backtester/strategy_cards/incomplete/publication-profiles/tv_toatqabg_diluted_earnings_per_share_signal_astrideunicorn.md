---

id: tv_profile_toatqabg

name: "Diluted Earnings Per Share Signal [AstrideUnicorn]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Diluted Earnings Per Share Signal compares reported diluted EPS with the analyst EPS estimate to identify earnings surprises after accounting for potential share dilution. It aims to flag cases where an apparently positive ordinary EPS surprise may conceal weaker diluted economics. The indicator uses a symmetric threshold around zero rather than simply checking whether reported EPS exceeds consensus. It supplies a fundamental event signal, not a complete post-earnings trading system. Point-in-time estimates and reporting consistency are essential to interpreting its historical marks."

registry_key: null

runner: null

evaluation: null

---

# Diluted Earnings Per Share Signal [AstrideUnicorn]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Diluted Earnings Per Share Signal compares reported diluted EPS with the analyst EPS estimate to identify earnings surprises after accounting for potential share dilution. It aims to flag cases where an apparently positive ordinary EPS surprise may conceal weaker diluted economics. The indicator uses a symmetric threshold around zero rather than simply checking whether reported EPS exceeds consensus. It supplies a fundamental event signal, not a complete post-earnings trading system. Point-in-time estimates and reporting consistency are essential to interpreting its historical marks.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Source includes substantive parameterized computations/code that can be reproduced.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- At each earnings date, calculate (diluted EPS minus EPS estimate) divided by EPS estimate.
- Compare the percentage result with positive/negative threshold and draw bullish/bearish triangles.

## Outputs and intended use

- Green up and red down triangles identify sufficiently large diluted surprises.

## Parameters and stated settings

- Earnings Surprise Threshold defaults to 20%; BUY requires above threshold and SELL below its negative.

## Failure modes and caveats

- Zero or negative estimates can create undefined or economically inverted percentage surprises.
- The opening bearish wording is vague, but settings explicitly specify the negative threshold.
- After-release marks do not establish pre-release availability or achievable announcement fills.

## Missing information and implementation boundary

- Provider matching, release timestamps, zero-estimate behavior and revision policy are not specified.

## Data requirements

Required inputs: point-in-time diluted EPS releases, matching pre-release analyst EPS estimates.

Repository input-class support: unavailable or unresolved. Fundamental release and consensus data are external to OHLCV and their point-in-time availability is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
Diluted Earnings Surprise =  (Diluted EPS - EPS Estimate)/ EPS Estimate.
```

### E2: mechanism, readiness

```text
lower than minus Earnings Surprise Threshold
```

### E3: parameters

```text
default value for Earnings Surprise Threshold is 20%.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_toatqabg_diluted_earnings_per_share_signal_astrideunicorn](../tv_toatqabg_diluted_earnings_per_share_signal_astrideunicorn.md)

## Source

https://www.tradingview.com/script/ToaTQAbG-Diluted-Earnings-Per-Share-Signal-AstrideUnicorn/

Publication ID: ToaTQAbG. Source SHA-256: d72184ac043f09f669164dc21e062034c94e3695a7697377684589ef005a73db. Raw-description SHA-256: 9110ca02ca9b12461934f7e1b14d2550d14ac62d828cf48e8d8d1b5ac21fb6cb.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
