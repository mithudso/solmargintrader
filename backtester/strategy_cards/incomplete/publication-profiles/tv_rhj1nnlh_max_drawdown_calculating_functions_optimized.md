---

id: tv_profile_rhj1nnlh

name: "Max Drawdown Calculating Functions (Optimized)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Calculate the largest decline from an earlier peak to a later trough in an ordered numerical array, including account-balance histories."

registry_key: null

runner: null

evaluation: null

---

# Max Drawdown Calculating Functions (Optimized)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: study. Review: independently reviewed.

## Idea and objective

Calculate the largest decline from an earlier peak to a later trough in an ordered numerical array, including account-balance histories.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The printed pairwise and running-peak recurrences define the principal absolute-drawdown calculation over an ordered nonempty array. This usable scope excludes percentage normalization and exact tuple-return or edge-case parity.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- The author offers absolute and percentage-named functions. Printed snippets calculate absolute earlier-peak/later-trough differences with a pairwise maximum update and a linear running-peak recurrence; the percentage normalization is not printed.

## Outputs and intended use

- Return an array containing maximum drawdown, peak, trough and iteration count. The demonstration uses recent closes, but the motivating input is account balance values.

## Parameters and stated settings

- Input is an arbitrary-length float array. The example uses the last ten closes; source complexity claims are n*(n-1)/2 versus n-1 comparisons.

## Failure modes and caveats

- Array ordering matters: a trough before a peak must not count as subsequent drawdown. Relative drawdown needs special treatment for zero or negative peaks.

## Missing information and implementation boundary

- Percentage denominator, empty-array behavior, peak/trough return types and tie handling are not fully documented.
- The illustrative snippets omit accumulator initialization; a full runnable implementation and explicit empty/zero/negative-input policy are not provided.

## Data requirements

Required inputs: ordered caller-supplied equity or price array.

Repository input-class support: available. A deterministic ordered-array calculation needs no external feed beyond the caller's chosen series.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Input : an array of floats of arbitrary size (the values we want the DD of)
Output : an array of 4 values [maxDD, peak, trough, iterations]
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
one non optimized needs n*(n - 1)/2 comparisons for a collection of n datas, the other one only needs n-1 comparisons.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
In the example we calculate the maxDDs of the last 10 close values.
```

### E4: mechanism, readiness, missing_information

```text
var peak = 0;
var n = prices.length
for (var i = 1; i < n; i++){
    dif = prices[peak] - prices[i];
    peak = dif < 0 ? i : peak;
    maxDrawdown = maxDrawdown > dif ? maxDrawdown : dif;
}

var n = prices.length
for (var i = 0; i < n; i++){
    for (var j = i + 1; j < n; j++){
        dif = prices[i] - prices[j];
        maxDrawdown = maxDrawdown > dif ? maxDrawdown : dif;
    }
}
```

## Source

https://www.tradingview.com/script/Rhj1nNLH-Max-Drawdown-Calculating-Functions-Optimized/

Publication ID: Rhj1nNLH. Source SHA-256: f52a6a432248874d0bee86e0e07a1f227de104c8113bf715c37c723baf5bb208. Raw-description SHA-256: 57162375d5f5d1489836b9cc0307f831be03ae44ee29a723ae6b72d3c7a972b2.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
