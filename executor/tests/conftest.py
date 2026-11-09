"""Shared test machinery: an isolated home, a fixture-backed HTTP seam, an in-memory chain, and a transaction builder.

No test here touches the network. Recorded responses live in tests/fixtures (captured from the live services on
2026-11-07); everything else is built in memory.
"""

from __future__ import annotations

import base64
import json
import struct
from pathlib import Path
from typing import Any

import pytest
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction

from executor import registry, txverify
from executor.config import Config, load_config
from executor.engine import Engine
from executor.errors import SendRejected
from executor.jupiter import Jupiter
from executor.rpc import Rpc
from executor.tokens import USDC_MINT, WSOL_MINT

FIX = Path(__file__).parent / "fixtures"
SYSTEM = txverify.SYSTEM_PROGRAM
TOKEN = txverify.TOKEN_PROGRAM
ATA = txverify.ATA_PROGRAM
CB = txverify.COMPUTE_BUDGET
JUP = txverify.JUPITER_V6
SHARED_ROUTE = bytes.fromhex("c1209b3341d69c81")


def fixture(name: str) -> Any:
    return json.loads((FIX / name).read_text())


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Every test gets its own home and log dir; the real ~/.executor is never read or written."""
    monkeypatch.setenv("EXECUTOR_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("EXECUTOR_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.delenv("JUPITER_API_KEY", raising=False)
    return tmp_path


# -- transaction builder ---------------------------------------------------------------------------------------


def pk(s: str | Pubkey) -> Pubkey:
    return s if isinstance(s, Pubkey) else Pubkey.from_string(s)


def meta(addr, signer=False, writable=False) -> AccountMeta:
    return AccountMeta(pk(addr), signer, writable)


def ix(program: str, data: bytes, *accts: AccountMeta) -> Instruction:
    return Instruction(pk(program), data, list(accts))


def cu_limit(n: int) -> Instruction:
    return ix(CB, bytes([2]) + struct.pack("<I", n))


def cu_price(micro: int) -> Instruction:
    return ix(CB, bytes([3]) + struct.pack("<Q", micro))


def ata_create(owner: str, mint: str, payer: str | None = None, wallet: str | None = None) -> Instruction:
    payer = payer or owner
    wallet = wallet or owner
    ata = txverify.ata_address(wallet, mint)
    return ix(
        ATA,
        b"\x01",
        meta(payer, True, True), meta(ata, False, True), meta(wallet), meta(mint),
        meta(SYSTEM), meta(TOKEN),
    )  # fmt: skip


def sys_transfer(src: str, dst: str, lamports: int) -> Instruction:
    return ix(SYSTEM, struct.pack("<IQ", 2, lamports), meta(src, True, True), meta(dst, False, True))


def jupiter_ix(
    owner: str,
    mint_in: str,
    mint_out: str,
    data: bytes | None = None,
    *,
    amount=10_000_000,
    quoted=901_607,
    slippage=50,
) -> Instruction:
    if data is None:
        data = (
            SHARED_ROUTE
            + b"\x00"
            + struct.pack("<I", 1)
            + bytes([48, 100, 0, 1])
            + struct.pack("<QQHB", amount, quoted, slippage, 0)
        )
    return ix(
        JUP,
        data,
        meta(owner, True, False),
        meta(txverify.ata_address(owner, mint_in), False, True),
        meta(txverify.ata_address(owner, mint_out), False, True),
        meta(POOL_VAULT_IN, False, True),
        meta(POOL_VAULT_OUT, False, True),
        meta(POOL_STATE, False, True),
    )


# Stable, valid, throwaway addresses standing in for AMM state and vaults (program-owned accounts in the fake chain).
POOL_STATE = str(Keypair.from_seed(bytes([7] * 32)).pubkey())
POOL_VAULT_IN = str(Keypair.from_seed(bytes([8] * 32)).pubkey())
POOL_VAULT_OUT = str(Keypair.from_seed(bytes([9] * 32)).pubkey())
ATTACKER = str(Keypair.from_seed(bytes([66] * 32)).pubkey())
UNKNOWN_PROGRAM = str(Keypair.from_seed(bytes([77] * 32)).pubkey())
OTHER_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"  # USDT, real mint but not part of a SOL/USDC swap


def swap_instructions(
    owner: str,
    mint_in: str,
    mint_out: str,
    amount: int,
    *,
    priority_micro: int = 50_000,
    cu: int = 100_000,
    quoted: int | None = None,
    slippage: int = 50,
) -> list[Instruction]:
    out = [cu_limit(cu), cu_price(priority_micro)]
    if WSOL_MINT in (mint_in, mint_out):
        out.append(ata_create(owner, WSOL_MINT))
    if mint_in == WSOL_MINT:
        wsol_ata = txverify.ata_address(owner, WSOL_MINT)
        out.append(sys_transfer(owner, wsol_ata, amount))
        out.append(ix(TOKEN, bytes([17]), meta(wsol_ata, False, True)))
    if quoted is None:
        quoted = amount * 901_607 // 10_000_000 if mint_in == WSOL_MINT else amount * 10_000_000 // 901_607
    out.append(jupiter_ix(owner, mint_in, mint_out, amount=amount, quoted=quoted, slippage=slippage))
    if WSOL_MINT in (mint_in, mint_out):
        wsol_ata = txverify.ata_address(owner, WSOL_MINT)
        out.append(
            ix(TOKEN, bytes([9]), meta(wsol_ata, False, True), meta(owner, False, True), meta(owner, True, False))
        )
    return out


def make_tx(instructions: list[Instruction], payer: str, n_sigs: int = 1) -> VersionedTransaction:
    msg = Message.new_with_blockhash(instructions, pk(payer), Hash.default())
    return VersionedTransaction.populate(msg, [Signature.default()] * msg.header.num_required_signatures)


def tx_b64(tx: VersionedTransaction) -> str:
    return base64.b64encode(bytes(tx)).decode()


# -- fixture-backed HTTP ---------------------------------------------------------------------------------------


class FakeHttp:
    """Serves recorded Jupiter / LI.FI / RPC responses by URL path. Records every call."""

    def __init__(self):
        self.calls: list[tuple[str, str, Any]] = []
        self.handlers: dict[str, Any] = {}

    def on(self, path_fragment: str, response):
        self.handlers[path_fragment] = response

    def _answer(self, method: str, url: str, payload: Any):
        self.calls.append((method, url, payload))
        for frag, resp in self.handlers.items():
            if frag in url:
                return resp(payload) if callable(resp) else resp
        raise AssertionError(f"unexpected {method} {url}")

    def get_json(self, url, params=None, headers=None):
        return self._answer("GET", url, params)

    def post_json(self, url, body, headers=None):
        return self._answer("POST", url, body)


# -- in-memory chain -------------------------------------------------------------------------------------------


def token_account(
    mint: str, owner: str, amount: int, lamports: int = 2_039_280, program: str = TOKEN
) -> dict[str, Any]:
    data = bytearray(165)
    data[0:32] = bytes(pk(mint))
    data[32:64] = bytes(pk(owner))
    data[64:72] = struct.pack("<Q", amount)
    data[108] = 1
    return {"lamports": lamports, "owner": program, "data": bytes(data)}


def wallet_account(lamports: int) -> dict[str, Any]:
    return {"lamports": lamports, "owner": SYSTEM, "data": b""}


def pool_account(lamports: int = 1_000_000) -> dict[str, Any]:
    return {"lamports": lamports, "owner": JUP, "data": b"\x00" * 8}


class FakeRpc(Rpc):
    """Subclasses Rpc so the engine's isinstance-free duck typing is exercised; every network method is overridden."""

    def __init__(self):
        self.state: dict[str, dict[str, Any] | None] = {}
        self.mods: dict[str, Any] = {}  # addr -> function(pre account) -> post account (applied in simulate)
        self.sim_err: Any = None
        self.sent: list[str] = []
        self.send_behaviour: Any = "ok"  # "ok" | "reject" | "timeout" | "wrong_sig"
        self.statuses: dict[str, Any] = {}
        self.default_status: Any = {"confirmationStatus": "confirmed", "err": None}
        self.tx_meta: dict[str, Any] | None = None  # returned for any signature when set
        self.txs: dict[str, Any] = {}
        self.height = 1000
        self.simulations = 0
        self.tx_available = True

    def balance(self, address):
        acc = self.state.get(address)
        return acc["lamports"] if acc else 0

    def accounts(self, addresses):
        return [self.state.get(a) for a in addresses]

    def block_height(self):
        return self.height

    def simulate(self, tx_b64_, watch, sig_verify, replace_blockhash):
        self.simulations += 1
        post = []
        for addr in watch:
            acc = self.state.get(addr)
            fn = self.mods.get(addr)
            post.append(fn(acc) if fn else acc)
        return {"err": self.sim_err, "accounts": post, "unitsConsumed": 90_000, "logs": []}

    def send_transaction(self, tx_b64_):
        self.sent.append(tx_b64_)
        if self.send_behaviour == "reject":
            raise SendRejected("sendTransaction rejected: preflight failed")
        if self.send_behaviour == "timeout":
            raise TimeoutError("read timed out")
        tx = VersionedTransaction.from_bytes(base64.b64decode(tx_b64_))
        sig = str(tx.signatures[0])
        return "1" * 64 if self.send_behaviour == "wrong_sig" else sig

    def signature_statuses(self, signatures):
        return [self.statuses.get(s, self.default_status) for s in signatures]

    def transaction(self, signature):
        if not self.tx_available:
            return None
        return self.txs.get(signature, self.tx_meta)


