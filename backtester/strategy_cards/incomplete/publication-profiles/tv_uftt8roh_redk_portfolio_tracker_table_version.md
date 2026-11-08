---

id: tv_profile_uftt8roh

name: "RedK Portfolio Tracker [Table Version]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "The table version of RedK Portfolio Tracker presents manually configured holdings and gain/loss information in a chart-overlay table. It replaces the older infobox presentation with more flexible colors, text size and placement. Its purpose is quick monitoring of a small portfolio, not automated account discovery or trading execution; dividends are mentioned only as a possible future addition."

registry_key: null

runner: null

evaluation: null

---

# RedK Portfolio Tracker [Table Version]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

The table version of RedK Portfolio Tracker presents manually configured holdings and gain/loss information in a chart-overlay table. It replaces the older infobox presentation with more flexible colors, text size and placement. Its purpose is quick monitoring of a small portfolio, not automated account discovery or trading execution; dividends are mentioned only as a possible future addition.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Entered holdings, entry prices and quantities define basic marked-value and cost comparison; fees, FX, dividends and cash-flow performance remain outside this narrow scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Combine entered positions, entry prices, quantities and free cash with market values to display portfolio and gain/loss information.
- Provide a table plus a stepping portfolio plot; the PnL plot is initially hidden.

## Outputs and intended use

- Read color-coded portfolio status directly on the price chart and adjust layout to suit the display.

## Parameters and stated settings

- Up to ten holdings plus free cash. Default display is on the price chart with no scale, visible portfolio line and hidden PnL plot; colors, size and location are configurable.

## Failure modes and caveats

- Analytical: static entries can become stale after trades or corporate actions; table colors do not constitute account reconciliation.

## Missing information and implementation boundary

- Valuation timing, PnL formula, cash-flow handling, fees, FX and dividend accounting are unspecified.

## Data requirements

Required inputs: user holdings quantities and entry prices, free cash, holding market prices.

Repository input-class support: unavailable or unresolved. Caller holdings and market prices are required; no actual portfolio inputs are supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
up to 10 holdings (+ free cash)
```

### E2: mechanism, readiness

```text
entry price and qty, then also add the free cash
```

### E3: parameters, readiness

```text
the PnL plot will be hidden by default
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_uftt8roh_redk_portfolio_tracker_table_version](../tv_uftt8roh_redk_portfolio_tracker_table_version.md)

## Source

https://www.tradingview.com/script/UFTT8ROh-RedK-Portfolio-Tracker-Table-Version/

Publication ID: UFTT8ROh. Source SHA-256: fb3ac6da72324aa17d3ae3d7ecdf9a0ebc4b6aaa69788660f6b469dcc25811d2. Raw-description SHA-256: 65ebee012e2508117f9f090b798a11609c1298ea975aa99b7c10f26f4cbf8041.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
