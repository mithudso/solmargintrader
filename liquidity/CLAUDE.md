# liquidity — agent rules

The Aero Slipstream LP manager. See README.md. **It can move real money.**

## Live operation (owner authorization)

On 2026-11-06 the owner authorized autonomous live operation for his own wallet
`0x901a89cEC0608eB5435A915f006b45bD46405314`. He described it as very small scale, with him as the only user.
Within that authorization agents may:
- install, restart and run `aero-lp daemon --live` (`scripts/aero-lp-service install`);
- let the daemon rebalance, compound, and deploy idle coins inside the caps in `~/.aero-lp/config.toml`.

Still required:
- Never raise a cap in `~/.aero-lp/config.toml` (`max_position_usd`, `max_total_deployed_usd`, `max_gas_usd`,
  `allowed_tokens`), and never lower `min_net_apr`, without the owner asking for it in that session.
- Never read, print or copy the key file (`key_file`). The program reads it itself and refuses it unless
  it is mode 600 and owned by the user.
- Code defaults stay dry-run. A fresh install must never sign.
- To stop everything, use `scripts/aero-lp-service kill`. Do not edit the config.

## Code rules

- Contract addresses live only in `src/aero_lp/addresses.py`. Change them only when two sources agree
  (the Aero docs Security page and the dromos-labs/metadex-slipstream-public deployment JSON).
- `strategy.py` and `allocator.py` stay pure (no I/O). Unit-test every decision branch.
- Every on-chain sequence goes through `Rebalancer` and a `Runner`, so dry-run simulates exactly what
  live would send.
- Income figures must be *measured*: fee growth and gauge reward share. Never use a quoted APR.
- Verify with `.venv/bin/ruff check src tests && .venv/bin/pytest -q` (offline) and `.venv/bin/pytest -q -m network` (live reads).
