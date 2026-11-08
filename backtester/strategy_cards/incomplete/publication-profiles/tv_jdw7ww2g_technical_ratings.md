---

id: tv_profile_jdw7ww2g

name: "Technical Ratings"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Technical Ratings condenses a collection of moving-average and oscillator biases into a common signed rating and familiar buy/neutral/sell labels. It aims to provide a configurable technical consensus rather than an executable strategy. Users can alter group weights, choose chart or confirmed higher-timeframe calculations, and configure markers/alerts. The source explains how delayed values control repainting, but its timing prose is not perfectly consistent: it describes markers at the next opening while later allowing close-time markers for repainting signals. Those claims require code verification before historical signals are treated as causal."

registry_key: null

runner: null

evaluation: null

---

# Technical Ratings

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Technical Ratings condenses a collection of moving-average and oscillator biases into a common signed rating and familiar buy/neutral/sell labels. It aims to provide a configurable technical consensus rather than an executable strategy. Users can alter group weights, choose chart or confirmed higher-timeframe calculations, and configure markers/alerts. The source explains how delayed values control repainting, but its timing prose is not perfectly consistent: it describes markers at the next opening while later allowing close-time markers for repainting signals. Those claims require code verification before historical signals are treated as causal.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Individual oscillator vote predicates needed for the aggregate technical rating are absent.

- Individual oscillator vote predicates needed for the aggregate technical rating are absent.

## How it works

- Assign component biases +1/0/-1, average within MA/oscillator groups and combine with configurable weights.
- Ignore unavailable early-history components until sufficient data exists.
- Map rating magnitude to states; use cumulative advances/declines for color intensity and optional marker conditions.

## Outputs and intended use

- Columns, group labels, reference levels, configurable triangles and matching alerts provide technical-consensus context.

## Parameters and stated settings

- 26 components: 15 MA and 11 oscillator; default group weighting 50/50.
- SMA/EMA lengths 10,20,30,50,100,200; HMA 9; VWMA 20; Ichimoku plus named oscillators.
- Neutral band ±0.1, strong states beyond ±0.5, rating range ±1 and five color intensities.
- Timeframe, repaint option, marker levels/advances and alternating-direction restriction are configurable.

## Failure modes and caveats

- Correlated indicators do not provide independent votes.
- Early-history composition changes as components become available.
- Non-repainting and alert-timing claims are source descriptions, not verified implementation guarantees.

## Missing information and implementation boundary

- Individual oscillator defaults/vote predicates, exact marker logic and executable trade/risk rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. All named technical components use chart OHLCV; higher-timeframe values can be aggregated from compatible data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
26 different technical indicators.
```

### E2: parameters

```text
15 different components
```

### E3: parameters

```text
11 components
```

### E4: parameters

```text
10, 20, 30, 50, 100 and 200
```

### E5: parameters

```text
period 9
```

### E6: parameters

```text
period 20
```

### E7: parameters

```text
default is 50/50.
```

### E8: parameters

```text
0.5/-0.5 level
```

### E9: parameters

```text
0.1/-0.1 level
```

### E10: parameters

```text
between +1 and -1
```

### E11: parameters

```text
capped to 5
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_jdw7ww2g_technical_ratings](../tv_jdw7ww2g_technical_ratings.md)

## Source

https://www.tradingview.com/script/Jdw7wW2g-Technical-Ratings/

Publication ID: Jdw7wW2g. Source SHA-256: c8ec02ec7fcbce74539f0f7c62c59b55dda9d25f967effd48598dbfc91f83c72. Raw-description SHA-256: 3cbb5bc6c7acabdd3713a9de8a6418e00c0785beb6c67fce38014f211eff2a54.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
