---

id: tv_profile_pl0ipxy0

name: "HTF Liquidity Levels"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "HTF Liquidity Levels tracks previous daily, weekly and monthly extremes, emphasizing those price references that have not yet been revisited. Its purpose is to frame potential directional destinations or clusters during an intraday session. The author interprets those untouched levels as possible resting-order pools, but the indicator does not directly observe stop orders or order-book depth. A cluster is a price-geometry reference, not proof that price must move toward it. Tapped levels are visually distinguished and removed after the day ends."

registry_key: null

runner: null

evaluation: null

---

# HTF Liquidity Levels

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

HTF Liquidity Levels tracks previous daily, weekly and monthly extremes, emphasizing those price references that have not yet been revisited. Its purpose is to frame potential directional destinations or clusters during an intraday session. The author interprets those untouched levels as possible resting-order pools, but the indicator does not directly observe stop orders or order-book depth. A cluster is a price-geometry reference, not proof that price must move toward it. Tapped levels are visually distinguished and removed after the day ends.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Previous completed day/week/month extrema form a reproducible principal drawing; reaching a level highlights it and tapped references clear at day end. Cluster narratives and trade entries are not required for this level indicator.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Maintain prior day/week/month highs and lows and monitor whether price reaches them.
- Highlight touched levels and clear the touched subset at day end.

## Outputs and intended use

- Untapped higher-timeframe references and clusters support discretionary directional-bias planning.

## Parameters and stated settings

- Daily, weekly and monthly references are disclosed; no numeric defaults or controls are listed.

## Failure modes and caveats

- Historical extremes do not reveal actual resting order quantities.
- A supposed liquidity magnet can fail, and nearest-level/path arguments are qualitative.

## Missing information and implementation boundary

- Touch definition, session/timezone, retained history, cluster calculation, confirmation and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Prior-period extrema and touch tests use OHLCV prices/timestamps; order-book data is not part of the described implementation.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, purpose, readiness

```text
previous days, weeks, and months highs & lows
```

### E2: mechanism, outputs_and_use

```text
Once a level is tapped, it is highlighted. At the end of each day, all tapped levels are cleared.
```

### E3: risks

```text
resting orders, mainly in the form of stop-loss orders.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_pl0ipxy0_htf_liquidity_levels](../tv_pl0ipxy0_htf_liquidity_levels.md)

## Source

https://www.tradingview.com/script/PL0iPxy0-HTF-Liquidity-Levels/

Publication ID: PL0iPxy0. Source SHA-256: d47f7a1a437c647847215a80f2eda90cbd02ad569077615e238bdafbebd2679c. Raw-description SHA-256: 66d090a14639245ccdecccfeb596431b2385bbcb20701454bdb377b38ba95f4e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
