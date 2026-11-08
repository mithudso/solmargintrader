---

id: tv_profile_hdskv6q5

name: "LTF Volume Microburst Bubbles (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "LTF Volume Microburst Bubbles identifies unusually large, directionally efficient lower-timeframe candles inside each chart candle. It aims to distinguish concentrated bursts of participation from ordinary total-bar volume. A signed aggregate score reflects whether bullish or bearish qualifying bursts dominate. The author suggests interpreting those bursts in market context: they may confirm continuation or appear near a reversal. The source explicitly says a burst alone cannot determine which outcome follows. It therefore acts as an intrabar participation cue rather than a standalone directional trading system."

registry_key: null

runner: null

evaluation: null

---

# LTF Volume Microburst Bubbles (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

LTF Volume Microburst Bubbles identifies unusually large, directionally efficient lower-timeframe candles inside each chart candle. It aims to distinguish concentrated bursts of participation from ordinary total-bar volume. A signed aggregate score reflects whether bullish or bearish qualifying bursts dominate. The author suggests interpreting those bursts in market context: they may confirm continuation or appear near a reversal. The source explicitly says a burst alone cannot determine which outcome follows. It therefore acts as an intrabar participation cue rather than a standalone directional trading system.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Burst concentration and signed score aggregation equations are undisclosed.

- Burst concentration and signed score aggregation equations are undisclosed.

## How it works

- Compare each intrabar volume with an EMA baseline and require a spike-ratio threshold.
- Require sufficient candle body relative to its full range and, optionally, an enabled session.
- Combine bullish/bearish qualifying bursts with concentration and strength into a signed score; signal when it reaches a threshold.

## Outputs and intended use

- Bubbles scale with unusual participation; directional signals and first-burst levels supply chart context.

## Parameters and stated settings

- Automatic/manual lower timeframe, EMA baseline length, spike/body-efficiency/signal thresholds and session timezone/selection are configurable.
- New Level Cooldown and Max Level Age govern repeat levels; numeric defaults are absent.

## Failure modes and caveats

- Candle-direction volume does not identify actual aggressor transactions.
- Intrabar availability and session filtering can change signals; continuation/reversal interpretation remains discretionary.

## Missing information and implementation boundary

- Score equation, concentration normalization, automatic-timeframe mapping, level construction, defaults and trade management are absent.

## Data requirements

Required inputs: lower-timeframe ohlcv, session/timezone definitions.

Repository input-class support: unavailable or unresolved. Requires compatible intrabar histories beyond chart candles; coverage is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
ratio = volume / volumeBaseline
```

### E2: mechanism

```text
EMA-based volume baseline.
```

### E3: mechanism, parameters

```text
Candle body efficiency above the minimum requirement.
```

### E4: risks

```text
Microburst itself does not determine whether price will continue or reverse.
```

### E5: parameters

```text
New Level Cooldown
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hdskv6q5_ltf_volume_microburst_bubbles_zeiierman](../tv_hdskv6q5_ltf_volume_microburst_bubbles_zeiierman.md)
- [tv_method_liquidity_sweep](../../tv_method_liquidity_sweep.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/Hdskv6Q5-LTF-Volume-Microburst-Bubbles-Zeiierman/

Publication ID: Hdskv6Q5. Source SHA-256: bf3748b570d42c446272179a6290525e18dfd9aef9a9f8869b04087d165a17a3. Raw-description SHA-256: e0f74dc235056f8d5b8bc778eb7bd02318f86d89840d1104d9cfacad8f351b68.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
