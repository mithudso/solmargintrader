---

id: tv_profile_2gaiphlg

name: "Periodic Activity Tracker [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Periodic Activity Tracker summarizes the balance of attributed buying and selling volume within calendar aggregation periods. It is intended to help a discretionary trader compare activity across periods and see when the difference between the two sides expands or contracts. The author interprets the upper line and signed delta as relative aggressiveness, while acknowledging that every liquid-market trade has both a buyer and seller. The display is an activity comparison rather than a standalone entry or exit rule. Its paired lines and bars express the same period totals in different visual forms."

registry_key: null

runner: null

evaluation: null

---

# Periodic Activity Tracker [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Periodic Activity Tracker summarizes the balance of attributed buying and selling volume within calendar aggregation periods. It is intended to help a discretionary trader compare activity across periods and see when the difference between the two sides expands or contracts. The author interprets the upper line and signed delta as relative aggressiveness, while acknowledging that every liquid-market trade has both a buyer and seller. The display is an activity comparison rather than a standalone entry or exit rule. Its paired lines and bars express the same period totals in different visual forms.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core buy-versus-sell volume attribution rule is absent.

- The core buy-versus-sell volume attribution rule is absent.

## How it works

- Accumulate buy and sell volume over the selected anchor period, then calculate their difference.
- Group displayed bars by calendar context: hours within the day, days within the week, weeks within the month, or months within the year.

## Outputs and intended use

- Red/green lines with gradient fill and matching paired bars compare attributed volumes.
- Optional delta and period tags make changes in relative activity easier to inspect.

## Parameters and stated settings

- Hourly, Daily, Weekly and Monthly anchors; bar width, volume colors and delta visibility are adjustable.
- The description inconsistently calls Daily the default in one example and Hourly the default later.
- Recommended maximum chart intervals are 5m, 1H, 4H and 1D for those respective anchors.

## Failure modes and caveats

- Buy/sell attribution does not establish actual aggressor classification without the undisclosed input method.
- Chart interval changes collection detail; incompatible intervals or excessive bar width generate warnings.

## Missing information and implementation boundary

- The rule assigning volume to buying versus selling is absent.
- No systematic price confirmation, entry, exit or sizing rule is given.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described aggregation is compatible with candle volume and prices; no separate trade feed is disclosed. This does not verify aggressor classification or code parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, readiness

```text
tracks the cumulative buy and sell volume in a user-defined period
```

### E2: mechanism, outputs_and_use

```text
Delta (difference) between buy & sell volume for each period
```

### E3: parameters

```text
the anchor period is set to Daily
```

### E4: parameters

```text
By default, the tool is set to Hourly.
```

### E5: parameters

```text
Hourly	: 5m charts or lower
[*] Daily	: 1H charts or lower
[*] Weekly	: 4H charts or lower
[*] Monthly	: 1D charts or lower
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_2gaiphlg_periodic_activity_tracker_luxalgo](../tv_2gaiphlg_periodic_activity_tracker_luxalgo.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/2GaipHlg-Periodic-Activity-Tracker-LuxAlgo/

Publication ID: 2GaipHlg. Source SHA-256: 42e282f4480b38333c80a197f1403fae3a087c6347e8d77712c3e424016ad893. Raw-description SHA-256: 9e3b0aa5ac611bc24cfac456e8173de7513602b1bf2257d92cc9d73f240304cb.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
