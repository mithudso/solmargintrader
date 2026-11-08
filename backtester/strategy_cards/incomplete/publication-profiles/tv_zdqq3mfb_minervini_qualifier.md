---

id: tv_profile_zdqq3mfb

name: "Minervini Qualifier"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Minervini Qualifier colors a moving-average envelope according to a stock trend-template qualification and exposes individual condition states. It aims to make progress toward the referenced stock-selection conditions visible over time. A separate relative-strength display compares the stock with a chosen index. The author explicitly says that relative strength may differ from the book method, so the indicator should not be represented as an exact implementation of the published template."

registry_key: null

runner: null

evaluation: null

---

# Minervini Qualifier

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Minervini Qualifier colors a moving-average envelope according to a stock trend-template qualification and exposes individual condition states. It aims to make progress toward the referenced stock-selection conditions visible over time. A separate relative-strength display compares the stock with a chosen index. The author explicitly says that relative strength may differ from the book method, so the indicator should not be represented as an exact implementation of the published template.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for daily close versus SMA20 direction only. Full qualification/fill, envelope geometry, SMA200 duration and reference-index strength remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow daily direction output: M_t=mean(Close_t…Close_(t−19)). Display red direction when current Close_t<M_t and blue when Close_t>M_t; exact equality is not defined. This does not reproduce envelope width, full Minervini qualification, long-term SMA trend duration or index-relative strength.
- Use an SMA envelope and condition-dependent fill: transparent for failed qualification, yellow for a remaining close/SMA condition, and directional colors for progressively longer long-term-average uptrends.
- Plot each qualification condition as a separate true/false-colored line and compute a reference-index strength measure.

## Outputs and intended use

- Read condition history and the strength value above/below its neutral reference.
- The author restricts useful interpretation to daily charts.

## Parameters and stated settings

- Envelope uses SMA20; yellow references close below SMA50. Green requires SMA200 rising at least one month, blue at least five months.
- Relative strength compares with 100; individual-condition and strength displays default on.
- Daily closes and fixed SMA20 define this independent direction output. Require sufficient history; equality and incomplete-history display need implementation choices.

## Failure modes and caveats

- Book references do not disclose the implemented criteria or establish exact template parity.

## Missing information and implementation boundary

- Complete qualification rules, trend-duration test, envelope width and relative-strength formula/lookback are absent.

## Data requirements

Required inputs: ohlcv, reference index prices.

Repository input-class support: unavailable or unresolved. Selected external series or user pivots are required beyond chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
SMA 20day envelope curve
```

### E2: parameters

```text
close is still below SMA50
```

### E3: parameters

```text
SMA200 trending for at least one month up
```

### E4: parameters

```text
SMA200 trending up for at least 5 months
```

### E5: parameters

```text
above 100
```

### E6: parameters

```text
default:on
```

### E7: risks

```text
might be different to what Mark Minervini is using.
```

### E8: mechanism, parameters, readiness

```text
current close price is below the SMA20 and when blue, current close price is above the SMA20.
```

### E9: mechanism, parameters, readiness

```text
It gives only useful information on daily timeframe
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_zdqq3mfb_minervini_qualifier](../tv_zdqq3mfb_minervini_qualifier.md)
- [xs_momentum](../../xs_momentum.md)

## Source

https://www.tradingview.com/script/zDQQ3mFb-Minervini-Qualifier/

Publication ID: zDQQ3mFb. Source SHA-256: a0858672c754da50538cdb0e75b6d9e854c84da24e63378e3e9005c2f1f64244. Raw-description SHA-256: 09cc76832ede5b85a3a791d5cf826c116b5076105905a02ec358627e4bde343e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
