---

id: tv_profile_25py1uvb

name: "Position Cost Distribution"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Estimate the distribution of outstanding share positions by acquisition-price region rather than simply accumulating traded volume at price."

registry_key: null

runner: null

evaluation: null

---

# Position Cost Distribution

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Estimate the distribution of outstanding share positions by acquisition-price region rather than simply accumulating traded volume at price.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Outstanding-share source, corporate-action adjustment, bucket allocation, conservation constraints and handling of turnover above one are unspecified.

- Outstanding-share source, corporate-action adjustment, bucket allocation, conservation constraints and handling of turnover above one are unspecified.

## How it works

- Initialize all shares into the first bar's price range, ideally covering the IPO. For each later day divide volume by outstanding shares, reduce existing bucket holdings by that turnover fraction and allocate new volume into the day's price range.

## Outputs and intended use

- Inspect estimated cost concentrations as possible pressure/support-resistance regions. The author distinguishes this modeled position distribution from a volume profile.

## Parameters and stated settings

- Initialization depends on chart start. Bucket granularity and allocation settings are not stated. Equal transfer probability for all shares is an explicit model assumption.

## Failure modes and caveats

- The model does not observe actual holder cost basis. Share issuance, splits, turnover above available shares and initialization error can materially distort inferred positions.

## Missing information and implementation boundary

- Outstanding-share source, corporate-action adjustment, bucket allocation, conservation constraints and handling of turnover above one are unspecified.

## Data requirements

Required inputs: daily OHLCV, historical shares outstanding, corporate-action adjustments.

Repository input-class support: unavailable or unresolved. Share-count history and corporate actions are external inputs; the saved prose does not supply them.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The daily turnover ratio is calculated by dividing the bar's trading volume by total outstanding shares.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
the model assumes each share has an equal probability of being exchanged, regardless of how long ago it was acquired or at what price.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Preferably, the chart window should include the stock's IPO date
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_25py1uvb_position_cost_distribution](../tv_25py1uvb_position_cost_distribution.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/25py1UVB-Position-Cost-Distribution/

Publication ID: 25py1UVB. Source SHA-256: 348736fd9863cc5caa5d66540dc477b1e65d12f1b8b6bd530cfeb17ad46bc484. Raw-description SHA-256: 8601a83dc9496de87c4d269c5dea61559453ad163fe7fe731385db551bf02a9f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
