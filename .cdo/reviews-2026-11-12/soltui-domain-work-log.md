# SolTUI domain review — 2026-11-12

Owner: `/root/full_repo_health`. Root owns existing test files; this batch owns twelve domain production modules and the new domain regression test only. No owner home, feed, model, service, wallet, signing or order is exercised.

Commands selected before the first regression run:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=botmanager/src:.:executor/src INDEX_NO_AUTO=1 .venv/bin/python -m unittest soltui.tests.test_domain_audit_boundaries
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=botmanager/src:.:executor/src INDEX_NO_AUTO=1 .venv/bin/python -m unittest soltui.tests.test_domain_audit_boundaries soltui.tests.test_coin_fit soltui.tests.test_council soltui.tests.test_eth_scan soltui.tests.test_live_score soltui.tests.test_signals soltui.tests.test_signal_live soltui.tests.test_top5 soltui.tests.test_trend soltui.tests.test_utxo_scan soltui.tests.test_vote_explanation soltui.tests.test_wallet_activity soltui.tests.test_presets_netpct soltui.tests.test_simulation soltui.tests.test_cumulative soltui.tests.test_analyze
/opt/homebrew/bin/ruff check <modified domain paths>
git diff --check
```

Empirical scope: temporary local evidence, synthetic numeric vectors and injected provider functions. This is implementation regression verification, not strategy fitting, historical profitability qualification, a live API check or installed owner acceptance. Existing full SolTUI suite is long; affected tests run before a final integrated full gate once all source writes settle.

Source preimages: `/tmp/oraclebot-soltui-parent-preimages-20261112/soltui/`. Complete original reads cover all twelve assigned modules; exact ranges and final deltas will be saved in the final receipt. The design prototype's missing dependency/preflight is a separate M5 limitation.