def tx_json(
    owner: str, native_delta: int, fee: int, token_changes: dict[str, tuple[int, int]], slot: int = 99
) -> dict[str, Any]:
    """A getTransaction-shaped dict: owner is account 0; token_changes maps mint -> (pre, post) raw amount."""

    def entries(idx):
        return [
            {"accountIndex": 1, "mint": m, "owner": owner, "uiTokenAmount": {"amount": str(pp[idx])}}
            for m, pp in token_changes.items()
        ]

    return {
        "slot": slot,
        "transaction": {"message": {"accountKeys": [owner, "11111111111111111111111111111111"]}},
        "meta": {
            "err": None, "fee": fee, "preBalances": [1_000_000_000, 1], "postBalances": [1_000_000_000 + native_delta, 1],
            "preTokenBalances": entries(0), "postTokenBalances": entries(1), "loadedAddresses": {"writable": [], "readonly": []},
        },
    }  # fmt: skip


def delta_native(n: int):
    return lambda acc: {**acc, "lamports": acc["lamports"] + n} if acc else None


def delta_token(n: int, mint: str, owner: str):
    def fn(acc):
        cur = struct.unpack("<Q", acc["data"][64:72])[0] if acc else 0
        base = acc or token_account(mint, owner, 0)
        data = bytearray(base["data"])
        data[64:72] = struct.pack("<Q", cur + n)
        return {**base, "data": bytes(data)}

    return fn


