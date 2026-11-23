---

id: tv_profile_0x1dgqjw

name: "XABCD Harmonic Pattern Custom Range Interactive"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "This interactive harmonic-pattern tool automates parts of manually drawing XABCD structures and planning their potential reversal zones. A user selects initial chart points, the script snaps them to candle extremes, and a BC-ratio validity check determines whether a supported pattern is generated. The purpose is to reduce drawing effort and errors while connecting identification with visual risk/reward planning, rather than to scan every possible pattern or submit orders."

registry_key: null

runner: null

evaluation: null

---

# XABCD Harmonic Pattern Custom Range Interactive

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This interactive harmonic-pattern tool automates parts of manually drawing XABCD structures and planning their potential reversal zones. A user selects initial chart points, the script snaps them to candle extremes, and a BC-ratio validity check determines whether a supported pattern is generated. The purpose is to reduce drawing effort and errors while connecting identification with visual risk/reward planning, rather than to scan every possible pattern or submit orders.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Harmonic BC acceptance, projected reversal-zone ratios and stop equations are not defined.

- Harmonic BC acceptance, projected reversal-zone ratios and stop equations are not defined.

## How it works

- Accept points X through C interactively, attach them to candle highs/lows and check the BC ratio before generating a single supported harmonic pattern.
- Project D/PRZ and calculate planning outputs from A to D; execution-zone display can be shifted toward C.
- Use equal XAB and BCD time lengths for the projected full structure; D timing is only approximate.

## Outputs and intended use

- Review BC validity, projected PRZ, execution-zone graphics and profit/loss planning. The author recommends oscillator/divergence cross-checks for initial points.

## Parameters and stated settings

- Targets use 0.382 and 0.618 of A-to-D; default execution reference is D. Stop/target settings can be automatic or manual.
- Supported patterns include Alt Bat, Bat, Crab, Gartley, Butterfly, Deep Crab and Shark. Daily and lower timeframes are intended; automated alerts are unsupported in this release.

## Failure modes and caveats

- D projection ignores holidays/extended sessions; source notes time-array label bugs and drawing limitations. Analytical: discretionary point selection can materially change the pattern.

## Missing information and implementation boundary

- Exact BC acceptance ratios, stop equations, overlapping-pattern selection and confirmation rules are not reproduced; linked outside explanations are not substitute evidence.

## Data requirements

Required inputs: ohlcv, user-selected X A B C chart points.

Repository input-class support: unavailable or unresolved. OHLCV supports the price class, but the user’s interactive point selection is required and not supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
Take Profit is calculated based on ratio 0.382 and 0.618 of Point A to D.
```

### E2: parameters, readiness

```text
Execution zone can be offset to Point C, by default using Point D.
```

### E3: mechanism, readiness

```text
where XAB and BCD are one to one ratio.
```

### E4: parameters, readiness

```text
Automated alert is not supported for this release.
```

### E5: risks, readiness

```text
Point D time is for approximation only, not including holidays and extended session.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_0x1dgqjw_xabcd_harmonic_pattern_custom_range_interactive](../tv_0x1dgqjw_xabcd_harmonic_pattern_custom_range_interactive.md)
- [tv_method_harmonic_xabcd](../tv_method_harmonic_xabcd.md)
- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)

## Source

https://www.tradingview.com/script/0x1Dgqjw-XABCD-Harmonic-Pattern-Custom-Range-Interactive/

Publication ID: 0x1Dgqjw. Source SHA-256: 0b795534fd2b049f4146a32dff34a41c95971e6618485f7ad5596dce22700c3a. Raw-description SHA-256: dba9825ff8044e432ba0d0df9481ce83b5a804dec1690ede5c257d60bcec8cac.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
