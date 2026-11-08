---

id: tv_profile_34r4mh5w

name: "Market Microstructure Analytics"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Market Microstructure Analytics estimates spread and liquidity stress from ordinary chart bars, helping users compare execution conditions with their own recent history. Its outputs are statistical proxies for transaction mechanics rather than observations of the exchange order book."

registry_key: null

runner: null

evaluation: null

---

# Market Microstructure Analytics

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Market Microstructure Analytics estimates spread and liquidity stress from ordinary chart bars, helping users compare execution conditions with their own recent history. Its outputs are statistical proxies for transaction mechanics rather than observations of the exchange order book.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for disclosed individual Roll, Parkinson and Amihud component computations, and signed-change OLS Kyle outline with supplied windows/edge conventions; exact composite, streaming MAD and tanh regime model remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Independently reproducible component scope: Roll=2*sqrt(-cov(deltaP_t,deltaP_t-1)) where covariance is negative; Parkinson range variance as printed; Amihud from supplied dollar volume. Caller selects rolling windows, dispersion convention and policies for nonnegative covariance, zero volume/range and insufficient samples. Kyle’s signed-change OLS outline is separately disclosed, with the source wording distinction retained.
- Roll spread uses twice the square root of negative lagged price-change covariance. Corwin–Schultz separates single- and paired-bar high/low ranges; Abdi–Ranaldo uses the close displacement from the log high/low midpoint and adjacent displacement products, excluding invalid flat-range pairs. A separate effective-spread proxy combines tick-rule direction and displacement from the bar midpoint.
- Amihud divides absolute log return by dollar volume and scales by 100 million for display. Kyle uses OLS of signed price-level change deltaP=Ct-Ct-1 on raw tick-signed volume Q=direction*V, with direction positive/negative for rising/falling closes and carried forward on equality; lambda=cov(Q,deltaP)/var(Q) under an intercept regression. Here price-level change is not abs(deltaP). The prose calls Roll inputs absolute price changes in contrast to log returns, so that wording must not be imported as a magnitude transform into Kyle; intercept/covariance conventions are not fully printed. Parkinson bar variance is ln(H/L)^2/(4*ln(2)).
- Spread, illiquidity and absolute-lambda robust z-scores are individually clipped and averaged, then transformed with tanh into the Liquidity Stress Index.

## Outputs and intended use

- Dashboard estimates, weights, stress/regime readings and the spread trend help assess whether trading conditions are becoming unusually expensive. A fast-versus-slow composite-spread EMA comparison indicates widening or compression without specifying price direction.

## Parameters and stated settings

- Estimation window defaults to 20 bars; smoothing 1 disables EMA smoothing. Maximum composite weight defaults to 70%, with a ridge equal to 5% of mean robust variance. LSI clipping defaults to three robust deviations. Spread-trend EMAs use five and twenty periods.
- Amihud display factor is 100 million; MAD scale consistency factor 1.4826. Robust spread z-score >=2 flags unusual widening. LSI neutral is 50, elevated stress 65–80 and severe stress >80; exact tanh scale is unprinted.

## Failure modes and caveats

- Aggregated-bar covariance and tick-rule direction differ from transaction-level observations. The midpoint effective-spread proxy is upward biased, while Roll aggregation can understate spread. Elevated lambda alone does not prove informed trading; historical crisis narratives are not measured predictive results.

## Missing information and implementation boundary

- The full Corwin–Schultz algebra, treatment of nonnegative Roll covariance, exact streaming-MAD implementation, weight-cap redistribution and tanh scale are omitted. Live bid/ask platform claims are historical author statements, not verified current API facts.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical analytical engine explicitly uses chart OHLCV; optional live bid/ask validation is not needed for its calculated proxies.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, required_data, risks, readiness

```text
Using only the OHLCV data
```

### E2: mechanism, parameters, required_data, risks, readiness

```text
The default of 20 is a reasonable starting point
```

### E3: mechanism, parameters, required_data, risks, readiness

```text
set to five percent of the mean robust variance
```

### E4: mechanism, parameters, required_data, risks, readiness

```text
set by default at 70 percent of the total
```

### E5: mechanism, parameters, required_data, risks, readiness

```text
compares a five-period exponential moving average of the composite spread against a twenty-period average
```

### E6: mechanism, parameters, required_data, risks, readiness

```text
At the default of three robust standard deviations
```

### E7: mechanism, parameters, required_data, risks, readiness

```text
The rolling MAD computation is a streaming approximation to the exact finite-window MAD.
```

### E8: mechanism, parameters, readiness