@pytest.fixture
def owner_kp() -> Keypair:
    return Keypair.from_seed(bytes([1] * 32))


@pytest.fixture
def owner(owner_kp) -> str:
    return str(owner_kp.pubkey())


def write_keyfile(path: Path, kp: Keypair, mode: int = 0o600) -> str:
    path.write_text(json.dumps(list(bytes(kp))))
    path.chmod(mode)
    return str(path)


@pytest.fixture
def cfg(owner, tmp_path, owner_kp) -> Config:
    """A config for the synthetic owner, with a mode-600 key file for the synthetic key."""
    keyfile = write_keyfile(tmp_path / "key.json", owner_kp)
    c = load_config()
    c.owner = owner
    c.key_file = keyfile
    return c


@pytest.fixture
def chain(owner) -> FakeRpc:
    """A wallet with 1 SOL and 100 USDC, its SOL/USDC token accounts, and the pool accounts the fake route touches."""
    r = FakeRpc()
    r.state[owner] = wallet_account(1_000_000_000)
    r.state[txverify.ata_address(owner, USDC_MINT)] = token_account(USDC_MINT, owner, 100_000_000)
    r.state[txverify.ata_address(owner, WSOL_MINT)] = None
    for a in (POOL_STATE, POOL_VAULT_IN, POOL_VAULT_OUT):
        r.state[a] = pool_account()
    return r


QUOTE_SOL_USDC = fixture("jup_quote_sol_usdc.json")
PRICES = fixture("jup_prices.json")


def jup_http_for(
    owner: str, mint_in: str, mint_out: str, amount: int, instructions=None, out_amount: int | None = None, impact="0"
) -> FakeHttp:
    """HTTP seam that answers quote / price / swap consistently for a synthetic owner."""
    http = FakeHttp()

    def quote(params):
        q = json.loads(json.dumps(QUOTE_SOL_USDC))
        q["inputMint"], q["outputMint"] = params["inputMint"], params["outputMint"]
        q["inAmount"], q["slippageBps"], q["priceImpactPct"] = params["amount"], int(params["slippageBps"]), impact
        if out_amount is not None:
            q["outAmount"] = str(out_amount)
            q["otherAmountThreshold"] = str(int(out_amount * 0.995))
        elif mint_in == USDC_MINT:  # USDC -> SOL at ~90.1
            q["outAmount"] = str(int(int(params["amount"]) * 1000 / 90.1))
            q["otherAmountThreshold"] = str(int(int(q["outAmount"]) * 0.995))
        elif mint_in == WSOL_MINT:
            q["outAmount"] = str(int(int(params["amount"]) * 90.1 / 1000))
            q["otherAmountThreshold"] = str(int(int(q["outAmount"]) * 0.995))
        q["otherAmountThreshold"] = str(int(q["outAmount"]) * (10_000 - q["slippageBps"]) // 10_000)
        return q

    def swap(body):
        q = body["quoteResponse"]
        ixs = (
            instructions
            if instructions is not None
            else swap_instructions(
                owner, mint_in, mint_out, amount, quoted=int(q["outAmount"]), slippage=int(q["slippageBps"])
            )
        )
        tx = make_tx(ixs, owner)
        return {"swapTransaction": tx_b64(tx), "lastValidBlockHeight": 1200, "simulationError": None}

    http.on("/swap/v1/quote", quote)
    http.on("/swap/v1/swap", swap)
    http.on("/price/v3", PRICES)
    return http


def make_engine(cfg: Config, chain: FakeRpc, http: FakeHttp, clock=None) -> Engine:
    jup = Jupiter(cfg.jupiter_base_url, http, min_gap_s=0)
    t = {"now": 1_800_000_000.0}

    def tick():
        t["now"] += 0.5
        return t["now"]

    return Engine(cfg, http=http, rpc=chain, jup=jup, clock=clock or tick, sleep=lambda s: None)


@pytest.fixture
def ctx_factory(monkeypatch):
    """Install a registry context factory built from a given cfg/engine."""

    def install(cfg: Config, engine: Engine):
        monkeypatch.setattr(registry, "CONTEXT_FACTORY", lambda: registry.Context(cfg, engine))

    return install
