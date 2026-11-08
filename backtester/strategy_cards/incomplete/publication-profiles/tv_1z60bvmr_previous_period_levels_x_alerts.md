---

id: tv_profile_1z60bvmr

name: "Previous Period Levels - X Alerts"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Previous Period Levels places the completed higher-timeframe candle’s open, high, low and close on the current chart. It aims to make those reference prices visible while allowing the user to control how much annotation appears. The author also presents the script as an example of advanced input handling and clear code structure. Financially, the levels provide context for discretionary interaction with prior-period prices; the description does not turn a crossing into a defined long or short position. Alerts are filtered through an adjustable moving average to reduce repeated or false notifications, although the precise test is not disclosed."

registry_key: null

runner: null

evaluation: null

---

# Previous Period Levels - X Alerts

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Previous Period Levels places the completed higher-timeframe candle’s open, high, low and close on the current chart. It aims to make those reference prices visible while allowing the user to control how much annotation appears. The author also presents the script as an example of advanced input handling and clear code structure. Financially, the levels provide context for discretionary interaction with prior-period prices; the description does not turn a crossing into a defined long or short position. Alerts are filtered through an adjustable moving average to reduce repeated or false notifications, although the precise test is not disclosed.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for previous completed higher-timeframe OHLC reference lines. The independently optional SMA alert filter is underspecified; the level computation itself is explicit.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Retrieve previous higher-timeframe OHLC reference values and draw lines and labels.
- Use an adjustable SMA in alert conditions; the source does not define its crossing or confirmation logic.

## Outputs and intended use

- Configurable reference lines and optional labels show prior-period prices.
- Filtered alerts draw attention to interactions with those levels rather than specifying complete orders.

## Parameters and stated settings

- Resolution choices exclude intervals below one hour and add 6/12 hour, 5 day, 3/6 month and yearly references.
- Adjustable SMA and extensive visual/label formatting settings; defaults are absent.

## Failure modes and caveats

- Higher-timeframe references require correct completed-period alignment.
- An SMA filter may delay notifications and does not prove a level will hold.

## Missing information and implementation boundary

- Exact alert predicate, SMA input/length defaults, reference alignment and trade-management rules are not specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Prior-period price levels and an SMA use the OHLCV data class; actual higher-timeframe history and implementation are unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, readiness

```text
display of previous higher time-frame
      OHLC values, drawn using line.new and label.new.
```

### E2: parameters

```text
excludes time frames lower than 1 hour
```

### E3: parameters

```text
• 6, and 12 Hour
       • 5 Day
       • 3, and 6 Month
       • 1 Year
```

### E4: mechanism, parameters

```text
Alert conditions using an adjustable SMA
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_1z60bvmr_previous_period_levels_x_alerts](../tv_1z60bvmr_previous_period_levels_x_alerts.md)

## Source

https://www.tradingview.com/script/1z60BvMR-Previous-Period-Levels-X-Alerts/

Publication ID: 1z60BvMR. Source SHA-256: edefd7dc9402ba25eaffce40b58d0bcc8f215a3f6dc01c93ef89105e2005198c. Raw-description SHA-256: 968484f91542f9deec3e5c51c542380d37d954a7e076b233cf2a697ca86753a3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
