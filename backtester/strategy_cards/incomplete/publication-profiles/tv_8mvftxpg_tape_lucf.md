---

id: tv_profile_8mvftxpg

name: "Tape [LucF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Tape reproduces a trading-console-style stream of chart-feed updates and estimates cumulative volume delta within the live bar. It is specifically a realtime tool: historical bars cannot reconstruct its update sequence. The author distinguishes chart updates from individual exchange ticks because multiple transactions may be aggregated before Pine receives them. The intended use is observation of live price/volume activity and configurable event alerts. Its signed volume is based on price-update direction, so it should not be interpreted as directly measured bid/ask aggressor volume."

registry_key: null

runner: null

evaluation: null

---

# Tape [LucF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Tape reproduces a trading-console-style stream of chart-feed updates and estimates cumulative volume delta within the live bar. It is specifically a realtime tool: historical bars cannot reconstruct its update sequence. The author distinguishes chart updates from individual exchange ticks because multiple transactions may be aggregated before Pine receives them. The intended use is observation of live price/volume activity and configurable event alerts. Its signed volume is based on price-update direction, so it should not be interpreted as directly measured bid/ask aggressor volume.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Live price-change polarity, unchanged-price carry, bar-reset delta and marker conditions define the tape/delta output. A missing historical live feed affects data availability rather than specification completeness.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Sign each update’s volume by price change since the preceding update; retain the previous sign when price is unchanged.
- Accumulate delta within the bar and reset bar totals at the next bar; re-execution clears recorded realtime history.
- Trigger markers for sequential delta bumps, a closing-bar delta threshold, or a large realtime tape-line volume.

## Outputs and intended use

- Tape rows show update time, price and volume; summary shows elapsed time, price change from bar open and cumulative delta.
- Divergent bar/delta polarity colors the time orange; markers also drive alerts.

## Parameters and stated settings

- Number/order of rows, low-volume filtering, precision, text/colors, position and marker thresholds are configurable.
- Three marker types have distinct realtime/bar-close timing; no numeric threshold defaults are given.

## Failure modes and caveats

- Refresh or input changes reset elapsed realtime values.
- Feed aggregation and directional-sign approximation prevent tick-exact or bid/ask-exact inference.
- Historical OHLCV backtests cannot reproduce these alerts.

## Missing information and implementation boundary

- Exact update-volume extraction, connection-gap handling, defaults and execution rules are absent.

## Data requirements

Required inputs: realtime chart-feed update sequence with incremental volume.

Repository input-class support: unavailable or unresolved. Requires live update-level observations and persistent intrabar state; historical OHLCV lacks that sequence.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: risks, required_data

```text
will not display information on historical bars.
```

### E2: risks

```text
Multiple broker/exchange ticks are often aggregated in one  chart update.
```

### E3: mechanism, readiness

```text
If price does not move between consecutive updates, then the last known polarity is used.
```

### E4: risks

```text
these values will all reset if the script re-executes
```

### E5: parameters

```text
There are three types of markers
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_8mvftxpg_tape_lucf](../../../strategy_research/tv_8mvftxpg_tape_lucf.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/8mVFTxPg-Tape-LucF/

Publication ID: 8mVFTxPg. Source SHA-256: 1e9451b7e3cfff25d9908289900f04ed007f76b7476e575701eef70f2fa07d93. Raw-description SHA-256: 346761e2c8280f900ba499d218426371a6a8bdddf190ecf9cf878447ea685968.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
