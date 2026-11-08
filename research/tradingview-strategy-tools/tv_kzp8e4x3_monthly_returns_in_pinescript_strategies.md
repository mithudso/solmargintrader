---
id: tv_kzp8e4x3_monthly_returns_in_pinescript_strategies
name: "Monthly Returns in PineScript Strategies"
kind: research-tool
status: documentation-only
classification: reporting-tool
summary: "Add monthly and yearly return tables to an existing strategy so a trader can inspect when its performance changes."
registry_key: null
runner: null
evaluation: null
---
# Monthly Returns in PineScript Strategies

Version: 1.0.0 (2026-11-08). Delta: initial source-grounded companion card for a strategy-labelled tool.

**Classification:** reporting-tool. Companion research-tool card; excluded from the executable strategy roster.

## Idea and objective

Add monthly and yearly return tables to an existing strategy so a trader can inspect when its performance changes.

## How it works

- The script uses tables to display strategy performance by calendar period rather than add new entries or exits.
- Its intended use is to identify periods of unexpectedly good or poor performance for further analysis. A seasonal-looking return table is a diagnostic, not an independently tested timing rule.

## Documented rules and trade lifecycle

- Integrate the reporting code into an existing strategy.
- Display monthly/yearly performance; no separate trading rules are documented.

## Parameters and stated settings

- No return formula, calendar timezone, equity sampling policy or numerical defaults are stated in the description.

## Failure modes and caveats

- Different handling of open P&L, period boundaries or cash flows can change period returns.
- Selecting months after viewing the table would introduce a new selection experiment that needs independent validation.

## Missing information and implementation boundary

- Recover the return-compounding method, reset behavior, treatment of incomplete periods and realized versus marked-to-market equity.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: purpose

> This script will just show a table with monthly/yearly performance of your script. Quite a lot of traders/investors used to look at returns like that. Also, it might help you to identify periods of time when your strategy performed good/bad than expected and try to analyze that better.

## Sources

https://www.tradingview.com/script/kzp8e4X3-Monthly-Returns-in-PineScript-Strategies/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
