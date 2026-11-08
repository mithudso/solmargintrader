---

id: tv_profile_eyhkvavh

name: "Index Generator [By MUQWISHI]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Index Generator builds a custom securities basket and displays its market-cap-weighted behavior as an index. It is intended for tracking a chosen market theme and researching historical movement, with a holdings table explaining each constituent’s contribution. The user controls the basket and display currency, so the resulting history is not evidence of an investable or historically reconstituted official index."

registry_key: null

runner: null

evaluation: null

---

# Index Generator [By MUQWISHI]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Index Generator builds a custom securities basket and displays its market-cap-weighted behavior as an index. It is intended for tracking a chosen market theme and researching historical movement, with a holdings table explaining each constituent’s contribution. The user controls the basket and display currency, so the resulting history is not evidence of an investable or historically reconstituted official index.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Index divisor, constituent weight updates and historical shares treatment are missing from the core index calculation.

- Index divisor, constituent weight updates and historical shares treatment are missing from the core index calculation.

## How it works

- Collect shares and prices for user-selected securities, calculate market capitalization and derive constituent weights.
- Combine holdings into an index series and display daily index change plus a constituent table and chart.

## Outputs and intended use

- Read index name/value, point/percentage daily changes, holdings price/cap/weight and company-information tooltips.

## Parameters and stated settings

- There are 34 symbol fields. Users choose index name, common currency, table layout/sort/style, candle/bar/line format and component visibility.

## Failure modes and caveats

- Analytical: current holdings or share counts applied retrospectively can introduce survivorship or lookahead bias; currency alignment matters.

## Missing information and implementation boundary

- Index divisor/base date, shares-outstanding history, FX conversion timing, corporate actions and rebalancing rules are not disclosed.

## Data requirements

Required inputs: selected securities price histories, shares outstanding histories, FX conversion series, company metadata.

Repository input-class support: unavailable or unresolved. External fundamentals, FX and selected holdings are required; no historical point-in-time basket is supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
collecting the number of shares and then computes the market capitalization
```

### E2: parameters, readiness

```text
There are 34 fields where user can fill them with symbols.
```

### E3: parameters, readiness

```text
Entering a currency. To unite all securities in one currency.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_eyhkvavh_index_generator_by_muqwishi](../tv_eyhkvavh_index_generator_by_muqwishi.md)

## Source

https://www.tradingview.com/script/EyHkVAVH-Index-Generator-By-MUQWISHI/

Publication ID: EyHkVAVH. Source SHA-256: ac02ec8fc618dda859b5be4b6bfdef09f3e126c804b53118b95a619a7538789e. Raw-description SHA-256: 6367a5e19af312021456e64d517c1f9a71e6513a75b50953b3ac5d7ca971cc48.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
