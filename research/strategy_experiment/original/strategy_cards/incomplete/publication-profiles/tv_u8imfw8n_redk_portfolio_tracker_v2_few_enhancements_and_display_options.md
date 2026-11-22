---

id: tv_profile_u8imfw8n

name: "RedK_Portfolio Tracker v2: few enhancements and display options"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Portfolio Tracker v2 monitors user-entered holdings and summarizes portfolio value and profit/loss in an infobox. This revision emphasizes displaying the summary as a floating panel and including free cash in overall portfolio accounting. It is a manually configured valuation aid rather than a brokerage reconciliation system or a buy/sell strategy."

registry_key: null

runner: null

evaluation: null

---

# RedK_Portfolio Tracker v2: few enhancements and display options

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Portfolio Tracker v2 monitors user-entered holdings and summarizes portfolio value and profit/loss in an infobox. This revision emphasizes displaying the summary as a floating panel and including free cash in overall portfolio accounting. It is a manually configured valuation aid rather than a brokerage reconciliation system or a buy/sell strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The explicit sum-of-symbol-times-quantity example defines gross holdings valuation; cash/PnL accounting and transactional returns remain unresolved extras.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Track holding cost and current value, include free cash in total portfolio/P&L percentage accounting while leaving position cost/value separate.
- Offer portfolio and PnL plots plus an infobox that can be moved to the price panel with plots hidden.

## Outputs and intended use

- Monitor daily portfolio changes through the summary panel; changing panel placement/scale is a display operation.

## Parameters and stated settings

- Supports ten positions plus cash, with cash not using a position slot. Default placement is a lower panel; users can hide plots and use no scale for floating display.

## Failure modes and caveats

- Analytical: manually entered positions/costs and market-feed timing can diverge from actual account equity; cash treatment and realized flows need verification.

## Missing information and implementation boundary

- Holdings input schema, fee/dividend/corporate-action treatment, PnL equations and transaction-history support are not described here.

## Data requirements

Required inputs: user portfolio holdings and cost basis, free cash, holding market prices.

Repository input-class support: unavailable or unresolved. Requires private holding/cash inputs and external security prices; chart OHLCV alone does not define the portfolio.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
Cash" will not count towards the total 10 positions
```

### E2: mechanism, readiness

```text
it will not impact the "cost of positions" or the (current) "value of positions"
```

### E3: parameters, readiness

```text
By default, when the Portfolio Tracker is added to the chart, it will occupy its own lower panel
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_u8imfw8n_redk_portfolio_tracker_v2_few_enhancements_and_display_options](../tv_u8imfw8n_redk_portfolio_tracker_v2_few_enhancements_and_display_options.md)

## Source

https://www.tradingview.com/script/U8imfw8n-RedK-Portfolio-Tracker-v2-few-enhancements-and-display-options/

Publication ID: U8imfw8n. Source SHA-256: 9886309abd37e4a81e4edc3067ed34ec670e2b978b9fe72532454b5967c7731d. Raw-description SHA-256: c40ed70a6cda735709e1899731e71fa40a610ddc972ed4ad7fcf2b44f84b42d9.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
