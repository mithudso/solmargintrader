---

id: tv_profile_zxcxrnij

name: "RedK Multi-Modal TrailingStop (RedK MMTStop)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "RedK Multi-Modal TrailingStop places several common stop-distance models behind one visual and alert interface. It aims to support management of an existing position, letting the trader change the stop method without changing how proximity and risk states are presented. A separate ATR-based distance gauge labels price as safe, watch or critical regardless of the selected stop model. The introductory claim of realizing maximum profit is aspirational: no trailing stop guarantees that outcome, and the indicator itself does not execute a broker order."

registry_key: null

runner: null

evaluation: null

---

# RedK Multi-Modal TrailingStop (RedK MMTStop)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

RedK Multi-Modal TrailingStop places several common stop-distance models behind one visual and alert interface. It aims to support management of an existing position, letting the trader change the stop method without changing how proximity and risk states are presented. A separate ATR-based distance gauge labels price as safe, watch or critical regardless of the selected stop model. The introductory claim of realizing maximum profit is aspirational: no trailing stop guarantees that outcome, and the indicator itself does not execute a broker order.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Stop recurrences, flip rules and safe/watch/critical thresholds are undisclosed.

## How it works

- Select ATR/Supertrend, Chandelier, Donchian, standard-deviation channel or fixed-percentage trail.
- Feed the selected trail into common flip/cross logic and calculate price-to-stop distance in separate ATR units.
- Classify proximity into safe/watch/critical states and expose corresponding alerts.

## Outputs and intended use

- Stop line/bands, live method/side/price panel, zone-transition prices, flip/cross/critical alerts and screener flip value support risk monitoring.

## Parameters and stated settings

- Five methods and five alerts. Separate safe-zone ATR and method settings plus layout/colors are configurable.
- Example uses 5% trailing stop on daily NVDA and ATR trail on 30-minute gold; defaults are not enumerated.

## Failure modes and caveats

- Close crosses and intrabar proximity are different events; exact timing matters.
- Indicator alerts do not ensure fills, prevent gaps or maximize realized gains.

## Missing information and implementation boundary

- Exact method equations, ratchet/reset/flip rules, lengths/multipliers, proximity thresholds and defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. All advertised stop models and distance gauges use OHLCV prices/volatility; live broker integration is not described.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
5 of the most-common trailing stop methods
```

### E2: parameters

```text
same five alerts
```

### E3: parameters

```text
5% -based trailing stops
```

### E4: parameters

```text
30min timeframe
```

### E5: mechanism, readiness

```text
gap between price and the stop in ATR units
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_trailing_stop](../../../strategy_research/tv_method_trailing_stop.md)
- [tv_zxcxrnij_redk_multi_modal_trailingstop_redk_mmtstop](../tv_zxcxrnij_redk_multi_modal_trailingstop_redk_mmtstop.md)

## Source

https://www.tradingview.com/script/ZxCXrnij-RedK-Multi-Modal-TrailingStop-RedK-MMTStop/

Publication ID: ZxCXrnij. Source SHA-256: c31d5a34bd94adf6d5a0b5e330cb36b473ff673c9e2c16df83d9380108f57b8c. Raw-description SHA-256: bc8b0d75c9d91e3f3e0bdea98a6462fe27f2200b4a949d923aea20ee96eb8841.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
