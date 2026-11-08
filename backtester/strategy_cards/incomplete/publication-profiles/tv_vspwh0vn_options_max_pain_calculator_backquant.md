---

id: tv_profile_vspwh0vn

name: "Options Max Pain Calculator [BackQuant]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Options Max Pain Calculator models expiry payout concentration with synthetic open interest. It displays a hypothetical minimum-payout strike, pin zone, pain heatmap and gamma profile. The source explicitly lacks live options data, so these are scenario outputs rather than measured dealer positioning or actual market max pain. Claims of gravitational pull or manipulation risk are interpretations and do not establish expiry-price forecasts."

registry_key: null

runner: null

evaluation: null

---

# Options Max Pain Calculator [BackQuant]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Options Max Pain Calculator models expiry payout concentration with synthetic open interest. It displays a hypothetical minimum-payout strike, pin zone, pain heatmap and gamma profile. The source explicitly lacks live options data, so these are scenario outputs rather than measured dealer positioning or actual market max pain. Claims of gravitational pull or manipulation risk are interpretations and do not establish expiry-price forecasts.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core computation or input definitions remain unresolved.

- Synthetic interest, gamma and pin-risk calculations are undisclosed.
- Scenario input defaults and units are incomplete.

## How it works

- Generate strikes around current price and synthetic call/put interest shaped by distance, volume baseline, sentiment and dealer inputs.
- Evaluate in-the-money payouts at candidate expiry prices and choose the strike minimizing total modeled payout.
- Estimate net gamma using an unnamed simplified pricing model.

## Outputs and intended use

- Inspect modeled pain concentration and proximity/time-based pin-risk dashboard.
- Use daily or every-bar updates for scenario analysis.

## Parameters and stated settings

- Recommended strike count 15–25 and range 8–15%. The author says put/call ratio exactly 1.0 does not work.
- Expiry days, strike increments, implied volatility and dealer factors are configurable.

## Failure modes and caveats

- Synthetic interest cannot establish real exposure or predict pinning.
- Gamma sign alone does not prove support or amplified movement.

## Missing information and implementation boundary

- Synthetic OI equation, multipliers, gamma model, sign assumptions and pin thresholds are missing.

## Data requirements

Required inputs: ohlcv, user option scenario inputs.

Repository input-class support: unavailable or unresolved. The scenario input contract is not established by chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, risks

```text
synthetic open interest distributions
```

### E2: risks

```text
not live market information.
```

### E3: parameters

```text
recommended: 15-25
```

### E4: parameters

```text
recommended: 8-15%
```

### E5: parameters, risks

```text
It does not work if set to 1.0
```

### E6: mechanism

```text
The strike with minimum total pain becomes the Max Pain level
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_vspwh0vn_options_max_pain_calculator_backquant](../tv_vspwh0vn_options_max_pain_calculator_backquant.md)

## Source

https://www.tradingview.com/script/vsPwh0vN-Options-Max-Pain-Calculator-BackQuant/

Publication ID: vsPwh0vN. Source SHA-256: 0d9ef33d6b581e692437113359f1ac7c63d103caefd6b998bd6ad0b7e52e68c2. Raw-description SHA-256: 446da1cab00a1c95045c02bc909d4e855732b24db47b730c95a724d58c37d079.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
