---

id: tv_profile_xascppnw

name: "Nick Rypock Trailing Reverse (NRTR) [everget]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "NRTR is a percentage-based trailing reversal reference that follows extremes reached within the current trend. The distinguishing feature is excluding extremes from the preceding trend, so a new trend’s reference starts from its own evolving range. The source compares it with Chandelier Exit conceptually but explicitly removes ATR, making the selected percentage rather than measured volatility determine distance."

registry_key: null

runner: null

evaluation: null

---

# Nick Rypock Trailing Reverse (NRTR) [everget]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

NRTR is a percentage-based trailing reversal reference that follows extremes reached within the current trend. The distinguishing feature is excluding extremes from the preceding trend, so a new trend’s reference starts from its own evolving range. The source compares it with Chandelier Exit conceptually but explicitly removes ATR, making the selected percentage rather than measured volatility determine distance.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Reversal condition and trend/extreme reset timing are not sufficiently defined.

- Reversal condition and trend/extreme reset timing are not sufficiently defined.

## How it works

- Maintain the current trend’s peak or trough and place the reference a constant percentage below an uptrend peak or above a downtrend trough.
- Exclude previous-trend extremes from the dynamic channel calculation.

## Outputs and intended use

- Inspect the trailing reverse line as a trend-following/reversal reference; exact trade actions are not specified in the prose.

## Parameters and stated settings

- Percentage distance is fundamental but no default, allowed range or input-price definition is supplied.

## Failure modes and caveats

- Analytical: a fixed percentage can be too tight in volatile regimes or too wide in quiet ones, and gap crossings can exceed the implied reference.

## Missing information and implementation boundary

- Initial trend state, reversal/cross condition, extreme reset timing and stop execution rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
doesn't involve ATR component and uses a percentage instead.
```

### E2: mechanism, readiness

```text
exclude the extremes related to the previous trend.
```

### E3: outputs_and_use, readiness

```text
below the maximum peak for the current uptrend, above the minimum bottom for the current downtrend
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_xascppnw_nick_rypock_trailing_reverse_nrtr_everget](../tv_xascppnw_nick_rypock_trailing_reverse_nrtr_everget.md)

## Source

https://www.tradingview.com/script/XAscppNW-Nick-Rypock-Trailing-Reverse-NRTR-everget/

Publication ID: XAscppNW. Source SHA-256: 020b78585a95baca45219606b9d73fb602152d30e01497ba5ef0e53742385e73. Raw-description SHA-256: 68be4f1cf4b47efbede4d638e513acf629587c1f93ed6b3d50d7011ea60c44cf.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