```text
The Roll (1984) estimator is the oldest and most widely cited. It computes the rolling covariance between a price change and the price change that came before it, then takes two times the square root of the negative of that covariance. One important detail: Roll's model is defined in terms of absolute price changes, not log-returns. Using log-returns introduces a scaling distortion tied to the price level of the asset, which biases the spread estimate upward at high prices. This implementation correctly uses delta-P throughout.
```

### E9: mechanism, parameters, readiness

```text
Kyle lambda, estimated here via ordinary least squares regression of price changes on signed volume, is the most theoretically sophisticated metric in the indicator. Each bar's signed volume is the total volume signed by the tick rule direction: positive if the bar closed higher than the previous bar, negative if it closed lower. The regression coefficient from regressing price changes on this signed volume is the lambda estimate. A high positive lambda means prices are moving more than expected for the amount of flow being absorbed, which is the signature of informed trading. When lambda rises, someone in the market likely knows something that others do not, and market makers are widening their spreads in response. The critical implementation detail here is that the volume must not be normalised before the regression. Normalising the signed volume changes the regression coefficient from a price-impact-per-share measure to a dimensionless sensitivity measure, which is a different quantity and does not correspond to Kyle's original model.
```

### E10: mechanism, parameters, readiness

```text
The Parkinson (1980) range-based volatility estimator serves a supporting role: it estimates intrabar variance from the high-low range using the formula sigma-squared equals one over four times the natural log of two, multiplied by the square of the log ratio of high to low. This estimator is approximately five times more statistically efficient than the classic close-to-close variance estimator for the same number of observations (Parkinson 1980). Its role in this indicator is to help decompose the high-low range: the range reflects both volatility and the spread, and the ratio of the composite spread estimate to the Parkinson volatility tells you which component is dominant at any given time.
```

### E11: mechanism, parameters, readiness

```text
The Amihud (2002) illiquidity ratio is the most widely used liquidity measure in the academic asset pricing literature. Its construction is conceptually simple: it divides the absolute value of a log return by the dollar volume of trading in the same period. What this measures is price impact per dollar traded. If a stock moves one percent and 10 million dollars changed hands, the ratio is small. If the same one percent move happened on only 50,000 dollars of volume, the ratio is large, indicating a thin market where small amounts of capital move prices significantly. Unlike the spread measures, which capture the cost of a single round trip, the Amihud ratio captures market depth. This implementation uses dollar volume rather than share or contract volume, which is the correct specification for comparability across instruments at different price levels. The ratio is scaled by a factor of 100 million for display purposes; its absolute level is asset-dependent and should always be interpreted relative to the instrument's own history.
```

### E12: mechanism, parameters, readiness

```text
Multiplied by the consistency factor 1.4826, it provides an equivalent to the standard deviation that is resistant to outliers with a breakdown point of 0.5, meaning up to half the observations in a window can be extreme values without corrupting the estimate. This approach follows Rousseeuw and Croux (1993), who established the formal properties of MAD-based scale estimators.
```

### E13: mechanism, parameters, readiness

```text
the composite spread is compared to its rolling median, and the deviation is normalised by the MAD. The result is a standardised score that tells you how many robust standard deviations the current spread is from its recent typical level. A score of two or above signals a statistically unusual widening event. The same procedure is applied independently to the Amihud illiquidity ratio and to the absolute value of Kyle lambda.
```

### E14: mechanism, parameters, readiness

```text
These three scores are then combined into the Liquidity Stress Index, computed as their equal-weighted average after each component has been winsorised at plus or minus three robust standard deviations. The winsorisation prevents a single extreme reading in one dimension from overwhelming the composite. Each component is then winsorised before averaging to prevent a single extreme dimension from dominating. The result is mapped to a zero-to-100 scale using the hyperbolic tangent function, where 50 represents neutral conditions, readings in the 65 to 80 range indicate elevated stress, and readings above 80 indicate severe stress across multiple liquidity dimensions simultaneously.
```

### E15: mechanism, parameters, readiness

```text
carrying the previous sign forward when the price is unchanged.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_34r4mh5w_market_microstructure_analytics](../../../strategy_research/tv_34r4mh5w_market_microstructure_analytics.md)

## Source

https://www.tradingview.com/script/34R4Mh5W-Market-Microstructure-Analytics/

Publication ID: 34R4Mh5W. Source SHA-256: ac15c46253c133ff711804bdc32c4ee54d6bd6820cd333450d5db23184b28e51. Raw-description SHA-256: 0e88512961fd35ed1534002877e9591ccfc3a38785710a077e7d190095549da4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
