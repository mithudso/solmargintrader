import pytest
from eth_account import Account
from web3 import Web3

from aero_lp import abi, config, wallet
from aero_lp.chain import _type_str
from aero_lp.executor import minted_token_id


def test_abi_parser_tuple_array_and_names():
    params = abi._p("tuple(address target, bool allowFailure, bytes callData)[] calls, uint256 x")
    assert params[0]["type"] == "tuple[]" and params[0]["name"] == "calls"
    assert [c["type"] for c in params[0]["components"]] == ["address", "bool", "bytes"]
    assert _type_str(params[0]) == "(address,bool,bytes)[]"
    assert params[1] == {"type": "uint256", "name": "x"}


def test_abis_encode_offline():
    w3 = Web3()
    npm = w3.eth.contract(address="0x4857DB576eE0e45F10525eC59527BfD10beeC60b", abi=abi.NPM)
    mint = npm.encode_abi(
        "mint",
        args=[("0x" + "11" * 20, "0x" + "22" * 20, 100, -100, 100, 1, 2, 0, 0, "0x" + "33" * 20, 9, 0)],
    )
    # selector of mint((address,address,int24,int24,int24,uint256,uint256,uint256,uint256,address,uint256,uint160))
    sig = "mint((address,address,int24,int24,int24,uint256,uint256,uint256,uint256,address,uint256,uint160))"
    assert mint[:10] == "0x" + Web3.keccak(text=sig).hex().removeprefix("0x")[:8]
    router = w3.eth.contract(address="0x9Ee35Bf1bd69a03c6F0393582030fCe8Bb93D418", abi=abi.SWAP_ROUTER)
    data = router.encode_abi(
        "exactInputSingle", args=[("0x" + "11" * 20, "0x" + "22" * 20, 100, "0x" + "33" * 20, 1, 2, 3, 0)]
    )
    assert data.startswith("0x")


def test_minted_token_id_parses_transfer_from_zero():
    npm = "0x4857DB576eE0e45F10525eC59527BfD10beeC60b"
    owner = "0x00000000000000000000000000000000000000aa"
    topic0 = "0x" + Web3.keccak(text="Transfer(address,address,uint256)").hex().removeprefix("0x")
    logs = [
        {
            "address": "0x" + "99" * 20,
            "topics": [topic0, "0x" + "0" * 64, "0x" + "0" * 62 + "aa", hex(5)],
            "data": "0x",
        },
        {
            "address": npm,
            "topics": [topic0, "0x" + "0" * 64, "0x" + "0" * 62 + "aa", "0x" + format(1651452, "064x")],
            "data": "0x",
        },
    ]
    assert minted_token_id(logs, npm, owner) == 1651452
    assert minted_token_id(logs[:1], npm, owner) is None


def test_config_load_and_reject_unknown(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text(
        'owner = "0x00000000000000000000000000000000000000aa"\ntoken_ids = [1]\n'
        "[strategy]\nvol_k = 2.5\n[safety]\nmax_position_usd = 500\n"
    )
    cfg = config.load(p)
    assert cfg.strategy.vol_k == 2.5 and cfg.safety.max_position_usd == 500
    p.write_text('owner = "0x00000000000000000000000000000000000000aa"\ntoken_ids = [1]\ntypo_key = 1\n')
    with pytest.raises(ValueError, match="typo_key"):
        config.load(p)
    p.write_text('owner = "nope"\ntoken_ids = [1]\n')
    with pytest.raises(ValueError):
        config.load(p)


def test_example_config_parses():
    from pathlib import Path

    cfg = config.load(Path(__file__).parent.parent / "config.example.toml")
    assert cfg.reward_mode in config.REWARD_MODES


def test_wallet_rejects_mismatch_without_leaking_key(monkeypatch):
    monkeypatch.delenv("AERO_LP_KEY_FILE", raising=False)
    acct = Account.create()
    key = acct.key.hex()
    monkeypatch.setattr(wallet, "_from_keychain", lambda owner: None)
    monkeypatch.setenv("AERO_LP_PRIVATE_KEY", key)
    assert wallet.load_signer(acct.address).address == acct.address
    with pytest.raises(wallet.WalletError) as e:
        wallet.load_signer("0x00000000000000000000000000000000000000aa")
    assert key.removeprefix("0x") not in str(e.value)
    monkeypatch.setenv("AERO_LP_PRIVATE_KEY", "not-a-key")
    with pytest.raises(wallet.WalletError) as e2:
        wallet.load_signer(acct.address)
    assert "not-a-key" not in str(e2.value)
    assert e2.value.__cause__ is None


def test_misplaced_strategy_slippage_key_warns_instead_of_silently_doing_nothing(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text(
        'owner = "0x00000000000000000000000000000000000000aa"\ntoken_ids = [1]\n[strategy]\nmax_slippage_bps = 500\n'
    )
    with pytest.warns(UserWarning, match=r"\[execution\]\.max_slippage_bps"):
        cfg = config.load(p)
    assert cfg.execution.max_slippage_bps == 50.0  # unchanged default: the strategy key never applied


def test_config_rejects_negative_safety_limits(tmp_path):
    with pytest.raises(ValueError):
        config.SafetyConfig(max_gas_usd=-1)


def test_key_file_must_be_private_and_owned(tmp_path, monkeypatch):
    import os

    acct = Account.create()
    f = tmp_path / "wallet.private"
    f.write_text(acct.key.hex() + "\n")
    monkeypatch.delenv("AERO_LP_PRIVATE_KEY", raising=False)
    monkeypatch.setattr(wallet, "_from_keychain", lambda owner: None)
    os.chmod(f, 0o644)
    with pytest.raises(wallet.WalletError, match="readable by other users") as e:
        wallet.load_signer(acct.address, str(f))
    assert acct.key.hex().removeprefix("0x") not in str(e.value)
    os.chmod(f, 0o600)
    assert wallet.load_signer(acct.address, str(f)).address == acct.address
    monkeypatch.setattr(os, "getuid", lambda: 12345)
    with pytest.raises(wallet.WalletError, match="not you"):
        wallet.load_signer(acct.address, str(f))
