---

id: tv_profile_lx3zlt9l

name: "Volume Profile 3D (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Volume Profile 3D adds perspective and shading to a price-binned volume distribution. It maps each bar’s volume by average price, optionally splitting up-bar and down-bar contributions, then tilts and scales blocks to make concentration visually prominent. The dimensional effect is a rendering choice; it does not add a third measured market variable or reveal actual resting liquidity."

registry_key: null

runner: null

evaluation: null

---

# Volume Profile 3D (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Profile 3D adds perspective and shading to a price-binned volume distribution. It maps each bar’s volume by average price, optionally splitting up-bar and down-bar contributions, then tilts and scales blocks to make concentration visually prominent. The dimensional effect is a rendering choice; it does not add a third measured market variable or reveal actual resting liquidity.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The average-price allocation formula and price-bin geometry are not fully defined.

- The average-price allocation formula and price-bin geometry are not fully defined.

## How it works

- Divide the sampled high-low span into buckets and assign each bar’s volume using its average price.
- Scale block width by relative volume and apply slope/perspective geometry; aggregate or separate bullish/bearish candle volume.

## Outputs and intended use

- Inspect high-volume nodes, PoC and thin zones as support/resistance, mean-reversion or breakout context; no mechanical trade trigger is supplied.

## Parameters and stated settings

- Controls include visible-candle versus custom-bar period, bucket count, tilt, width, bull/bear separation, templates/colors and PoC gradient. No numeric defaults are listed.

## Failure modes and caveats

- Analytical: average-price allocation compresses intrabar information and candle direction is not aggressor-side volume; viewport changes can change the sampled profile.

## Missing information and implementation boundary

- Average-price formula, value-area calculation, PoC tie rules, defaults and live historical consistency are not fully disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
Each bar’s volume is added to the correct level, based on its average price.
```

### E2: mechanism, readiness

```text
Bull/Bear separation to see whether up bars or down bars created the volume.
```

### E3: parameters, readiness

```text
Use Active Chart –[/b] Profile updates with visible candles.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_lx3zlt9l_volume_profile_3d_zeiierman](../../../strategy_research/tv_lx3zlt9l_volume_profile_3d_zeiierman.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [xs_momentum](../../../strategy_research/xs_momentum.md)

## Source

https://www.tradingview.com/script/LX3zlT9L-Volume-Profile-3D-Zeiierman/

Publication ID: LX3zlT9L. Source SHA-256: 00c81d5b76fd4263254545e4822096b37e08a3b56948fa284507c6a49c5a989e. Raw-description SHA-256: 3a3cedad87dce1beb5675a329eff9a47219295690bc945f1587aab5cfe9d90b6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
