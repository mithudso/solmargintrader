---
id: tv_otfw8b2a_trading_report_generator_from_csv
name: "Trading Report Generator from CSV"
kind: research-tool
status: documentation-only
classification: reporting-tool
summary: "Reconstruct a strategy-tester performance report from an existing transaction log; it evaluates executed decisions rather than generate new ones."
registry_key: null
runner: null
evaluation: null
---
# Trading Report Generator from CSV

Version: 1.0.0 (2026-11-08). Delta: initial source-grounded companion card for a strategy-labelled tool.

**Classification:** reporting-tool. Companion research-tool card; excluded from the executable strategy roster.

## Idea and objective

Reconstruct a strategy-tester performance report from an existing transaction log; it evaluates executed decisions rather than generate new ones.

## How it works

- Parse pasted CSV transactions once, build trade objects and sort them chronologically.
- For the chart instrument, map logged transactions to the next bar's time interval and submit limit orders at the recorded fill price.
- The broker emulator is used as a reporting container. Its replay orders encode history; they are not predictions or an autonomous trading policy.

## Documented rules and trade lifecycle

- Required documented columns are Symbol, Side, Qty, Fill Price and Closing Time.
- Changing the chart instrument selects the corresponding transactions when the CSV includes multiple instruments.
- The author assumes the real fill price lies inside the relevant historical bar range so the replay limit order can execute. That assumption must be checked.

## Parameters and stated settings

- A single text input holds the CSV. The chart symbol and timeframe affect the reconstructed report.

## Failure modes and caveats

- Timezone mistakes, bar mapping, mismatched instrument identifiers or fills outside the bar can distort or omit replayed transactions.
- Limit-order replay may fail to preserve real fill sequencing, partial fills, costs and realized accounting. Compare against the original log.

## Missing information and implementation boundary

- The complete CSV parser, instrument matching, timezone conversion, position accounting and fee treatment are absent from the saved code field.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: purpose

> This script is a special strategy that parses transactions in csv format from Paper Trading (and it will also work for other brokers) and “plays” them. As a result, we get a Performance Report for a specific instrument based on our real trades in Paper or another broker.

### E2: columns

> leaving only: Side, Qty, Fill Price, Closing Time.

### E3: replay

> At the beginning of the calculation, we parse the csv once, create trade objects (Trade) and sort them in chronological order. Next, on each bar, we check whether we have trades for the time period of the next bar. If there are, we place a limit order for each trade, with limit price == Fill Price of the trade. Here, we assume that if the trade is real, its execution price will be within the bar range, and the Pine strategy engine will execute this order at the specified limit price.

## Sources

https://www.tradingview.com/script/OTfw8b2a-Trading-Report-Generator-from-CSV/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
