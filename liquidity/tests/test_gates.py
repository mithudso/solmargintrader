"""Soak gate, research gate, grandfather record and the CLI refusal. Offline; nothing is signed."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from aero_lp import cli, gates
from aero_lp.config import Config, GateConfig, load

OWNER = "0x" + "ab" * 20
H = 3600.0


def cfg(**kw) -> Config:
    return Config(OWNER, **kw)


def passing(root, c):
    gates.record_research_result(root, c, c.gates.strategy_id, "pass", "test", now=1.0)


def soak(root, c, hours):
    t = 1000.0
    gates.record_dry_run_tick(root, c, t)
    for _ in range(int(hours * 2)):  # 30-minute ticks, the largest interval that counts
        t += 1800
        gates.record_dry_run_tick(root, c, t)


def test_live_refused_without_a_soak_record(tmp_path):
    c = cfg()
    passing(tmp_path, c)
    with pytest.raises(gates.LiveGateError, match="no soak record"):
        gates.check_live_allowed(tmp_path, c)


def test_live_allowed_after_the_configured_soak(tmp_path):
    c = cfg(gates=GateConfig(soak_hours=2))
    passing(tmp_path, c)
    soak(tmp_path, c, 1)
    with pytest.raises(gates.LiveGateError, match=r"1\.0 h of 2 h"):
        gates.check_live_allowed(tmp_path, c)
    soak(tmp_path, c, 1)  # restarts from the same fingerprint: continues accumulating
    assert any("soaked" in n for n in gates.check_live_allowed(tmp_path, c))


def test_default_soak_is_24_hours():
    assert GateConfig().soak_hours == 24.0


def test_downtime_between_dry_run_ticks_is_not_credited(tmp_path):
    c = cfg()
    gates.record_dry_run_tick(tmp_path, c, 0.0)
    doc = gates.record_dry_run_tick(tmp_path, c, 10 * H)
    assert doc["accumulated_s"] == gates.MAX_TICK_GAP_S


@pytest.mark.parametrize(
    "change",
    [
        lambda c: replace(c, allocator=replace(c.allocator, max_total_deployed_usd=999.0)),
        lambda c: replace(c, allocator=replace(c.allocator, min_net_apr=1.0)),
        lambda c: replace(c, safety=replace(c.safety, max_gas_usd=9.0)),
        lambda c: replace(c, strategy=replace(c.strategy, vol_k=3.0)),
        lambda c: replace(c, reward_mode="fees"),
    ],
)
def test_strategy_or_cap_change_resets_the_soak(tmp_path, change):
    c = cfg(gates=GateConfig(soak_hours=1))
    passing(tmp_path, c)
    soak(tmp_path, c, 1)
    gates.check_live_allowed(tmp_path, c)
    changed = change(c)
    with pytest.raises(gates.LiveGateError, match="configuration changed"):
        gates.check_live_allowed(tmp_path, changed)
    doc = gates.record_dry_run_tick(tmp_path, changed, 99999.0)
    assert doc["accumulated_s"] == 0.0 and len(doc["resets"]) == 1


def test_polling_and_gate_settings_do_not_reset_the_soak(tmp_path):
    c = cfg(gates=GateConfig(soak_hours=1))
    soak(tmp_path, c, 1)
    same = replace(c, poll_seconds=5.0, gates=GateConfig(soak_hours=1, allow_failed_research_gate=True))
    assert gates.config_fingerprint(same) == gates.config_fingerprint(c)


def test_grandfather_exempts_only_the_current_configuration(tmp_path):
    c = cfg()
    passing(tmp_path, c)
    gates.grandfather(tmp_path, c, "live before the gate existed", now=5.0)
    assert any("grandfathered" in n for n in gates.check_live_allowed(tmp_path, c))
    changed = replace(c, allocator=replace(c.allocator, max_position_usd=60.0))
    with pytest.raises(gates.LiveGateError, match="soak gate"):
        gates.check_live_allowed(tmp_path, changed)
    assert gates.summary(tmp_path, c)["grandfathered"] is True


def test_grandfather_is_one_time_and_needs_a_reason(tmp_path):
    c = cfg()
    with pytest.raises(ValueError):
        gates.grandfather(tmp_path, c, "  ")
    gates.grandfather(tmp_path, c, "reason")
    with pytest.raises(gates.LiveGateError, match="already exists"):
        gates.grandfather(tmp_path, c, "again")


def test_grandfather_survives_dry_run_ticks_of_the_same_config(tmp_path):
    c = cfg()
    passing(tmp_path, c)
    gates.grandfather(tmp_path, c, "r")
    gates.record_dry_run_tick(tmp_path, c, 1.0)
    gates.check_live_allowed(tmp_path, c)


def test_research_gate_missing_failed_and_passed(tmp_path):
    c = cfg(gates=GateConfig(soak_hours=0))
    gates.record_dry_run_tick(tmp_path, c, 1.0)
    with pytest.raises(gates.LiveGateError, match="no research-gate result"):
        gates.check_live_allowed(tmp_path, c)
    gates.record_research_result(tmp_path, c, c.gates.strategy_id, "fail", "KNOW-291 9/70 unsupported", now=10.0)
    with pytest.raises(gates.LiveGateError, match="'fail'"):
        gates.check_live_allowed(tmp_path, c)
    gates.record_research_result(tmp_path, c, "some-other-strategy", "pass", "x", now=20.0)
    with pytest.raises(gates.LiveGateError, match="'fail'"):  # another strategy's pass does not count
        gates.check_live_allowed(tmp_path, c)
    gates.record_research_result(tmp_path, c, c.gates.strategy_id, "pass", "rerun", now=30.0)
    gates.check_live_allowed(tmp_path, c)
    gates.record_research_result(tmp_path, c, c.gates.strategy_id, "fail", "regressed", now=40.0)
    with pytest.raises(gates.LiveGateError):  # the LATEST result decides
        gates.check_live_allowed(tmp_path, c)


@pytest.mark.parametrize(
    "content", ["not json", "{}", '{"results": "x"}', '{"results": [{"strategy": "aero-slipstream-lp"}]}']
)
def test_unreadable_research_record_fails_closed(tmp_path, content):
    c = cfg(gates=GateConfig(soak_hours=0))
    gates.record_dry_run_tick(tmp_path, c, 1.0)
    (tmp_path / "research-gate.json").write_text(content)
    with pytest.raises(gates.LiveGateError, match="research gate"):
        gates.check_live_allowed(tmp_path, c)


def test_owner_override_is_explicit_and_logged(tmp_path):
    c = cfg(gates=GateConfig(soak_hours=0, allow_failed_research_gate=True))
    gates.record_dry_run_tick(tmp_path, c, 1.0)
    gates.record_research_result(tmp_path, c, c.gates.strategy_id, "fail", "KNOW-291", now=2.0)
    notes = gates.check_live_allowed(tmp_path, c, now=50.0)
    assert any("OVERRIDDEN" in n for n in notes)
    line = json.loads((tmp_path / "gate-overrides.jsonl").read_text().splitlines()[0])
    assert line["gate"] == "research" and line["strategy"] == c.gates.strategy_id and "fail" in line["why"]
    # the override never waives the soak
    strict = replace(c, gates=GateConfig(soak_hours=1, allow_failed_research_gate=True))
    with pytest.raises(gates.LiveGateError, match="soak gate"):
        gates.check_live_allowed(tmp_path, strict)


def test_override_defaults_off():
    assert GateConfig().allow_failed_research_gate is False
    with pytest.raises(ValueError):
        GateConfig(allow_failed_research_gate="yes")  # type: ignore[arg-type]


def test_gates_load_from_toml(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text(
        f'owner = "{OWNER}"\n[gates]\nsoak_hours = 6\nallow_failed_research_gate = true\n'
        '[safe_exit]\nconvert_to = "USDC"\n'
    )
    c = load(p)
    assert c.gates.soak_hours == 6 and c.gates.allow_failed_research_gate and c.safe_exit.convert_to == "USDC"
    p.write_text(f'owner = "{OWNER}"\n[safe_exit]\nconvert_to = "DOGE"\n')
    with pytest.raises(ValueError):
        load(p)


def test_cli_refuses_live_daemon_before_touching_the_signer(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AERO_LP_HOME", str(tmp_path))
    cfgfile = tmp_path / "c.toml"
    cfgfile.write_text(f'owner = "{OWNER}"\n')
    monkeypatch.setattr("aero_lp.wallet.load_signer", lambda *a, **k: pytest.fail("signer must not load"))
    monkeypatch.setattr(cli, "AeroChain", lambda *a, **k: pytest.fail("no chain access before the gate"))
    monkeypatch.setattr(cli, "Engine", lambda *a, **k: pytest.fail("no engine construction before the gate"))
    assert cli.main(["daemon", "-c", str(cfgfile), "--live"]) == 3
    assert "refusing live mode" in capsys.readouterr().err
    assert cli.main(["run", "-c", str(cfgfile), "--live", "--once"]) == 3


def test_cli_gates_commands_round_trip(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AERO_LP_HOME", str(tmp_path))
    cfgfile = tmp_path / "c.toml"
    cfgfile.write_text(f'owner = "{OWNER}"\n')
    assert cli.main(["gates", "record-research", "-c", str(cfgfile), "--result", "fail", "--source", "KNOW-291"]) == 0
    assert cli.main(["gates", "record-research", "-c", str(cfgfile)]) == 2
    assert cli.main(["gates", "grandfather", "-c", str(cfgfile), "--reason", "live before gates"]) == 0
    assert cli.main(["gates", "grandfather", "-c", str(cfgfile), "--reason", "again"]) == 1
    out = capsys.readouterr().out
    assert "grandfathered" in out and "'fail'" in out
