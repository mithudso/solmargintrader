---

id: tv_profile_mbxxbs1f

name: "RedK_Directional Index / K xDMI"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "RedK xDMI modifies directional-movement analysis to display trend strength with a signed orientation and less cascaded smoothing. It uses weighted averages and optional volume weighting, aiming to make bullish/bearish control easier to read. The source incorrectly describes conventional ADX as restricted below zero; that historical comparison is not adopted as a technical fact."

registry_key: null

runner: null

evaluation: null

---

# RedK_Directional Index / K xDMI

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

RedK xDMI modifies directional-movement analysis to display trend strength with a signed orientation and less cascaded smoothing. It uses weighted averages and optional volume weighting, aiming to make bullish/bearish control easier to read. The source incorrectly describes conventional ADX as restricted below zero; that historical comparison is not adopted as a technical fact.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Signed ADX equation, directional-movement tie/true-range handling, volume normalization, step rounding and full defaults are unspecified.

- Signed ADX equation, directional-movement tie/true-range handling, volume normalization, step rounding and full defaults are unspecified.

## How it works

- Smooth directional-index components with WMA, derive an unrestricted signed strength measure and optionally weight DMI by volume.
- Offer stepped strength display, an adjustable strong-trend level and area/histogram visualization.

## Outputs and intended use

- The author suggests a rising DI cross plus strong-trend threshold for control, while using signed strength for trend quality and broader confirmation.

## Parameters and stated settings

- Defaults are length 7 and smoothing 3; volume weighting is off by default. Step examples are 5/10 and strong-trend suggestions 20–30.

## Failure modes and caveats

- Analytical: less smoothing increases response and noise; signed strength is not conventional ADX and threshold transfer needs testing. Source’s below-zero description is erroneous.

## Missing information and implementation boundary

- Signed ADX equation, directional-movement tie/true-range handling, volume normalization, step rounding and full defaults are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
length = 7, smoothing = 3
```

### E2: parameters, readiness

```text
not set by default.
```

### E3: parameters, readiness

```text
say 5 or 10
```

### E4: parameters, readiness

```text
between 20 to 30
```

### E5: risks, readiness

```text
restricted the ADX to oscillate below zero
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_mbxxbs1f_redk_directional_index_k_xdmi](../tv_mbxxbs1f_redk_directional_index_k_xdmi.md)

## Source

https://www.tradingview.com/script/mbXXbS1f-RedK-Directional-Index-K-xDMI/

Publication ID: mbXXbS1f. Source SHA-256: 3709f19a624f6f0121de58072e60e460861bd0db03773cfef582a97a565d58b0. Raw-description SHA-256: 256d6fb9fcdb1d4dc41ea06782edcd083b55561e8f89e077c377109676f4f781.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
