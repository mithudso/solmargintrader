---

id: tv_profile_xzfb6isb

name: "Smart Trader, Concentric Candles & Aristotelian Cycloids"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Explore candle-derived cycloid geometry and price contacts using volatility-normalized coordinates. The author explicitly presents the market relevance as an unvalidated hypothesis, despite displaying probability-like contact scores."

registry_key: null

runner: null

evaluation: null

---

# Smart Trader, Concentric Candles & Aristotelian Cycloids

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Explore candle-derived cycloid geometry and price contacts using volatility-normalized coordinates. The author explicitly presents the market relevance as an unvalidated hypothesis, despite displaying probability-like contact scores.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Yang-Zhang estimator details, radius conversion in log space, contact tolerances and sigmoid weights/calibration are undisclosed.

- Yang-Zhang estimator details, radius conversion in log space, contact tolerances and sigmoid weights/calibration are undisclosed.

## How it works

- Estimate per-bar Yang-Zhang volatility, scale log-price by that estimate, then select two backward-scanned range-expansion candles and optionally the largest-range candle in a period.
- Each selected candle provides an outer full-range circle plus upper/lower wick circles. Standard/curtate cycloids use a shared outer rolling radius, traced-point radius and apex phase; numerical inversion maps each bar coordinate to an angle and exponential transformation restores price.
- Contact analysis combines contact direction, curve/zone, relative volume, delta, absorption and confluence through sigmoid scoring. Footprint mode compares contact-price rows; geometric/intrabar volume engines supply reduced alternatives.

## Outputs and intended use

- Polyline curves, apex/trough references, nearest support/resistance and a dashboard show geometry and contact behavior.
- P(up), conviction and behavior labels are heuristic outputs, not demonstrated calibrated probabilities.

## Parameters and stated settings

- Volatility lookback default20, range1–2500; largest-candle lookback default20, range5–200.
- Live/closed calculation basis, trace/reference toggles, geometric/intrabar volume mode, recommended15-second intrabars and dashboard controls.

## Failure modes and caveats

- Diffusion scaling assumes a model and does not prove geometric invariance or predictive causality across instruments.
- The source inconsistently describes fallback as geometry-only versus volume-engine data; footprint access and tick-level precision claims are not verified.

## Missing information and implementation boundary

- Yang-Zhang estimator details, radius conversion in log space, contact tolerances and sigmoid weights/calibration are undisclosed.

## Data requirements

Required inputs: ohlcv, lower-timeframe volume data for intrabar mode, price-level footprint buy/sell history for full contact analysis.

Repository input-class support: unavailable or unresolved. OHLCV supplies geometric-mode inputs. Intrabar mode additionally needs lower-timeframe volume. Full CVCA requires optional contact-price footprint buy/sell levels whose availability is unverified;these data classes do not resolve the hidden geometry/scoring formulas.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Default: 20.
Range: 1–2500.
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Default: 20.
Range: 5–200.
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
x(θ) = R·θ − r·sin(θ+φ₀) + r·sin(φ₀)
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
y(θ) = R − r·cos(θ+φ₀)
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
15S (15-second) recommended
```

### E6: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
This indicator is [b]a theoretical exploration[/b]
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_volume_footprint](../tv_method_volume_footprint.md)
- [tv_xzfb6isb_smart_trader_concentric_candles_aristotelian_cycloids](../tv_xzfb6isb_smart_trader_concentric_candles_aristotelian_cycloids.md)

## Source

https://www.tradingview.com/script/xZFb6Isb-Smart-Trader-Concentric-Candles-Aristotelian-Cycloids/

Publication ID: xZFb6Isb. Source SHA-256: 4de2c19730b57f9fd3ae8adb912a8958dbc5d08ed23fffa3ed04b89bc2575859. Raw-description SHA-256: 29bd0ac58fc64549141922b526c76e38816f6d1f920398225f13272cf7bb4096.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
