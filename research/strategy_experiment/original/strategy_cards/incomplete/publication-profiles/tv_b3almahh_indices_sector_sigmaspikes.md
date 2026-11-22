---

id: tv_profile_b3almahh

name: "Indices Sector SigmaSpikes"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Indices Sector SigmaSpikes compares sector moves in units of their own recent return variability. The aim is to make cross-market daily changes meaningful: the same point or percentage move can be ordinary in one market and unusual in another. The screener helps locate sectors with outsized positive or negative movement, without specifying that those moves should be faded or followed."

registry_key: null

runner: null

evaluation: null

---

# Indices Sector SigmaSpikes

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Indices Sector SigmaSpikes compares sector moves in units of their own recent return variability. The aim is to make cross-market daily changes meaningful: the same point or percentage move can be ordinary in one market and unusual in another. The screener helps locate sectors with outsized positive or negative movement, without specifying that those moves should be faded or followed.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Daily percentage return divided by prior-window return standard deviation defines the sector spike output with configurable lookback and threshold.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Divide today’s return by the standard deviation of prior daily returns, excluding today from the volatility baseline.
- Scan selected symbols and compare the resulting sigma ratio with a user-chosen significance threshold.

## Outputs and intended use

- Use the cross-sector view to identify unusual directional activity and prioritize further investigation.

## Parameters and stated settings

- The illustrated baseline is 20 prior daily returns and is adjustable. Threshold examples are 1, 2 or 3 standard deviations.
- Up to 13 symbols can be scanned; Bursa indices are defaults. Custom timeframe currently supports Daily and Weekly.

## Failure modes and caveats

- The source warns multi-symbol requests can slow the screener; analytical: heavy tails and volatility regime shifts mean sigma units are not calibrated event probabilities.

## Missing information and implementation boundary

- Exact return convention, missing-data handling, weekly-baseline interpretation and trade decisions are not specified.

## Data requirements

Required inputs: price histories for up to thirteen caller-selected sector/index symbols.

Repository input-class support: available. Ordinary historical OHLCV/price inputs for caller-selected symbols are a supported data class. Exact selected-symbol cache coverage, synchronization and adjustments remain unverified; no dynamic point-in-time universe is required by the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
past 20days daily's return (today not included)
```

### E2: parameters, readiness

```text
threshold (1,2,3,etc)
```

### E3: parameters, readiness

```text
Scan up to 13 symbols at a time
```

### E4: parameters, readiness

```text
Custom Timeframe currently accept only Daily and Weekly.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_b3almahh_indices_sector_sigmaspikes](../../../strategy_research/tv_b3almahh_indices_sector_sigmaspikes.md)

## Source

https://www.tradingview.com/script/B3aLMAHh-Indices-Sector-SigmaSpikes/

Publication ID: B3aLMAHh. Source SHA-256: 645a21698fc0037aa1a250c3b508fa5684745e9b36c1c4a65a71af605faca80e. Raw-description SHA-256: 40e03f4352ce8f1874ff527c48ab9053cc7cd693bdd2c151f6a2424954484b7a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
