import os
import stat
from decimal import Decimal, localcontext

import pytest

from executor.config import OWNER_SOLANA, Config, default_toml, fingerprint, load_config, validate
from executor.errors import BadParams, ExecutorError, Refused
from executor.tokens import USDC_MINT, WSOL_MINT, raw_to_ui, resolve, ui_to_raw


def test_ui_to_raw_exact():
    assert ui_to_raw("1", 9) == 1_000_000_000
    assert ui_to_raw("0.000001", 6) == 1
    assert ui_to_raw(" 25.5 ", 6) == 25_500_000
    assert str(raw_to_ui(1, 6)) == "0.000001"


@pytest.mark.parametrize("bad", ["0", "-1", "abc", "1.0000001", "nan", "inf", "", "1e-7"])
def test_ui_to_raw_rejects(bad):
    with pytest.raises(BadParams):
        ui_to_raw(bad, 6)


def test_ui_to_raw_rejects_numbers_that_are_not_strings():
    with pytest.raises(BadParams):
        ui_to_raw(1.5, 6)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "amount", ["1.0000000000000000000000000001", "1e-100000000", "1e100000000", "18446744073.709551616"]
)
def test_ui_to_raw_never_rounds_underflows_or_exceeds_solana_u64(amount):
    with pytest.raises(BadParams):
        ui_to_raw(amount, 9)


def test_amount_conversion_is_independent_of_decimal_context():
    with localcontext() as ctx:
        ctx.prec = 6
        assert ui_to_raw("1.000000001", 9) == 1_000_000_001
        assert raw_to_ui(1_000_000_001, 9) == Decimal("1.000000001")
    assert ui_to_raw("18446744073.709551615", 9) == 2**64 - 1


def test_resolve_symbol_and_mint_and_unknown():
    assert resolve("sol").mint == WSOL_MINT
    assert resolve(USDC_MINT).symbol == "USDC"
    with pytest.raises(Refused):
        resolve("BONK")
    with pytest.raises(Refused):
        resolve("So1anaFakeMint111111111111111111111111111")


def test_config_created_mode_600_with_owner_defaults():
    cfg = load_config()
    mode = stat.S_IMODE(os.stat(cfg.path).st_mode)
    assert mode == 0o600
    assert cfg.mode == "dry-run"
    assert cfg.rails.max_position_usd == 25
    assert cfg.rails.daily_loss_stop_usd == 10
    assert cfg.rails.max_trade_usd <= 25
    assert cfg.rails.allowed_mints == ["SOL", "USDC"]
    assert cfg.gates.allow_failed_research_gate is False
    assert cfg.validation.enabled is False
    assert cfg.owner == OWNER_SOLANA


def test_code_defaults_are_dry_run_and_match_the_generated_file():
    assert Config().mode == "dry-run"
    assert 'mode = "dry-run"' in default_toml()


def test_config_round_trips_overrides(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text(default_toml().replace("max_position_usd = 25.0", "max_position_usd = 40"))
    p.chmod(0o600)
    assert load_config(p).rails.max_position_usd == 40.0


@pytest.mark.parametrize(
    "edit",
    [
        ("max_trade_usd = 10.0", "max_trade_usd = 30.0"),  # above max_position
        ("max_slippage_bps = 50", "max_slippage_bps = 5000"),
        ("max_slippage_bps = 50", "max_slippage_bps = 0"),
        ('mode = "dry-run"', 'mode = "yolo"'),
        ("daily_loss_stop_usd = 10.0", 'daily_loss_stop_usd = "ten"'),
        ("daily_loss_stop_usd = 10.0", "daily_loss_stop_usd = nan"),
        ("daily_loss_stop_usd = 10.0", "daily_loss_stop_usd = " + str(10**1000)),
        ('allowed_mints = ["SOL", "USDC"]', 'allowed_mints = ["SOL", "BONK"]'),
        ('allowed_mints = ["SOL", "USDC"]', "allowed_mints = []"),
        ("max_slippage_bps = 50", "max_slippage_bpz = 50"),  # typo = unknown key
        ('rpc_url = "https://api.mainnet-beta.solana.com"', 'rpc_url = "http://evil.example"'),
    ],
)
def test_config_fails_closed(tmp_path, edit):
    p = tmp_path / "c.toml"
    text = default_toml()
    assert edit[0] in text
    p.write_text(text.replace(*edit))
    p.chmod(0o600)
    with pytest.raises((ExecutorError, Refused)):
        load_config(p)


def test_config_refused_when_writable_by_others(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text(default_toml())
    p.chmod(0o666)
    with pytest.raises(ExecutorError, match="writable by others"):
        load_config(p)


def test_fingerprint_changes_with_rails_and_strategy():
    a, b = Config(), Config()
    b.rails.max_position_usd = 26
    assert fingerprint(a, "s") != fingerprint(b, "s")
    assert fingerprint(a, "s") != fingerprint(a, "t")
    c = Config()
    c.gates.soak_hours = 1  # gate settings alone do not reset the soak
    assert fingerprint(a, "s") == fingerprint(c, "s")


def test_validate_rejects_negative_reserve():
    c = Config()
    c.rails.min_sol_reserve_lamports = -1
    with pytest.raises(ExecutorError):
        validate(c)
