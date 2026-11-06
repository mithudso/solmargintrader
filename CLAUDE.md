# aero-liquidity

Auto-rebalancer for Aero (aero.xyz) Slipstream concentrated-liquidity deposits on Base. See README.md.

## Rules for agents
- Never run `aero-lp run --live` or sign/broadcast anything without the user's explicit instruction in that session.
- Dry-run and `simulate` use eth_simulateV1 only; they are safe to run.
- Contract addresses live only in `src/aero_lp/addresses.py`; change them only with two agreeing sources
  (Aero docs Security page + dromos-labs/metadex-slipstream-public deployment JSON).
- Keep `strategy.py` pure (no I/O); unit-test every decision branch.
- Verify: `.venv/bin/ruff check src tests && .venv/bin/pytest -q` (offline) and `.venv/bin/pytest -m network` (live reads).
