---

id: tv_profile_bbidyx3r

name: "BERLIN Range Index | Bar color version"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Make choppiness-based trend/range classification respond faster by modifying it with recent changes in ATR dispersion."

registry_key: null

runner: null

evaluation: null

---

# BERLIN Range Index | Bar color version

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Make choppiness-based trend/range classification respond faster by modifying it with recent changes in ATR dispersion.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: The factor formula, choppiness calculation details, threshold mapping and real-time confirmation are missing.

- The factor formula, choppiness calculation details, threshold mapping and real-time confirmation are missing.

## How it works

- Calculate running standard deviation of ATR, compare it with its recent low and derive a factor that filters the choppiness index.

## Outputs and intended use

- Color bars yellow for a trending interpretation and transparent gray for a ranging interpretation. Use it as a regime filter rather than a directional trade signal.

## Parameters and stated settings

- The source names the ATR-dispersion filter but gives no lengths, recent-low window, thresholds or defaults.

## Failure modes and caveats

- The author acknowledges a tradeoff: greater trend responsiveness also increases range misclassification. A trending state alone gives no long/short direction.

## Missing information and implementation boundary

- The factor formula, choppiness calculation details, threshold mapping and real-time confirmation are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history. Availability refers to input class, not code validation or cached history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The ATR based filter is calculated by first calculating the running standard deviation of the ATR, and then looking at that in relation to its recent low to find a filtering factor to use on the choppiness index.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Yellow = Trending
Transparent gray = Ranging
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bbidyx3r_berlin_range_index_bar_color_version](../tv_bbidyx3r_berlin_range_index_bar_color_version.md)

## Source

https://www.tradingview.com/script/bBidYX3r-BERLIN-Range-Index-Bar-color-version/

Publication ID: bBidYX3r. Source SHA-256: c9fe5817beeb4a37f1ebf800aa0e67f79dc688b4addaceb02e7b60d496d0b995. Raw-description SHA-256: 55e89f7d11b0ef19669bc4c3bd0c8bfae2aa0492ea5368ecdfdf1d71b5f87592.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
