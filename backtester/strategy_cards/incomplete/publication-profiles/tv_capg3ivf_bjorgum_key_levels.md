---

id: tv_profile_capg3ivf

name: "Bjorgum Key Levels"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Bjorgum Key Levels identifies three related price-action situations around important levels: an initial breakout, a breakout that fails, and a later pullback to a flipped level. The idea is to help a trader distinguish momentum entries from trap reversals and trend pullback entries, each with a different balance between entry price and directional support. The source describes their rationale and visual alerts but does not disclose the actual detection algorithm."

registry_key: null

runner: null

evaluation: null

---

# Bjorgum Key Levels

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Bjorgum Key Levels identifies three related price-action situations around important levels: an initial breakout, a breakout that fails, and a later pullback to a flipped level. The idea is to help a trader distinguish momentum entries from trap reversals and trend pullback entries, each with a different balance between entry price and directional support. The source describes their rationale and visual alerts but does not disclose the actual detection algorithm.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Key-level construction and event confirmation conditions are undisclosed.

- Key-level construction and event confirmation conditions are undisclosed.

## How it works

- Analyze key levels, price structure and trend direction to label breakouts, false breakouts and backchecks.
- Treat a backcheck as a trend pullback into a previously flipped level, with contextual risk beneath demand or above supply.

## Outputs and intended use

- Use visual signals and alerts to inspect the three setup families rather than assuming every level breach is a continuation.

## Parameters and stated settings

- Three setup types are named; no numeric lookbacks, level definitions, thresholds or defaults are supplied.

## Failure modes and caveats

- The source notes breakout entries can be higher-priced and traps oppose a larger trend; analytical: examples do not establish steady returns or diversification benefits.

## Missing information and implementation boundary

- Key-level construction, trap failure timing, backcheck tolerance, alert confirmation and full risk/exit rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, purpose, readiness

```text
capture 3 of the most significant points in price action
```

### E2: mechanism, readiness

```text
Breakouts
[*]False Breakouts (Traps)
[*]Back Checks
```

### E3: outputs_and_use, readiness

```text
providing visual signals and alerts for when they occur.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_capg3ivf_bjorgum_key_levels](../tv_capg3ivf_bjorgum_key_levels.md)
- [tv_method_liquidity_sweep](../../../strategy_research/tv_method_liquidity_sweep.md)

## Source

https://www.tradingview.com/script/CapG3ivf-Bjorgum-Key-Levels/

Publication ID: CapG3ivf. Source SHA-256: 99633d8bada919260042a7fdaccec5e76ebea1387cd789795b35ee5d8a077bbc. Raw-description SHA-256: 21bd505daa7831d7a2443bed36ad5635edcffdc4fe6d422fae90b86dfb492d1b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
