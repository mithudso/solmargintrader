"""Mock-only confirmed outcome and cooldown regressions."""

from types import SimpleNamespace

import pytest
from test_engine import make_engine
from test_executor import OWNER, T0, FakeChain, WalletRunner, make_position

from aero_lp import engine as engine_module
from aero_lp.executor import ExecConfig, RebalanceError, Rebalancer


@pytest.mark.parametrize("operation", ["collect", "swap"])
def test_confirmed_transfer_amounts_survive_failed_postreceipt_read(operation):
    pos = make_position(False)

    class FailRead(WalletRunner):
        def execute(self, txs):
            result = super().execute(txs)
            if txs and (txs[-1].label == "collect" or txs[-1].label.startswith("swap ")):
                raise RuntimeError("post-receipt state unavailable")
            return result

    runner = FailRead(pos, pos.pool.sqrt_price_x96)
    rb = Rebalancer(FakeChain(), OWNER, ExecConfig())
    with pytest.raises(RebalanceError) as exc:
        if operation == "collect":
            rb.collect(pos, runner)
        else:
            rb.swap_exact(pos.pool, T0, 10**15, runner, 1)
    if operation == "collect":
        assert exc.value.partial.amounts_in_position == (10**15, 7)
    else:
        assert exc.value.partial.amount_out == 2230356


def test_recovered_replacement_resets_cooldown_once(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)
    slot = eng.state.slot(42)
    slot.current_token_id, slot.last_rebalance_ts, slot.edge_checks = 77, 100, 3
    eng.chain = SimpleNamespace(position=lambda *a, **k: SimpleNamespace(
        owner=OWNER, pool=SimpleNamespace(address="0x" + "11" * 20)))
    monkeypatch.setattr(engine_module, "minted_token_id", lambda *a: 88)
    monkeypatch.setattr(engine_module.time, "time", lambda: 7200)
    mint = {"hash": "0xmint", "pool": "0x" + "11" * 20,
            "intent": {"kind": "mint"}, "receipt": {"status": 1, "logs": []}}
    remove = {"intent": {"kind": "remove", "token_id": 77}, "receipt": {"status": 1}}
    eng.recover_submission(mint, [remove, mint])
    assert (slot.current_token_id, slot.last_rebalance_ts, slot.edge_checks) == (88, 7200, 0)
    monkeypatch.setattr(engine_module.time, "time", lambda: 9000)
    eng.recover_submission(mint, [remove, mint])
    assert slot.last_rebalance_ts == 7200 and len(slot.history) == 1
