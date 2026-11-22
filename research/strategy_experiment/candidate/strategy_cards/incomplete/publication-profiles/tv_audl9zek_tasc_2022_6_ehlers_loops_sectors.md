---

id: tv_profile_audl9zek

name: "TASC 2022.6 Ehlers' Loops - Sectors"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This publication extends a Crocker-style comparative graph to several tickers and adds a candle side panel so the visualization can stand on its own. The financial objective supported by the short source is multi-instrument comparison with the current instrument’s price action available beside it. The description refers to a TASC article but does not reproduce its calculation, so this record does not import the price-volume filtering rules from another publication merely because their titles are related. Its intended use is visual research rather than a disclosed sector-rotation trade or ranked allocation model."

registry_key: null

runner: null

evaluation: null

---

# TASC 2022.6 Ehlers' Loops - Sectors

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This publication extends a Crocker-style comparative graph to several tickers and adds a candle side panel so the visualization can stand on its own. The financial objective supported by the short source is multi-instrument comparison with the current instrument’s price action available beside it. The description refers to a TASC article but does not reproduce its calculation, so this record does not import the price-volume filtering rules from another publication merely because their titles are related. Its intended use is visual research rather than a disclosed sector-rotation trade or ranked allocation model.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The Crocker graph computation, axes and ticker transformations are not described.

- The Crocker graph computation, axes and ticker transformations are not described.

## How it works

- Expand an unspecified Crocker graph to multiple tickers.
- Draw a side box containing current-ticker candles for standalone inspection.

## Outputs and intended use

- Comparative graph and candle side panel support multi-symbol market visualization.

## Parameters and stated settings

- Five tickers are shown; ticker defaults and all calculation controls are absent.

## Failure modes and caveats

- Without axis definitions or normalization rules, apparent inter-ticker differences may reflect scaling choices.

## Missing information and implementation boundary

- Graph inputs, axes, filters, normalization, ticker choices, update timing and financial decision rules are not described.

## Data requirements

Required inputs: multiple ticker histories, unspecified graph input streams.

Repository input-class support: unavailable or unresolved. External ticker histories and the graph’s actual data streams are not identified sufficiently to establish availability.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, readiness

```text
the crocker graph is expanded to show 5 tickers.
```

### E2: outputs_and_use

```text
draws a side box with current tickers candles so it can be used as standalone.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_audl9zek_tasc_2022_6_ehlers_loops_sectors](../tv_audl9zek_tasc_2022_6_ehlers_loops_sectors.md)

## Source

https://www.tradingview.com/script/AudL9ZEK-TASC-2022-6-Ehlers-Loops-Sectors/

Publication ID: AudL9ZEK. Source SHA-256: 336a42cc45a64dc1bed04ffe0bd740ffe453158aad077a65f86a984bdd8532ab. Raw-description SHA-256: e6c50c467e57191dc774628e7339e13fd650e97827eddc409b3f7d800d909dda.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
