"""Builds and runs the rebalance transaction sequence.

Sequence (one stage at a time; later stages are sized from the real results of earlier ones):
  A. unstake      gauge.withdraw(tokenId)                     (only if staked; claims AERO to owner)
  B. remove       npm.multicall([decreaseLiquidity, collect, burn])
  C. swap         approve(tokenIn -> SwapRouter), exactInputSingle on the same pool
  D. mint         approve(token0/1 -> NPM), npm.mint(new range)
  E. stake        npm.approve(gauge, newId), gauge.deposit(newId)   (only for AERO-reward mode)

Two runners execute stages:
  SimRunner  - eth_simulateV1 on live Base state, no signatures, nothing broadcast (dry run).
  LiveRunner - signs locally and broadcasts; simulates every tx with eth_estimateGas first.

The bot only ever spends tokens that came out of the position being rebalanced: amounts are
measured as wallet balance deltas from the start of the rebalance.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from eth_account.signers.local import LocalAccount
from hexbytes import HexBytes
from web3 import Web3

from . import abi, addresses, clmath
from .chain import AeroChain, PositionState
from .strategy import Range

T = TypeVar("T")

UINT128_MAX = (1 << 128) - 1
TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)")


@dataclass(frozen=True)
class ExecConfig:
    max_slippage_bps: float = 50.0
    max_priority_fee_gwei: float = 0.001  # stay under Slipstream's MEV-capture priority-fee threshold
    deadline_s: int = 600
    min_swap_usd: float = 1.0
    receipt_timeout_s: int = 180
    # Abort before the first swap when spot has moved more than this since the pre-send check
    # (1 tick ~= 1 bp). Swap/mint min-amounts are anchored to the post-remove spot, so an
    # attacker pushing the price between the TWAP check and the swap would otherwise pass.
    max_stage_drift_bps: float = 100.0

    def __post_init__(self) -> None:
        # A slippage of 100% (10_000 bps) makes every min-out zero, i.e. no protection at all.
        if not 0 <= self.max_slippage_bps < 10_000:
            raise ValueError("max_slippage_bps must be in [0, 10000)")
        if self.max_priority_fee_gwei < 0 or self.min_swap_usd < 0:
            raise ValueError("max_priority_fee_gwei and min_swap_usd must be >= 0")
        if self.deadline_s <= 0 or self.receipt_timeout_s <= 0:
            raise ValueError("deadline_s and receipt_timeout_s must be > 0")
        if self.max_stage_drift_bps <= 0:
            raise ValueError("max_stage_drift_bps must be > 0")


@dataclass
class PlannedTx:
    label: str
    to: str
    data: str
    value: int = 0


@dataclass
class StageResult:
    logs: list[dict[str, Any]]
    balances: dict[str, int]
    tx_hashes: list[str] = field(default_factory=list)
    sqrt_price_x96: int = 0  # pool price after the stage (0 if no pool configured)


class Runner(Protocol):
    def execute(self, txs: list[PlannedTx]) -> StageResult: ...
    def block_timestamp(self) -> int: ...


def _hex(b: bytes | str) -> str:
    return b if isinstance(b, str) else "0x" + bytes(b).hex()


class SimRunner:
    """Accumulates every tx and re-simulates the whole sequence with eth_simulateV1 at each stage."""

    def __init__(self, chain: AeroChain, owner: str, tokens: list[str], pool: str | None = None):
        self.chain, self.owner, self.tokens, self.pool = chain, Web3.to_checksum_address(owner), tokens, pool
        self.history: list[PlannedTx] = []
        self.base_block = chain.head()[0]
        self._ts = int(chain.w3.eth.get_block(self.base_block)["timestamp"])
        self.gas_used: dict[str, int] = {}

    def block_timestamp(self) -> int:
        return self._ts + 2

    def execute(self, txs: list[PlannedTx]) -> StageResult:
        erc20 = self.chain.w3.eth.contract(abi=abi.ERC20)
        probes = [
            {"from": self.owner, "to": t, "data": erc20.encode_abi("balanceOf", args=[self.owner])} for t in self.tokens
        ]
        if self.pool:
            pc = self.chain.w3.eth.contract(abi=abi.CL_POOL)
            probes.append({"from": self.owner, "to": self.pool, "data": pc.encode_abi("slot0")})
        calls = [
            {"from": self.owner, "to": tx.to, "data": tx.data, "value": hex(tx.value)} for tx in self.history + txs
        ] + probes
        params = [{"blockStateCalls": [{"calls": calls}], "validation": False}, hex(self.base_block)]
        res = self.chain.w3.provider.make_request("eth_simulateV1", params)  # type: ignore[arg-type]
        if "error" in res:
            raise RuntimeError(f"eth_simulateV1 error: {res['error']}")
        out = res["result"][0]["calls"]
        n_hist = len(self.history)
        for i, tx in enumerate(txs):
            r = out[n_hist + i]
            if int(r["status"], 16) != 1:
                err = r.get("error") or {}
                raise RuntimeError(f"simulated tx '{tx.label}' reverted: {err.get('message') or err}")
            self.gas_used[tx.label] = int(r.get("gasUsed", "0x0"), 16)
        logs = [lg for r in out[n_hist : n_hist + len(txs)] for lg in r.get("logs", [])]
        first_probe = len(calls) - len(probes)
        bals = {t: int(out[first_probe + j]["returnData"], 16) for j, t in enumerate(self.tokens)}
        sqrt_p = int(out[-1]["returnData"][2:66], 16) if self.pool else 0
        self.history.extend(txs)
        return StageResult(logs, bals, sqrt_price_x96=sqrt_p)


class LiveRunner:
    """Signs and broadcasts. Every tx is gas-estimated (a full simulation) before it is signed."""

    READ_RETRIES = 8
    READ_RETRY_DELAY_S = 1.5

    def __init__(
        self, chain: AeroChain, account: LocalAccount, tokens: list[str], cfg: ExecConfig, pool: str | None = None
    ):
        self.chain, self.acct, self.tokens, self.cfg, self.pool = chain, account, tokens, cfg, pool
        self.w3 = chain.w3
        self.gas_used: dict[str, int] = {}
        # Every hash broadcast so far, appended before waiting for the receipt, so a timeout or revert
        # still leaves the hash on record (see RebalanceError).
        self.sent_hashes: list[str] = []
        self._next_nonce: int | None = None

    def block_timestamp(self) -> int:
        return int(self.w3.eth.get_block("latest")["timestamp"])

    def _read_at(self, block: int | str, read: Callable[[int | str], T]) -> T:
        """Run `read(block)`, retrying while the RPC node has not yet imported `block`.

        Public RPC endpoints are load-balanced: a call made right after a receipt can hit a node one block
        behind and return the pre-transaction balances. Pinning to the receipt's block and retrying makes
        a lagging node an error instead of silently stale data that the next stage would be sized from.
        """
        last: Exception | None = None
        tries = 1 if block == "latest" else self.READ_RETRIES
        for attempt in range(tries):
            try:
                return read(block)
            except Exception as e:  # noqa: BLE001 - node behind the receipt block: wait and retry
                last = e
                if attempt + 1 < tries:
                    time.sleep(self.READ_RETRY_DELAY_S)
        raise RuntimeError(f"RPC could not serve state at block {block}: {last}") from last

    def _nonce(self) -> int:
        """Next nonce: the node's pending count, but never below what this runner already used (a lagging
        node can report a stale, lower count right after our previous transaction)."""
        pending = int(self.w3.eth.get_transaction_count(self.acct.address, "pending"))
        return pending if self._next_nonce is None else max(pending, self._next_nonce)

    def _estimate_gas(self, req: dict[str, Any]) -> int:
        """eth_estimateGas, retried briefly: on a lagging node it reverts because the previous stage's state
        (e.g. the approval) is not there yet. A genuine revert still surfaces after the retries."""
        for attempt in range(3):
            try:
                return int(self.w3.eth.estimate_gas(req))
            except Exception:  # noqa: BLE001
                if attempt == 2:
                    raise
                time.sleep(self.READ_RETRY_DELAY_S)
        raise AssertionError("unreachable")

    def _visible(self, tx_hash: HexBytes) -> bool:
        try:
            return self.w3.eth.get_transaction(tx_hash) is not None
        except Exception:  # noqa: BLE001 - not found (or node error): treat as not broadcast
            return False

    def _fees(self) -> tuple[int, int]:
        base = int(self.w3.eth.get_block("latest").get("baseFeePerGas", 0))
        cap = int(self.cfg.max_priority_fee_gwei * 1e9)
        try:
            prio = min(int(self.w3.eth.max_priority_fee), cap)
        except Exception:  # noqa: BLE001
            prio = cap
        return base * 2 + prio, prio

    def execute(self, txs: list[PlannedTx]) -> StageResult:
        logs: list[dict[str, Any]] = []
        hashes: list[str] = []
        block: int | str = "latest"
        for tx in txs:
            max_fee, prio = self._fees()
            req: dict[str, Any] = {
                "from": self.acct.address,
                "to": Web3.to_checksum_address(tx.to),
                "data": tx.data,
                "value": tx.value,
                "chainId": addresses.BASE_CHAIN_ID,
                "nonce": self._nonce(),
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": prio,
                "type": 2,
            }
            req["gas"] = int(self._estimate_gas(req) * 1.25)  # reverts here if the tx would fail
            self._next_nonce = req["nonce"] + 1
            signed = self.acct.sign_transaction(req)
            h = HexBytes(signed.hash)
            # Recorded before broadcasting: the RPC layer retries transport errors, so a send that raises may
            # still have reached the mempool, and the hash is then the only handle on that transaction.
            self.sent_hashes.append(_hex(h))
            try:
                self.w3.eth.send_raw_transaction(signed.raw_transaction)
            except Exception:
                # A retry after the node already accepted the first attempt fails ("already known",
                # "nonce too low"). Carry on to the receipt only if the node can show the transaction.
                if not self._visible(h):
                    raise
            rcpt = self.w3.eth.wait_for_transaction_receipt(h, timeout=self.cfg.receipt_timeout_s)
            if rcpt["status"] != 1:
                raise RuntimeError(f"tx '{tx.label}' reverted: {_hex(h)}")
            self.gas_used[tx.label] = int(rcpt["gasUsed"])
            hashes.append(_hex(h))
            block = int(rcpt["blockNumber"])
            logs.extend(
                {"address": lg["address"], "topics": [_hex(t) for t in lg["topics"]], "data": _hex(lg["data"])}
                for lg in rcpt["logs"]
            )
        # Read the post-stage state at the last receipt's block, never at a possibly lagging "latest".
        bals = dict(
            zip(
                self.tokens,
                self._read_at(block, lambda b: self.chain.erc20_balances(self.acct.address, self.tokens, block=b)),
                strict=True,
            )
        )
        sqrt_p = 0
        if self.pool:
            pc = self.chain._c(self.pool, abi.CL_POOL)
            sqrt_p = int(self._read_at(block, lambda b: pc.functions.slot0().call(block_identifier=b))[0])
        return StageResult(logs, bals, hashes, sqrt_p)


@dataclass
class RebalanceResult:
    new_token_id: int | None
    staked: bool
    stages: list[str]
    tx_hashes: list[str]
    gas_used: dict[str, int]
    amounts_in_position: tuple[int, int] = (0, 0)
    aero_claimed: int = 0
    notes: list[str] = field(default_factory=list)


class RebalanceError(RuntimeError):
    """A rebalance failed part-way. `partial` holds what had already happened on chain.

    Once the old NFT is burned the funds sit in the wallet and a minted-but-unstaked NFT is a new token id
    the caller must start tracking, so the caller needs the completed stages, the broadcast hashes and the
    new token id, not just the error text.
    """

    def __init__(self, message: str, partial: RebalanceResult):
        super().__init__(message)
        self.partial = partial


StageHook = Callable[[str, "RebalanceResult"], None]


class Rebalancer:
    def __init__(self, chain: AeroChain, owner: str, cfg: ExecConfig):
        self.chain, self.owner, self.cfg = chain, Web3.to_checksum_address(owner), cfg
        self.npm = chain.npm
        self.router = chain._c(addresses.SWAP_ROUTER, abi.SWAP_ROUTER)
        self.erc20 = chain.w3.eth.contract(abi=abi.ERC20)

    # -------------------------------------------------------------- calldata builders

    def _approve(self, token: str, spender: str, amount: int) -> PlannedTx:
        return PlannedTx(
            f"approve {token[:8]}->{spender[:8]}", token, self.erc20.encode_abi("approve", args=[spender, amount])
        )

    def remove_calls(self, pos: PositionState, deadline: int, slip: float) -> PlannedTx:
        sa, sb = clmath.get_sqrt_ratio_at_tick(pos.tick_lower), clmath.get_sqrt_ratio_at_tick(pos.tick_upper)
        e0, e1 = clmath.get_amounts_for_liquidity(pos.pool.sqrt_price_x96, sa, sb, pos.liquidity)
        inner = []
        if pos.liquidity > 0:
            inner.append(
                self.npm.encode_abi(
                    "decreaseLiquidity",
                    args=[(pos.token_id, pos.liquidity, int(e0 * (1 - slip)), int(e1 * (1 - slip)), deadline)],
                )
            )
        inner.append(self.npm.encode_abi("collect", args=[(pos.token_id, self.owner, UINT128_MAX, UINT128_MAX)]))
        inner.append(self.npm.encode_abi("burn", args=[pos.token_id]))
        return PlannedTx(
            "remove liquidity + collect + burn",
            self.npm.address,
            self.npm.encode_abi("multicall", args=[[HexBytes(x) for x in inner]]),
        )

    # -------------------------------------------------------------- the sequence

    def rebalance(
        self,
        pos: PositionState,
        new: Range,
        stake_new: bool,
        runner: Runner,
        usd0: float,
        usd1: float,
        on_stage: StageHook | None = None,
    ) -> RebalanceResult:
        """Run the whole sequence. Any failure is re-raised as RebalanceError carrying the partial result.

        `on_stage(stage, partial_result)` runs after every completed stage (e.g. to persist the new token id
        the moment the mint lands); an exception from it aborts the sequence like any other failure.
        """
        res = RebalanceResult(None, False, [], [], {})
        try:
            return self._run(pos, new, stake_new, runner, usd0, usd1, res, on_stage or (lambda stage, r: None))
        except Exception as e:
            res.tx_hashes = list(getattr(runner, "sent_hashes", None) or res.tx_hashes)
            res.gas_used = dict(getattr(runner, "gas_used", {}))
            where = res.stages[-1] if res.stages else "start"
            raise RebalanceError(f"rebalance failed after stage '{where}': {e}", res) from e

    def _run(
        self,
        pos: PositionState,
        new: Range,
        stake_new: bool,
        runner: Runner,
        usd0: float,
        usd1: float,
        res: RebalanceResult,
        on_stage: StageHook,
    ) -> RebalanceResult:
        pool = pos.pool
        t0, t1 = pool.token0.address, pool.token1.address
        slip = self.cfg.max_slippage_bps / 1e4
        start = dict(
            zip(runner_tokens(t0, t1), self.chain.erc20_balances(self.owner, runner_tokens(t0, t1)), strict=True)
        )

        def deadline() -> int:
            # Fresh per stage: on the live runner a slow earlier stage must not leave a later one with an
            # expired deadline after the old NFT is already burned.
            return runner.block_timestamp() + self.cfg.deadline_s

        if pos.staked:
            g = self.chain.gauge_contract(pool.gauge)
            r = runner.execute([PlannedTx("gauge.withdraw", g.address, g.encode_abi("withdraw", args=[pos.token_id]))])
            res.stages.append("unstake")
            res.tx_hashes += r.tx_hashes
            res.aero_claimed = r.balances[addresses.AERO_TOKEN] - start[addresses.AERO_TOKEN]
            on_stage("unstake", res)

        r = runner.execute([self.remove_calls(pos, deadline(), slip)])
        res.stages.append("remove")
        res.tx_hashes += r.tx_hashes
        got0, got1 = max(0, r.balances[t0] - start[t0]), max(0, r.balances[t1] - start[t1])
        if t0 == addresses.AERO_TOKEN or t1 == addresses.AERO_TOKEN:
            res.notes.append("pool contains AERO: claimed AERO is included in the redeposit")
        on_stage("remove", res)
        if r.sqrt_price_x96:
            drift = abs(clmath_tick(r.sqrt_price_x96) - pool.tick)
            if drift > self.cfg.max_stage_drift_bps:
                raise RuntimeError(
                    f"spot moved {drift} ticks since the pre-send check (> {self.cfg.max_stage_drift_bps}); "
                    "not swapping into a possibly manipulated price. Tokens are in the wallet."
                )

        # Swap toward the new range's value ratio. Our own swap moves the price, so after the first
        # pass we recompute at the post-swap price and do one small corrective pass if still off.
        sp = r.sqrt_price_x96 or pool.sqrt_price_x96
        avail0, avail1 = got0, got1
        value_usd = got0 / 10**pool.token0.decimals * usd0 + got1 / 10**pool.token1.decimals * usd1
        for attempt in range(2):
            raw_p = clmath.sqrtx96_to_price(sp)
            frac0 = clmath.value0_fraction(
                raw_p, clmath.price_from_tick(new.tick_lower), clmath.price_from_tick(new.tick_upper)
            )
            direction, amt = clmath.swap_to_ratio(avail0, avail1, raw_p, frac0, pool.fee)
            amt_i = int(amt)
            dec_in, usd_in = (pool.token0.decimals, usd0) if direction == 0 else (pool.token1.decimals, usd1)
            swap_usd = amt_i / 10**dec_in * usd_in
            threshold = self.cfg.min_swap_usd if attempt == 0 else max(self.cfg.min_swap_usd, 0.0025 * value_usd)
            if amt_i <= 0 or swap_usd < threshold:
                break
            t_in, t_out = (t0, t1) if direction == 0 else (t1, t0)
            expected_out = amt_i * raw_p * (1 - pool.fee) if direction == 0 else amt_i / raw_p * (1 - pool.fee)
            min_out = int(expected_out * (1 - slip))
            params = (t_in, t_out, pool.tick_spacing, self.owner, deadline(), amt_i, min_out, 0)
            r = runner.execute(
                [
                    self._approve(t_in, self.router.address, amt_i),
                    PlannedTx(
                        f"swap#{attempt + 1} {amt_i} {'0->1' if direction == 0 else '1->0'}",
                        self.router.address,
                        self.router.encode_abi("exactInputSingle", args=[params]),
                    ),
                ]
            )
            res.stages.append("swap")
            res.tx_hashes += r.tx_hashes
            on_stage("swap", res)
            avail0, avail1 = max(0, r.balances[t0] - start[t0]), max(0, r.balances[t1] - start[t1])
            sp = r.sqrt_price_x96 or sp
        sp_now = sp
        if not new.contains(clmath_tick(sp_now)):
            res.notes.append("price left the target range during the swap; mint will be single-sided")

        sa, sb = clmath.get_sqrt_ratio_at_tick(new.tick_lower), clmath.get_sqrt_ratio_at_tick(new.tick_upper)
        liq = clmath.get_liquidity_for_amounts(sp_now, sa, sb, avail0, avail1)
        if liq <= 0:
            raise RuntimeError(f"nothing to mint: {avail0} token0 + {avail1} token1 give zero liquidity")
        e0, e1 = clmath.get_amounts_for_liquidity(sp_now, sa, sb, liq)
        mint = (
            t0,
            t1,
            pool.tick_spacing,
            new.tick_lower,
            new.tick_upper,
            avail0,
            avail1,
            int(e0 * (1 - slip)),
            int(e1 * (1 - slip)),
            self.owner,
            deadline(),
            0,
        )
        r = runner.execute(
            [
                self._approve(t0, self.npm.address, avail0),
                self._approve(t1, self.npm.address, avail1),
                PlannedTx(
                    f"mint [{new.tick_lower},{new.tick_upper})",
                    self.npm.address,
                    self.npm.encode_abi("mint", args=[mint]),
                ),
            ]
        )
        res.stages.append("mint")
        res.tx_hashes += r.tx_hashes
        res.new_token_id = minted_token_id(r.logs, self.npm.address, self.owner)
        res.amounts_in_position = (avail0 - (r.balances[t0] - start[t0]), avail1 - (r.balances[t1] - start[t1]))
        if res.new_token_id is None:
            raise RuntimeError("mint succeeded but no Transfer(0x0 -> owner) log found")
        on_stage("mint", res)

        if stake_new and pool.gauge_alive:
            g = self.chain.gauge_contract(pool.gauge)
            r = runner.execute(
                [
                    PlannedTx(
                        "npm.approve(gauge)",
                        self.npm.address,
                        self.npm.encode_abi("approve", args=[g.address, res.new_token_id]),
                    ),
                    PlannedTx("gauge.deposit", g.address, g.encode_abi("deposit", args=[res.new_token_id])),
                ]
            )
            res.stages.append("stake")
            res.tx_hashes += r.tx_hashes
            res.staked = True
            on_stage("stake", res)
        elif stake_new:
            res.notes.append("gauge not activated: left the new deposit unstaked (earning fees)")
        res.gas_used = dict(getattr(runner, "gas_used", {}))
        return res


def clmath_tick(sqrt_price_x96: int) -> int:
    return int(clmath.tick_from_price(clmath.sqrtx96_to_price(sqrt_price_x96)) // 1)


def runner_tokens(t0: str, t1: str) -> list[str]:
    out = [Web3.to_checksum_address(t0), Web3.to_checksum_address(t1)]
    if addresses.AERO_TOKEN not in out:
        out.append(addresses.AERO_TOKEN)
    return out


def minted_token_id(logs: list[dict[str, Any]], npm: str, owner: str) -> int | None:
    topic0 = _hex(TRANSFER_TOPIC).lower()
    zero = "0x" + "0" * 64
    owner_t = "0x" + "0" * 24 + owner.lower()[2:]
    for lg in logs:
        topics = [t.lower() if isinstance(t, str) else _hex(t).lower() for t in lg["topics"]]
        if (
            str(lg["address"]).lower() == npm.lower()
            and len(topics) == 4
            and topics[0] == topic0
            and topics[1] == zero
            and topics[2] == owner_t
        ):
            return int(topics[3], 16)
    return None


def gas_cost_usd(gas_units: int, gas_price_wei: int, eth_usd: float, l1_fee_usd: float = 0.0) -> float:
    return gas_units * gas_price_wei / 1e18 * eth_usd + l1_fee_usd


def now() -> float:
    return time.time()


def fmt_amount(raw: int, decimals: int) -> str:
    v = raw / 10**decimals
    return f"{v:.6g}" if abs(v) < 1e6 else f"{v:,.0f}"
