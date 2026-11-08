---

id: tv_profile_djr8hv4v

name: "Waindrops [Makit0]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Waindrops splits user-defined periods into two portions and draws separate price-volume distributions and VWAPs for each. It aims to make intraperiod migration of value visible, with color based on whether the later VWAP rises, falls or matches the earlier one. Custom unbalanced/session settings support overnight-versus-cash comparison. The publication also teaches drawing-array techniques, but its financial purpose is explicit. The histogram is derived by iterating price ticks within candles, which can become computationally expensive and is not transaction-level volume reconstruction."

registry_key: null

runner: null

evaluation: null

---

# Waindrops [Makit0]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Waindrops splits user-defined periods into two portions and draws separate price-volume distributions and VWAPs for each. It aims to make intraperiod migration of value visible, with color based on whether the later VWAP rises, falls or matches the earlier one. Custom unbalanced/session settings support overnight-versus-cash comparison. The publication also teaches drawing-array techniques, but its financial purpose is explicit. The histogram is derived by iterating price ticks within candles, which can become computationally expensive and is not transaction-level volume reconstruction.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Candle-volume allocation and custom period/session splitting equations remain unspecified.

## How it works

- Aggregate high/low and independent VWAP/profile per period half.
- Draw central range and left/right VWAP bars with per-price histograms and volume labels.
- Classify sentiment by later-minus-earlier VWAP subject to a tick-based neutral tolerance.

## Outputs and intended use

- Waindrop bars/profiles, optional labels and current-price tracker support visual volume/price comparison.

## Parameters and stated settings

- Period default60 minutes, maximum2880; charts 1m–720m only.
- Default execution window five 24H periods, histogram bin two ticks (max50), bar width two pixels, profile width four pixels and neutral tolerance zero.
- Update cadence ranges end-period, halves, quarters or each bar; balanced halves default.

## Failure modes and caveats

- Fine tick granularity can trigger execution/loop timeout errors.
- Period/session alignment and incomplete halves affect interpretation.
- The source does not disclose candle-volume allocation across tick prices.

## Missing information and implementation boundary

- Exact per-tick allocation, VWAP price source, unbalanced-boundary mapping and defaults for update cadence are not fully reproduced.

## Data requirements

Required inputs: intraday ohlcv, symbol tick size, session/period definitions.

Repository input-class support: unavailable or unresolved. Requires supported intraday coverage, tick metadata and configured custom periods; exact available coverage is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
default 60, max 2880
```

### E2: parameters

```text
up to 12H (720m)
```

### E3: parameters

```text
lower chart timeframe you can use is 1m
```

### E4: parameters

```text
default 5
```

### E5: parameters

```text
Ticks per bar (max 50)
```

### E6: parameters

```text
default 2
```

### E7: parameters

```text
default 4
```

### E8: parameters

```text
default 0
```

### E9: mechanism, readiness

```text
for each tick in it stores the price and volume
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_djr8hv4v_waindrops_makit0](../../../strategy_research/tv_djr8hv4v_waindrops_makit0.md)

## Source

https://www.tradingview.com/script/dJr8hv4v-Waindrops-Makit0/

Publication ID: dJr8hv4v. Source SHA-256: c845dadef8a831bd7410f29a20684dd86a722dd16bebcdaa7116354257ff3d4f. Raw-description SHA-256: 7038c21464cdb380857d2ebd8ed80400b9171eb93407fbaac5865fc686a19fb2.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
