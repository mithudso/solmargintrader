---

id: tv_profile_hekxth56

name: "Backward Number of Bars"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Limit a strategy test by number of historical bars so a TradingView comparison can match an externally downloaded dataset."

registry_key: null

runner: null

evaluation: null

---

# Backward Number of Bars

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Limit a strategy test by number of historical bars so a TradingView comparison can match an externally downloaded dataset.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Window signature, whether the current bar counts, time anchoring and integration into entries/exits are unspecified.

- Window signature, whether the current bar counts, time anchoring and integration into entries/exits are unspecified.

## How it works

- Expose a backwards-bar window condition and use it to restrict the bars considered by a strategy. The author contrasts bar-count limits with selecting a calendar start date.

## Outputs and intended use

- Use the window condition to compare backtests over equivalent sample sizes. This is a test-scope aid and does not define a market entry or exit.

## Parameters and stated settings

- The source gives a 1000-bar external-data example and mentions window() == 1 as the inclusion test; it states no default.

## Failure modes and caveats

- Equal bar counts do not guarantee equal timestamps, session coverage or adjusted prices. Feed discrepancies can persist after sample-size matching.

## Missing information and implementation boundary

- Window signature, whether the current bar counts, time anchoring and integration into entries/exits are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history. Availability refers to input class, not code validation or cached history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
For example, we can draw 1000 bar data from stock exchange and perform the backtest on this data.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
You can plan your strategy by checking the number of bars you test with the window () == 1 parameter here
```

## Source

https://www.tradingview.com/script/hekXth56-Backward-Number-of-Bars/

Publication ID: hekXth56. Source SHA-256: 5d363da7e239180f99d16c85409b30f1ac93126ffd80150209a13d018c71753b. Raw-description SHA-256: c71af1b57b47fd33b0df4af0139def7b4cc90fac77f02afa67143dae7cbf5f29.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
