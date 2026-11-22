---

id: tv_profile_ulnivzea

name: "SMU STDEV Candles"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "SMU STDEV Candles changes the presentation of standard-deviation information from a line into candle-like objects, allowing comparison with ordinary price candles. The intent is to expose changes within the indicator’s candle representation rather than introduce a fully described volatility forecast. The source speculates about historical structural shifts and algorithmic effects without disclosing evidence that identifies their cause."

registry_key: null

runner: null

evaluation: null

---

# SMU STDEV Candles

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

SMU STDEV Candles changes the presentation of standard-deviation information from a line into candle-like objects, allowing comparison with ordinary price candles. The intent is to expose changes within the indicator’s candle representation rather than introduce a fully described volatility forecast. The source speculates about historical structural shifts and algorithmic effects without disclosing evidence that identifies their cause.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The deviation estimator and candle OHLC transformation are absent.

- The deviation estimator and candle OHLC transformation are absent.

## How it works

- Construct a standard-deviation series in candle format; the method for deriving its open/high/low/close is not explained.

## Outputs and intended use

- Compare the indicator candles with price candles at different timeframes to inspect changes in volatility behavior.

## Parameters and stated settings

- No lookback, source series, candle-construction setting or defaults are supplied.

## Failure modes and caveats

- Analytical: candle styling can imply intraperiod detail that is not defined; claims about algorithms suppressing volatility are not established by the description.

## Missing information and implementation boundary

- Standard-deviation estimator, sampling window, OHLC transformation, normalization and trade interpretation are unknown.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
creates a STDEV in a candle format
```

### E2: outputs_and_use, readiness

```text
compare it with the actual price candle.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ulnivzea_smu_stdev_candles](../tv_ulnivzea_smu_stdev_candles.md)

## Source

https://www.tradingview.com/script/ULnIvZeA-SMU-STDEV-Candles/

Publication ID: ULnIvZeA. Source SHA-256: d197f1ee454685ba433db1935b23e165eaa1e35261d37505d42666c142b3611f. Raw-description SHA-256: 282fc4f1ac7db4f8592255b5cd233bd71b99a86ceb97835898147c17df7947e3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
