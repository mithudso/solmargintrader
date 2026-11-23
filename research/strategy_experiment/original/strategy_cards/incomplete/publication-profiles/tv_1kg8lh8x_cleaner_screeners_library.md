---

id: tv_profile_1kg8lh8x

name: "Cleaner Screeners Library"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Cleaner Screeners Library supplies the presentation layer for a configurable financial screener. It organizes symbols and indicator readings into groups and renders a common panel, allowing a caller to compare multiple symbols, timeframes, and indications without rebuilding the table structure. The library does not itself establish what an RSI value or a strong rating means for trading. Instead, the calling script supplies indicator values and configures the display and strength conventions. Its useful output is a consistent monitoring interface, not a portfolio-selection model or an automated order generator."

registry_key: null

runner: null

evaluation: null

---

# Cleaner Screeners Library

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Cleaner Screeners Library supplies the presentation layer for a configurable financial screener. It organizes symbols and indicator readings into groups and renders a common panel, allowing a caller to compare multiple symbols, timeframes, and indications without rebuilding the table structure. The library does not itself establish what an RSI value or a strong rating means for trading. Instead, the calling script supplies indicator values and configures the display and strength conventions. Its useful output is a consistent monitoring interface, not a portfolio-selection model or an automated order generator.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the principal financial screener-panel interface: initialization, grouped supplied values and display are documented. Internal strength normalization and example API typos remain caveats, not a claim of executable parity.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Initialize a panel, create screener groups, add indicator values with names/timeframes, then refresh the panel through display.
- Panel, screener, indication, config, and icon objects carry values, ratings, tooltips, layout and theme state.

## Outputs and intended use

- A vertical or horizontal table presents grouped symbol/indicator readings.
- External indicator inputs and customizable icons/colors support a caller’s monitoring workflow.

## Parameters and stated settings

- Configurable strong/weak values, theme, cell dimensions, text/font, borders and position.
- The source advertises 170 color presets and shows an RSI(close,14) example; these are display capacity and an example, not a validated trading setup.

## Failure modes and caveats

- A polished panel can obscure stale or incorrectly requested upstream values.
- Strong/weak ratings depend on caller conventions rather than a disclosed universal financial rule.

## Missing information and implementation boundary

- No market-data acquisition logic, default symbol universe, signal formula, update timing or decision rule is supplied.
- Examples contain inconsistent cleanscreen/cleanscreens names and spelling, so executable API correctness is unverified.

## Data requirements

Required inputs: caller-provided symbol/timeframe indicator values, external indicator series when selected.

Repository input-class support: unavailable or unresolved. The library renders supplied indications. Required symbols, feeds and indicator definitions are caller-dependent and not established by the description.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, outputs_and_use

```text
This indicator displays a panel with a list of symbols and their indications.
```

### E2: parameters

```text
Customizable colors with 170 presets included (dark and light)
```

### E3: parameters

```text
Customizable strong and weak values
```

### E4: parameters

```text
cleanscreens.Inidcator('1h', 'RSI', ta.rsi(close, 14))
```

### E5: mechanism, readiness

```text
Update the panel with cleanscreens.display(_paneel)
```

## Source

https://www.tradingview.com/script/1kg8lH8X-Cleaner-Screeners-Library/

Publication ID: 1kg8lH8X. Source SHA-256: 6c7f411b3f4863dfd73b8ea980925bdd6ab916d1c5c2ea5be1ad595e421a3716. Raw-description SHA-256: 35808659ff8c43a93943f8301d14f7a6ba5471cbdf8e8ed3151404ee060ad9ac.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
