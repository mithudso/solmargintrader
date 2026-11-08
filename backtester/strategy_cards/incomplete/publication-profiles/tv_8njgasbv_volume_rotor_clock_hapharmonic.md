---

id: tv_profile_8njgasbv

name: "Volume Rotor Clock [hapharmonic]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Volume Rotor Clock combines an ornamental clock with a financial volume dashboard and multi-symbol scanner. The current chart’s volume dominance appears on clock-hand tips, while scanned assets occupy bullish or bearish halves according to their attributed buy/sell totals. An additional watchlist highlights bullish assets whose volume persistently exceeds its moving average. Its financial purpose is therefore genuine despite the elaborate clock artwork. The author interprets sustained high-volume dominance as accumulation, but this should remain a hypothesis because the buy/sell assignment method is undisclosed."

registry_key: null

runner: null

evaluation: null

---

# Volume Rotor Clock [hapharmonic]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Rotor Clock combines an ornamental clock with a financial volume dashboard and multi-symbol scanner. The current chart’s volume dominance appears on clock-hand tips, while scanned assets occupy bullish or bearish halves according to their attributed buy/sell totals. An additional watchlist highlights bullish assets whose volume persistently exceeds its moving average. Its financial purpose is therefore genuine despite the elaborate clock artwork. The author interprets sustained high-volume dominance as accumulation, but this should remain a hypothesis because the buy/sell assignment method is undisclosed.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The buy/sell volume attribution underlying dominance is missing.

- The buy/sell volume attribution underlying dominance is missing.

## How it works

- Sum attributed buy/sell volume over the configured recent-bar window and compute each side’s share.
- Place assets by dominant side and scale their circles by dominance.
- Promote bullish assets when barssince(not(volume>SMA(volume,X))) is at least Y.

## Outputs and intended use

- Clock-tip colors/percentages and tooltips show current-symbol volume totals/shares.
- Scanner circles and the filtered upper watchlist focus attention on potentially sustained buying activity.

## Parameters and stated settings

- Up to 20 symbol slots and 20 visual templates.
- Lookback 0 uses the current bar; 7 includes eight bars, explicitly including the current bar.
- Volume MA Length X, Consecutive Days Above MA Y, watchlist rows, timezone and clock geometry/colors are configurable.

## Failure modes and caveats

- Attributed volume dominance does not prove institutional accumulation.
- The filter labels consecutive days but its formula counts bars, making timeframe interpretation important.
- Developing-bar volume can change eligibility.

## Missing information and implementation boundary

- Buy/sell volume formula, symbol defaults, X/Y defaults, timeframe handling and trade rules are absent.

## Data requirements

Required inputs: selected multi-symbol ohlcv histories.

Repository input-class support: unavailable or unresolved. Requires aligned histories for user-selected assets; the selected universe and its data coverage are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
ta.barssince(not(volume > ta.sma(volume, X))) >= Y
```

### E2: parameters

```text
up to 20 slots
```

### E3: parameters

```text
20 unique templates
```

### E4: parameters

```text
`0`: Calculates using the [b]current bar only[/b].
```

### E5: parameters

```text
`7`: Calculates the sum of volume over the [b]last 8 bars[/b]
```

### E6: parameters, risks

```text
Consecutive Days Above MA
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_8njgasbv_volume_rotor_clock_hapharmonic](../tv_8njgasbv_volume_rotor_clock_hapharmonic.md)
- [tv_method_volume_delta](../../tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/8nJGAsbV-Volume-Rotor-Clock-hapharmonic/

Publication ID: 8nJGAsbV. Source SHA-256: c5715032d5b2a9ce63ebae55752da0731a9318280a45d54387e342fa2934ad21. Raw-description SHA-256: f336448320cde21eaa74e241233aa8a590d19a25a7596ff1d8dd0717a876bc6a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
