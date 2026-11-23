---

id: tv_profile_puwmpoyc

name: "MACD with HTF Panels [theUltimator5]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "MACD with HTF Panels combines a conventional chart-timeframe MACD with small independent higher-timeframe views drawn to its side. It aims to keep momentum context visible without chart switching and demonstrates a reusable presentation method for other indicators. Each panel has its own timeframe calculation while sharing common indicator settings. The table remains broader than the visible panel count, so hiding a panel does not imply its numerical values disappear."

registry_key: null

runner: null

evaluation: null

---

# MACD with HTF Panels [theUltimator5]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

MACD with HTF Panels combines a conventional chart-timeframe MACD with small independent higher-timeframe views drawn to its side. It aims to keep momentum context visible without chart switching and demonstrates a reusable presentation method for other indicators. Each panel has its own timeframe calculation while sharing common indicator settings. The table remains broader than the visible panel count, so hiding a panel does not imply its numerical values disappear.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for ordinary chart-only EMA MACD line/signal/histogram with chosen lengths/source. HTF mapping/confirmation, panel scaling and exact publication averaging defaults remain caveats.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow chart-only ordinary MACD: declare source X and lengths F,S,G; MACD=EMA_F(X)−EMA_S(X), Signal=EMA_G(MACD), Histogram=MACD−Signal. This declares the ordinary EMA convention for the source-named standard MACD rather than claiming undocumented default lengths or selectable-average parity. Disable HTF panels.
- Calculate MACD line, signal and histogram with adjustable lengths and color the histogram by both sign and slope.
- Draw higher-timeframe mini-charts with optional candles; position horizontally in bars and scale candle heights using ATR.

## Outputs and intended use

- Compare momentum direction and change across the current chart and higher timeframes.
- A table shows all four higher-timeframe MACD, signal and histogram values regardless of how many panels are visible.

## Parameters and stated settings

- Up to five total timeframes are supported: current plus four higher-timeframe panels.
- Four panels default to a 2x2 layout; one to three stack vertically. Candles default off and table defaults bottom right.
- Caller supplies source and fast/slow/signal lengths under the stated EMA convention. Show HTF panels off selects the chart-only fallback; numeric MACD defaults are not given.

## Failure modes and caveats

- Unconfirmed higher-timeframe values may evolve; displayed agreement is not an entry rule.

## Missing information and implementation boundary

- MACD averaging types/default lengths, automatic timeframe mapping, ATR scale formula and higher-timeframe confirmation policy are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supplies the default input class; this does not establish source-code parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
up to 5 (current + 4)
```

### E2: mechanism

```text
four-way histogram coloring based on sign and slope
```

### E3: parameters

```text
When 4 panels (default) is selected, the stack is 2x2.
```

### E4: parameters

```text
These are disabled by default
```

### E5: parameters

```text
default position = bottom right
```

### E6: mechanism

```text
vertical scaling is based on ATR
```

### E7: mechanism, parameters, readiness

```text
The core of this indicator is a normal MACD.  Line, signal, and histogram, fully adjustable lengths
```

### E8: mechanism, parameters, readiness

```text
Disabling the HTF panels simply makes this indicator appear as a standard MACD
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_puwmpoyc_macd_with_htf_panels_theultimator5](../tv_puwmpoyc_macd_with_htf_panels_theultimator5.md)

## Source

https://www.tradingview.com/script/pUwmpOyc-MACD-with-HTF-Panels-theUltimator5/

Publication ID: pUwmpOyc. Source SHA-256: 63175b8dee28c48db91c990934dc5facf08feb9ff93917651b19ddc9e8980f20. Raw-description SHA-256: 70f7bc3a0d5059eb6fa8ce00c5d69b877a352590fe91c2252de86febc3893a5c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
