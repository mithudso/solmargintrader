---

id: tv_profile_zlyn2rht

name: "Zigzag Cloud"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Zigzag Cloud measures price location relative to smoothed zigzag pivots rather than ordinary bar-by-bar prices. It combines an overall pivot average, separate high/low pivot averages and dispersion envelopes. The resulting cloud is intended to contextualize whether current price is relatively elevated or depressed compared with prior swings. It is an indicator specification at a conceptual level, not an entry/exit strategy, and the source does not disclose the pivot detector or full dispersion definitions."

registry_key: null

runner: null

evaluation: null

---

# Zigzag Cloud

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Zigzag Cloud measures price location relative to smoothed zigzag pivots rather than ordinary bar-by-bar prices. It combines an overall pivot average, separate high/low pivot averages and dispersion envelopes. The resulting cloud is intended to contextualize whether current price is relatively elevated or depressed compared with prior swings. It is an indicator specification at a conceptual level, not an entry/exit strategy, and the source does not disclose the pivot detector or full dispersion definitions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core rules remain unresolved.

- Pivot construction and complete averaging/dispersion equations are absent.

## How it works

- Average the latest N zigzag pivots for the central line.
- Build adjacent averages using only pivot highs and only pivot lows.
- Add Bollinger-style upper/lower bands around the main average and outer bands derived from high- and low-pivot averages.

## Outputs and intended use

- Inspect the cloud and lines as relative price-location references.
- No automatic trade, breakout confirmation or reversal rule is stated.

## Parameters and stated settings

- Seven lines are described; the main Bollinger offsets use two standard deviations. N and averaging-type defaults are absent.

## Failure modes and caveats

- An evolving zigzag endpoint can alter averages unless confirmation is enforced.
- Swing-sampled dispersion differs from bar-sampled volatility.

## Missing information and implementation boundary

- Zigzag length/confirmation, mean type, N for each series and standard-deviation sample/basis are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the built-in calculation path.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Indicator presents 7 lines
```

### E2: mechanism

```text
moving average[/b] of last N zigzag pivots
```

### E3: parameters

```text
2 standard deviation difference.
```

### E4: mechanism

```text
only pivot highs and pivot lows
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_zlyn2rht_zigzag_cloud](../tv_zlyn2rht_zigzag_cloud.md)

## Source

https://www.tradingview.com/script/zlyn2RHt-Zigzag-Cloud/

Publication ID: zlyn2RHt. Source SHA-256: c6cb02477e5237435a574a40ad95812400d045c5f0cd05841e42ef2edfada893. Raw-description SHA-256: 76e79741a9c4ebd0b4f15f9f2dfbe64d0c5684d222ac682ccf6b6766ef89673d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
