---

id: tv_profile_zsgx4esy

name: "Smart Trader, Episode 06, Isotropic Trend Lines"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Isotropic Trend Lines measures structural trend slope in log-price units normalized by realized volatility, aiming to make steepness less dependent on display scaling. It reduces non-overlapping blocks to range midpoints, finds a monotonic sequence, fits boundary lines through selected extremes and compares multiple scales. A state machine describes channel exits, returns and failures. This is contextual channel analysis rather than buy/sell advice. Volatility normalization helps comparability but cannot make different sampling intervals economically identical or make correlated prime-length analyses independent."

registry_key: null

runner: null

evaluation: null

---

# Smart Trader, Episode 06, Isotropic Trend Lines

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Isotropic Trend Lines measures structural trend slope in log-price units normalized by realized volatility, aiming to make steepness less dependent on display scaling. It reduces non-overlapping blocks to range midpoints, finds a monotonic sequence, fits boundary lines through selected extremes and compares multiple scales. A state machine describes channel exits, returns and failures. This is contextual channel analysis rather than buy/sell advice. Volatility normalization helps comparability but cannot make different sampling intervals economically identical or make correlated prime-length analyses independent.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Primary-scale/default conflict and incomplete volatility/state-transition equations prevent exact reproduction.

## How it works

- Estimate Yang-Zhang sigma; form each block’s geometric high/low midpoint.
- Find longest recent same-direction midpoint chain and compute arctangent(log displacement/sigma/elapsed bars).
- Fit log-linear upper/lower boundaries through extreme highs/lows, aggregate scale directions and track sigma-distance break/retest states.

## Outputs and intended use

- Channel/projection/fill, endpoint markers, trend-angle label and narrative dashboard support structural context.

## Parameters and stated settings

- Six stated scales 3,7,13,19,29,47, with primary user period; later defaults say period26/groups5/sigma20, conflicting with repeated scale19 wording.
- One-sigma excursion/rebound defines retest/confirmation context; consensus examples 5/6,6/6 and range≥4/6.
- Live default updates intrabar; Close mode shifts one bar and suppresses all nineteen alerts.

## Failure modes and caveats

- Primary-scale/default inconsistency affects reproduction.
- Live mode repaints intrabar; Close mode retains a deliberately live price header.
- Yang-Zhang assumptions and channel-extreme ordering can fail in unusual data.

## Missing information and implementation boundary

- Exact sigma equations/weights, state transition thresholds, boundary degeneracy handling and range-threshold default are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. All structural components derive from candle OHLCV; formulas/defaults remain incomplete.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
3, 7, 13, 19, 29, and 47
```

### E2: parameters, readiness

```text
Period 26, Groups 5, Sigma Length 20
```

### E3: parameters

```text
at least one σ away
```

### E4: parameters

```text
6/6
```

### E5: parameters

```text
5/6
```

### E6: parameters

```text
≥4/6
```

### E7: parameters

```text
19 alert conditions
```

### E8: risks

```text
Close Bar mode, all alert conditions are automatically suppressed
```

### E9: mechanism

```text
logarithmic price difference
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_liquidity_sweep](../../../strategy_research/tv_method_liquidity_sweep.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_zsgx4esy_smart_trader_episode_06_isotropic_trend_lines](../tv_zsgx4esy_smart_trader_episode_06_isotropic_trend_lines.md)

## Source

https://www.tradingview.com/script/ZSgx4eSy-Smart-Trader-Episode-06-Isotropic-Trend-Lines/

Publication ID: ZSgx4eSy. Source SHA-256: 29a6c1b2358138867ede2a6b55c186e00282d9581e2ae8134e1d2872b56d3ab3. Raw-description SHA-256: fd79515d984998fff9719cfec01e38108fd5f642ead05fe04c076346aeb0b7fa.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
