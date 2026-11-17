# Streaming Oracle compatibility fixtures

Version:1.0.0. Delta: preserve the synthetic0.9 state and actual-browser reference source.

`oracle-0.9-10m-state.json` contains synthetic state from canonical0.9, with31 issued forecasts and21 resolved outcomes. No owner profile, wallet, market performance or real account data is copied. Node tests use it to prove exact ten-minute key, weight, pending and metric compatibility.

`extension/e2e/fixtures/oracle-model-0.9.mjs` is the original model from commit ed7f4bd636f4027e4e5250ed47c3094bcdcbb3e1. Only its two relative import paths point to the unchanged reversal/indicator primitives. `oracle-model-0.9-provenance.json` binds the original source and adjusted fixture hashes. The native browser gate runs this frozen model inside Chrome, then verifies old-state persistence and resumed feedback using the new code. A Node-generated score differs by one floating-point field under the tested Chrome engine, so it is not misrepresented as a browser checkpoint. No production validation or score is relaxed.

The reference stays outside the Node test-discovery directory so it is not counted as an empty unit test. The reference module is test-only and is not imported by production source or listed as a runtime asset. The browser's separate test database leaves the running owner profile and real learned state untouched.
