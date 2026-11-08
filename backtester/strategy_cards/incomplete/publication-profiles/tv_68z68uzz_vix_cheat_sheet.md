---

id: tv_profile_68z68uzz

name: "VIX Cheat Sheet"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "VIX Cheat Sheet studies how the charted asset behaved around volatility-proxy extremes. It pairs either VIX or a local VixFix measure with the asset, allowing users outside large-cap US equities to avoid automatically treating VIX as the correct risk proxy. The emphasis is historical event analysis: correlation, subsequent returns and contextual boxes help the user inspect past relationships rather than receive a fixed trade command."

registry_key: null

runner: null

evaluation: null

---

# VIX Cheat Sheet

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

VIX Cheat Sheet studies how the charted asset behaved around volatility-proxy extremes. It pairs either VIX or a local VixFix measure with the asset, allowing users outside large-cap US equities to avoid automatically treating VIX as the correct risk proxy. The emphasis is historical event analysis: correlation, subsequent returns and contextual boxes help the user inspect past relationships rather than receive a fixed trade command.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** VIX-mode event-return study is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Measure correlation to the chosen volatility proxy and identify proxy closes above its upper Bollinger band.
- Collect the asset’s subsequent close-to-close and multi-session returns around those events, then preserve results in label tooltips.
- Color event bars by the selected proxy and optionally draw extended high-VIX episodes.
- On each VIX session close above its caller-configured upper Bollinger band, record asset close C0. After h=1,5,10 sessions compute100*(C[h]/C0-1) and summarize matured observations by horizon. Counting each qualifying session including overlaps is an explicit study policy, not asserted Pine parity. VixFix is excluded.

## Outputs and intended use

- Read current proxy changes and event-return tooltips; the live event label is replaced with a historical tooltip after its observation horizon.
- Usable scope: VIX-mode event-return study. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Return summaries include next close, 5 sessions and 10 sessions; an example episode uses VIX above 40 for at least ten consecutive sessions.
- VIX versus VixFix and box plotting are selectable; Bollinger lengths, multipliers and VixFix settings are not given.

## Failure modes and caveats

- The author notes VIX often fails as a proxy beyond large-cap US equities; analytical: post-event returns require future bars and cannot be known at event onset.

## Missing information and implementation boundary

- Correlation window, event-overlap handling, exact VixFix formula and executable trade decisions are absent.

## Data requirements

Required inputs: ohlcv, VIX historical prices or VixFix calculation.

Repository input-class support: unavailable or unresolved. VIX mode needs an external VIX series; VixFix mode may be OHLCV-derived but its construction is not provided.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
the average 5-session gain/loss following the same occurrence in addition to the average 10-session gain/loss
```

### E2: parameters, readiness

```text
$VIX measured above $40 for at least ten consecutive sessions.
```

### E3: risks, readiness

```text
using $VIX as a risk proxy or volatility metric often fails beyond large-cap U.S equities.
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
Measured are: $VIX correlation to an asset's price fluctuations, the average close-to-close gain/loss subsequent a $VIX/VixFix close above the upper Bollinger Band, the average 5-session gain/loss following the same occurrence in addition to the average 10-session gain/loss, all close-to-close, 5 session, and 10-session gains/losses are stored as tooltips for labels on the chart. The current close-to-close percentage gain/loss for $VIX and VixFix are displayed on the chart.
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
Measured are: $VIX correlation to an asset's price fluctuations, the average close-to-close gain/loss subsequent a $VIX/VixFix close above the upper Bollinger Band, the average 5-session gain/loss following the same occurrence in addition to the average 10-session gain/loss, all close-to-close, 5 session, and 10-session gains/losses are stored as tooltips for labels on the chart. The current close-to-close percentage gain/loss for $VIX and VixFix are displayed on the chart.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_68z68uzz_vix_cheat_sheet](../tv_68z68uzz_vix_cheat_sheet.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)

## Source

https://www.tradingview.com/script/68Z68uZZ-VIX-Cheat-Sheet/

Publication ID: 68Z68uZZ. Source SHA-256: 5c75835cffd6f5b832a45305f9719cfc6765a2e389c7fff1d62122e548038c26. Raw-description SHA-256: 593fc7575d8059d6d6764bc8407d44194cea109ef592cb0ab2931c36e56a95c1.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
