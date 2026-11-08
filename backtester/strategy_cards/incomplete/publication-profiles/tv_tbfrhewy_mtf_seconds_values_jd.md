---

id: tv_profile_tbfrhewy

name: "MTF seconds values - JD"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "MTF Seconds Values provides an array-based workaround for constructing multi-timeframe inputs on seconds charts. It is indicator infrastructure with an explicit SMA example, not an independent market signal. The author discusses a historical platform limitation; the profile records that context without asserting the limitation still applies to current Pine versions."

registry_key: null

runner: null

evaluation: null

---

# MTF seconds values - JD

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: study. Review: independently reviewed.

## Idea and objective

MTF Seconds Values provides an array-based workaround for constructing multi-timeframe inputs on seconds charts. It is indicator infrastructure with an explicit SMA example, not an independent market signal. The author discusses a historical platform limitation; the profile records that context without asserting the limitation still applies to current Pine versions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Aggregation algorithm, source values, interval alignment, confirmation rules and array-update semantics are not disclosed.

- Aggregation algorithm, source values, interval alignment, confirmation rules and array-update semantics are not disclosed.

## How it works

- Collect multi-timeframe values in arrays and let a calling calculation operate on those values, demonstrated by an SMA.

## Outputs and intended use

- Embed the helper in another financial script requiring seconds-timeframe aggregation or derived calculations.

## Parameters and stated settings

- No supported seconds intervals, aggregation parameters, array size or defaults are supplied.

## Failure modes and caveats

- Analytical: custom array aggregation can misalign boundaries or developing values; historical workaround behavior may be obsolete in newer platform versions.

## Missing information and implementation boundary

- Aggregation algorithm, source values, interval alignment, confirmation rules and array-update semantics are not disclosed.

## Data requirements

Required inputs: seconds-resolution price series, caller timeframe configuration.

Repository input-class support: unavailable or unresolved. Needs seconds observations and specified aggregation intervals; ordinary higher-timeframe OHLCV cannot reconstruct them.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
helper code with arrays to get MTF on seconds timeframes.
```

### E2: purpose, outputs_and_use, readiness

```text
I plotted the sma from the MTF values on the chart
```

## Source

https://www.tradingview.com/script/tbfrhEWY-MTF-seconds-values-JD/

Publication ID: tbfrhEWY. Source SHA-256: 6ff89423e5c5e349428eb7849015543654dd6d5de9e221e3b97bcb7095efeb5e. Raw-description SHA-256: 008ce345ca003391a204f7ace39d071165dbdab5f86a2ffc0c633dc6814baa91.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
