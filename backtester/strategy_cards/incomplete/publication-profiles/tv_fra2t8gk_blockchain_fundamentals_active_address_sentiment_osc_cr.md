---

id: tv_profile_fra2t8gk

name: "Blockchain Fundamentals - Active Address Sentiment Osc. [CR]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Active Address Sentiment Oscillator compares Bitcoin’s price growth with growth in daily active blockchain addresses. It frames unusually strong price growth relative to network-activity bands as overheating and unusually weak growth as undervaluation. This is a macro-relative-activity interpretation rather than an intrinsic value calculation or a precise timing signal, and the author repeatedly restricts use to daily charts."

registry_key: null

runner: null

evaluation: null

---

# Blockchain Fundamentals - Active Address Sentiment Osc. [CR]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Active Address Sentiment Oscillator compares Bitcoin’s price growth with growth in daily active blockchain addresses. It frames unusually strong price growth relative to network-activity bands as overheating and unusually weak growth as undervaluation. This is a macro-relative-activity interpretation rather than an intrinsic value calculation or a precise timing signal, and the author repeatedly restricts use to daily charts.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Address feed, standard-deviation window/multipliers, white-highlight condition and missing/revised data treatment are unspecified.

- Address feed, standard-deviation window/multipliers, white-highlight condition and missing/revised data treatment are unspecified.

## How it works

- Calculate rolling percentage changes of price and daily active addresses, construct standard-deviation bands around address growth and average the bands.
- Compare the price-change line with smoothed address-based bands; optional white background seeks narrower extreme zones.

## Outputs and intended use

- Inspect macro overvaluation/undervaluation context and possible local/cyclical extremes rather than minute-chart buy/sell signals.

## Parameters and stated settings

- Both percentage-change horizon and band averaging are 28 days. Daily timeframe is mandatory; further thresholds/defaults are not disclosed.

## Failure modes and caveats

- Analytical: active-address counts can reflect address reuse, batching or structural network changes rather than economic adoption; band deviations do not guarantee a pullback.

## Missing information and implementation boundary

- Address feed, standard-deviation window/multipliers, white-highlight condition and missing/revised data treatment are unspecified.

## Data requirements

Required inputs: BTC daily prices, daily active Bitcoin-address history.

Repository input-class support: unavailable or unresolved. Requires external on-chain address data; ordinary price OHLCV does not supply network activity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
percent change over the past 28 days for each metric
```

### E2: parameters, readiness

```text
averaging the bands over a 28 day period.
```

### E3: parameters, readiness

```text
ONLY GIVE YOU THE CORRECT RESULTS ON THE DAILY TIMEFRAME
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_fra2t8gk_blockchain_fundamentals_active_address_sentiment_osc_cr](../tv_fra2t8gk_blockchain_fundamentals_active_address_sentiment_osc_cr.md)

## Source

https://www.tradingview.com/script/fRA2t8gk-Blockchain-Fundamentals-Active-Address-Sentiment-Osc-CR/

Publication ID: fRA2t8gk. Source SHA-256: 52640be0ac768f0b2909c72c5120a3e7d712d8bdb4e6705f29cd162863b29e2e. Raw-description SHA-256: 2e6200eb2e36f6202d8cf16270899b347b7005d86a24e57e824284fffb6f2534.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
