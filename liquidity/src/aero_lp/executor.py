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
measured from token transfers in this operation's confirmed transaction receipts.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from eth_account.signers.local import LocalAccount
from hexbytes import HexBytes
from web3 import Web3

from . import abi, addresses, clmath
from .chain import AeroChain, PoolState, PositionState
from .strategy import Range
from .submissions import PendingSubmission, SubmissionJournal
from .validation import finite_number

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
        for name in ("max_slippage_bps", "max_priority_fee_gwei", "min_swap_usd", "max_stage_drift_bps"):
            finite_number(getattr(self, name), name, positive=name == "max_stage_drift_bps")
        for name in ("deadline_s", "receipt_timeout_s"):
            finite_number(getattr(self, name), name, positive=True, integer=True)
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
class ConfirmedTx:
    tx: PlannedTx
    logs: list[dict[str, Any]]


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


def token_delta(logs: list[dict[str, Any]], token: str, owner: str) -> int:
    """Net ERC20 transfers in these receipts only; unrelated block transfers cannot enter a budget."""
    delta = 0
    owner_topic = "0x" + "0" * 24 + owner.lower()[2:]
    for lg in logs:
        topics = [_hex(t).lower() for t in lg["topics"]]
        if str(lg["address"]).lower() != token.lower() or len(topics) != 3:
            continue
        if topics[0] != _hex(TRANSFER_TOPIC).lower():
            continue
        data = HexBytes(lg["data"])
        if len(data) != 32:
            raise RuntimeError("malformed ERC20 Transfer receipt")
        amount = int.from_bytes(data)
        delta += amount * ((topics[2] == owner_topic) - (topics[1] == owner_topic))
    return delta


def increased_amounts(logs: list[dict[str, Any]], npm: str, token_id: int) -> tuple[int, int]:
    topic = _hex(Web3.keccak(text="IncreaseLiquidity(uint256,uint128,uint256,uint256)")).lower()
    matches = []
    for lg in logs:
        topics = [_hex(t).lower() for t in lg["topics"]]
        if (
            str(lg["address"]).lower() == npm.lower()
            and len(topics) == 2
            and topics[0] == topic
            and int(topics[1], 16) == token_id
        ):
            data = HexBytes(lg["data"])
            if len(data) != 96:
                raise RuntimeError("malformed IncreaseLiquidity receipt")
            matches.append((int.from_bytes(data[32:64]), int.from_bytes(data[64:96])))
    if len(matches) != 1:
        raise RuntimeError("confirmed IncreaseLiquidity receipt missing or ambiguous")
    return matches[0]


class SimRunner:
    """Accumulates every tx and re-simulates the whole sequence with eth_simulateV1 at each stage."""

    def __init__(self, chain: AeroChain, owner: str, tokens: list[str], pool: str | None = None):
        self.chain, self.owner, self.tokens, self.pool = chain, Web3.to_checksum_address(owner), tokens, pool
        self.history: list[PlannedTx] = []
        self.confirmed: list[ConfirmedTx] = []
        self.logs: list[dict[str, Any]] = []
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
            try:
                raw_gas = r["gasUsed"]
                if not isinstance(raw_gas, str) or not raw_gas.startswith("0x"):
                    raise ValueError("gasUsed must be an RPC hex quantity")
                gas = int(raw_gas, 16)
                finite_number(gas, "simulated gas", positive=True, integer=True)
            except (KeyError, TypeError, ValueError) as error:
                raise RuntimeError(f"simulated tx '{tx.label}' has invalid or missing gas evidence") from error
            self.gas_used[tx.label] = self.gas_used.get(tx.label, 0) + gas
        logs = [lg for r in out[n_hist : n_hist + len(txs)] for lg in r.get("logs", [])]
        first_probe = len(calls) - len(probes)
        bals = {t: int(out[first_probe + j]["returnData"], 16) for j, t in enumerate(self.tokens)}
        sqrt_p = int(out[-1]["returnData"][2:66], 16) if self.pool else 0
        self.history.extend(txs)
        self.logs.extend(logs)
        self.confirmed.extend(ConfirmedTx(tx, out[n_hist + i].get("logs", [])) for i, tx in enumerate(txs))
        return StageResult(logs, bals, sqrt_price_x96=sqrt_p)


class LiveRunner:
    """Signs and broadcasts. Every tx is gas-estimated (a full simulation) before it is signed."""

    READ_RETRIES = 8
    READ_RETRY_DELAY_S = 1.5

    def __init__(
        self,
        chain: AeroChain,
        account: LocalAccount,
        tokens: list[str],
        cfg: ExecConfig,
        pool: str | None = None,
        *,
        journal: SubmissionJournal | None = None,
    ):
        self.chain, self.acct, self.tokens, self.cfg, self.pool = chain, account, tokens, cfg, pool
        self.w3 = chain.w3
        self.journal = journal
        self.group = uuid.uuid4().hex
        self._uncertain = False
        self._lease = None
        self.gas_used: dict[str, int] = {}
        # Every hash broadcast so far, appended before waiting for the receipt, so a timeout or revert
        # still leaves the hash on record (see RebalanceError).
        self.sent_hashes: list[str] = []
        self._next_nonce: int | None = None
        self.fee_wei = 0  # execution + L1 data fee actually paid, summed over every receipt
        # Every log of every receipt so far, kept even if a later read fails, so a minted NFT's id is not lost.
        self.logs: list[dict[str, Any]] = []
        self.confirmed: list[ConfirmedTx] = []

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

    def finish_submission(self) -> None:
        if self._lease is not None:
            self._lease.close()
            self._lease = None

    def execute(self, txs: list[PlannedTx]) -> StageResult:
        if txs:
            if self.journal is None:
                raise RuntimeError("a durable submission journal is required before live writes")
            if self._lease is None:
                self._lease = self.journal.acquire()
        try:
            return self._execute(txs)
        except BaseException:
            self.finish_submission()
            raise

    def _execute(self, txs: list[PlannedTx]) -> StageResult:
        logs: list[dict[str, Any]] = []
        hashes: list[str] = []
        block: int | str = "latest"
        for tx in txs:
            if self.journal is None:
                raise RuntimeError("a durable submission journal is required before live writes")
            if self.journal.owner.lower() != self.acct.address.lower():
                raise PendingSubmission("submission journal owner does not match the signer")
            if self._uncertain:
                raise PendingSubmission(
                    "this runner has an unresolved submitted outcome; reconcile before any new write"
                )
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
            signed = self.acct.sign_transaction(req)
            h = HexBytes(signed.hash)
            # Recorded before broadcasting: the RPC layer retries transport errors, so a send that raises may
            # still have reached the mempool, and the hash is then the only handle on that transaction.
            self._uncertain = True
            self.journal.before_submit(_hex(h), req["nonce"], tx, self.group, self.pool, self.tokens)
            self._next_nonce = req["nonce"] + 1
            self.sent_hashes.append(_hex(h))
            self._uncertain = True
            try:
                self.w3.eth.send_raw_transaction(signed.raw_transaction)
            except Exception:
                # A retry after the node already accepted the first attempt fails ("already known",
                # "nonce too low"). Carry on to the receipt only if the node can show the transaction.
                if not self._visible(h):
                    raise
            rcpt = self.w3.eth.wait_for_transaction_receipt(h, timeout=self.cfg.receipt_timeout_s)
            self.journal.receipt(_hex(h), rcpt)
            self._uncertain = False
            self.fee_wei += receipt_fee_wei(rcpt)  # a reverted transaction still paid for its gas
            if rcpt["status"] != 1:
                raise RuntimeError(f"tx '{tx.label}' reverted: {_hex(h)}")
            self.gas_used[tx.label] = self.gas_used.get(tx.label, 0) + int(rcpt["gasUsed"])
            hashes.append(_hex(h))
            block = int(rcpt["blockNumber"])
            self.chain.min_block = max(getattr(self.chain, "min_block", None) or 0, block)
            new_logs = [
                {"address": lg["address"], "topics": [_hex(t) for t in lg["topics"]], "data": _hex(lg["data"])}
                for lg in rcpt["logs"]
            ]
            logs.extend(new_logs)
            self.logs.extend(new_logs)
            self.confirmed.append(ConfirmedTx(tx, new_logs))
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
    fee_wei: int = 0  # gas actually paid (live runner only)
    amount_out: int = 0  # swap_exact: output token received, measured from the runner's balances


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
            self._finish(res, runner)  # gas paid before the failure still belongs in the P&L
            self._recover_mint(res, runner)
            where = res.stages[-1] if res.stages else "start"
            raise RebalanceError(f"rebalance failed after stage '{where}': {e}", res) from e
        finally:
            if hasattr(runner, "finish_submission"):
                runner.finish_submission()

    def _exit(
        self,
        pos: PositionState,
        runner: Runner,
        res: RebalanceResult,
        start: dict[str, int],
        deadline: Callable[[], int],
        slip: float,
        on_stage: StageHook,
    ) -> StageResult:
        """Unstake (if staked) and remove all liquidity + collect + burn. Shared by rebalance and withdraw."""
        exit_logs: list[dict[str, Any]] = []
        if pos.staked:
            g = self.chain.gauge_contract(pos.pool.gauge)
            r = runner.execute([PlannedTx("gauge.withdraw", g.address, g.encode_abi("withdraw", args=[pos.token_id]))])
            res.stages.append("unstake")
            res.tx_hashes += r.tx_hashes
            exit_logs.extend(r.logs)
            res.aero_claimed = token_delta(r.logs, addresses.AERO_TOKEN, self.owner)
            if res.aero_claimed <= 0 and pos.earned_aero > 0:
                res.notes.append(
                    "no AERO arrived on unstake although some had accrued: the gauge either applied the early-exit "
                    "penalty or deferred the reward (check gauge.deferredEmissions(owner))"
                )
            on_stage("unstake", res)
        r = runner.execute([self.remove_calls(pos, deadline(), slip)])
        res.stages.append("remove")
        res.tx_hashes += r.tx_hashes
        on_stage("remove", res)
        r.logs = exit_logs + r.logs
        if pos.liquidity > 0 and not any(
            token_delta(r.logs, t, self.owner) > 0 for t in (pos.pool.token0.address, pos.pool.token1.address)
        ):
            raise RuntimeError("remove receipt has no token proceeds; refusing to infer funds from wallet balances")
        return r

    def withdraw(self, pos: PositionState, runner: Runner, on_stage: StageHook | None = None) -> RebalanceResult:
        """Exit the position to the wallet: unstake, remove all liquidity, collect fees, burn the empty NFT.

        `amounts_in_position` holds the token0/token1 amounts *received* by the wallet.
        """
        res = RebalanceResult(None, False, [], [], {})
        hook = on_stage or (lambda stage, r: None)
        t0, t1 = pos.pool.token0.address, pos.pool.token1.address
        try:
            start = runner.execute([]).balances
            r = self._exit(
                pos,
                runner,
                res,
                start,
                lambda: runner.block_timestamp() + self.cfg.deadline_s,
                self.cfg.max_slippage_bps / 1e4,
                hook,
            )
            res.amounts_in_position = (token_delta(r.logs, t0, self.owner), token_delta(r.logs, t1, self.owner))
            self._finish(res, runner)
            return res
        except Exception as e:
            res.tx_hashes = list(getattr(runner, "sent_hashes", None) or res.tx_hashes)
            self._finish(res, runner)
            self._recover_confirmed(res, runner)
            if "remove" in res.stages:
                receipts = [lg for record in getattr(runner, "confirmed", ()) for lg in record.logs]
                res.amounts_in_position = (token_delta(receipts, t0, self.owner), token_delta(receipts, t1, self.owner))
            where = res.stages[-1] if res.stages else "start"
            raise RebalanceError(f"withdraw failed after stage '{where}': {e}", res) from e
        finally:
            if hasattr(runner, "finish_submission"):
                runner.finish_submission()

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
        start = runner.execute([]).balances

        def deadline() -> int:
            # Fresh per stage: on the live runner a slow earlier stage must not leave a later one with an
            # expired deadline after the old NFT is already burned.
            return runner.block_timestamp() + self.cfg.deadline_s

        r = self._exit(pos, runner, res, start, deadline, slip, on_stage)
        got0, got1 = (
            min(max(0, token_delta(r.logs, t, self.owner)), max(0, r.balances[t] - start[t])) for t in (t0, t1)
        )
        if t0 == addresses.AERO_TOKEN or t1 == addresses.AERO_TOKEN:
            res.notes.append("pool contains AERO: claimed AERO is included in the redeposit")
        self._check_drift(pool, r.sqrt_price_x96)

        sp = r.sqrt_price_x96 or pool.sqrt_price_x96

        funds = [got0, got1]

        def avail(r: StageResult) -> tuple[int, int]:
            return self._available(funds, (t0, t1), r, start, (0, 0))

        avail0, avail1, sp_now = self._ratio_swap_loop(
            pos.pool, new, runner, res, on_stage, avail, got0, got1, sp, usd0, usd1, deadline, slip
        )
        self._mint_and_stake(
            pos.pool, new, stake_new, runner, res, on_stage, start, avail0, avail1, sp_now, deadline, slip
        )
        self._finish(res, runner)
        return res

    # -------------------------------------------------------------- shared building blocks

    def _check_drift(self, pool: PoolState, sqrt_price: int) -> None:
        if not sqrt_price:
            raise RuntimeError("post-stage pool price unavailable")
        drift = abs(clmath_tick(sqrt_price) - pool.tick)
        if drift > self.cfg.max_stage_drift_bps:
            raise RuntimeError(
                f"spot moved {drift} ticks since the pre-send check (> {self.cfg.max_stage_drift_bps}); "
                "not swapping into a possibly manipulated price. Tokens are in the wallet."
            )

    def _available(
        self,
        funds: list[int],
        tokens: tuple[str, str],
        r: StageResult,
        start: dict[str, int],
        designated: tuple[int, int],
    ) -> tuple[int, int]:
        for i, t in enumerate(tokens):
            funds[i] += token_delta(r.logs, t, self.owner)
            if funds[i] < 0:
                raise RuntimeError("receipt spent more than this operation's token budget")
            funds[i] = min(funds[i], max(0, designated[i] + r.balances[t] - start[t]))
        return funds[0], funds[1]

    def _recover_amounts(self, res: RebalanceResult, logs: list[dict[str, Any]], token_id: int) -> None:
        try:
            res.amounts_in_position = increased_amounts(logs, self.npm.address, token_id)
        except RuntimeError as error:
            res.notes.append(f"confirmed NFT #{token_id}: deposited amounts unknown ({error}); no estimate substituted")

    def _recover_confirmed(self, res: RebalanceResult, runner: Runner) -> None:
        """Recover committed outcomes before a later state read or stage hook failed."""
        records = getattr(runner, "confirmed", ())
        stages = []
        for record in records:
            label, logs = record.tx.label, record.logs
            stage = None
            if label == "gauge.withdraw":
                stage, res.staked = "unstake", False
                res.aero_claimed = token_delta(logs, addresses.AERO_TOKEN, self.owner)
            elif label.startswith("remove"):
                stage = "remove"
            elif label.startswith("mint"):
                tid = minted_token_id(logs, self.npm.address, self.owner)
                if tid is not None:
                    res.new_token_id = tid
                    self._recover_amounts(res, logs, tid)
                    stage = "mint"
            elif label == "increaseLiquidity":
                params = self.npm.decode_function_input(record.tx.data)[1]["params"]
                self._recover_amounts(res, logs, params["tokenId"])
                stage = "increase"
            elif label == "gauge.deposit":
                stage, res.staked = "stake", True
            elif label.startswith("swap"):
                stage = "swap"
            elif label == "gauge.claimEmissions":
                stage = "claim"
                res.aero_claimed = token_delta(logs, addresses.AERO_TOKEN, self.owner)
            elif label == "collect":
                stage = "collect"
            elif label == "weth.withdraw":
                stage = "unwrap"
            elif label.startswith("router multicall:"):
                stage = "swap_to_eth"
            if stage:
                stages.append(stage)
        if stages:
            res.stages = stages

    def _recover_mint(self, res: RebalanceResult, runner: Runner) -> None:
        """If a mint receipt arrived but a later read failed, the stage never reported the new NFT. Its id is in the
        runner's logs; without it the position would sit in the wallet untracked."""
        before = res.new_token_id
        self._recover_confirmed(res, runner)
        if res.new_token_id is not None:
            if before is None:
                res.notes.append(f"NFT #{res.new_token_id} was minted; recovered from its confirmed receipt")
            return
        tid = minted_token_id(getattr(runner, "logs", None) or [], self.npm.address, self.owner)
        if tid is not None:
            res.new_token_id = tid
            self._recover_amounts(res, getattr(runner, "logs", []), tid)
            res.notes.append(f"NFT #{tid} was minted; the mint stage failed after its receipt")

    def _finish(self, res: RebalanceResult, runner: Runner) -> None:
        res.gas_used = dict(getattr(runner, "gas_used", {}))
        res.fee_wei = int(getattr(runner, "fee_wei", 0))

    def _ratio_swap_loop(
        self,
        pool: PoolState,
        new: Range,
        runner: Runner,
        res: RebalanceResult,
        on_stage: StageHook,
        avail: Callable[[StageResult], tuple[int, int]],
        avail0: int,
        avail1: int,
        sp: int,
        usd0: float,
        usd1: float,
        deadline: Callable[[], int],
        slip: float,
    ) -> tuple[int, int, int]:
        t0, t1 = pool.token0.address, pool.token1.address
        value_usd = avail0 / 10**pool.token0.decimals * usd0 + avail1 / 10**pool.token1.decimals * usd1
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
            if token_delta(r.logs, t_in, self.owner) != -amt_i or token_delta(r.logs, t_out, self.owner) <= 0:
                raise RuntimeError("swap receipt does not prove the expected token transfers")
            avail0, avail1 = avail(r)
            sp = r.sqrt_price_x96 or sp
        if not new.contains(clmath_tick(sp)):
            res.notes.append("price is outside the target range after the swap; the deposit will be single-sided")
        return avail0, avail1, sp

    def _mint_and_stake(
        self,
        pool: PoolState,
        new: Range,
        stake_new: bool,
        runner: Runner,
        res: RebalanceResult,
        on_stage: StageHook,
        start: dict[str, int],
        avail0: int,
        avail1: int,
        sp_now: int,
        deadline: Callable[[], int],
        slip: float,
    ) -> None:
        t0, t1 = pool.token0.address, pool.token1.address
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
        if res.new_token_id is None:
            raise RuntimeError("mint succeeded but no Transfer(0x0 -> owner) log found")
        res.amounts_in_position = increased_amounts(r.logs, self.npm.address, res.new_token_id)
        on_stage("mint", res)
        if stake_new and pool.gauge_alive:
            self._stake(pool, res.new_token_id, runner, res, on_stage)
        elif stake_new:
            res.notes.append("gauge not activated: left the new deposit unstaked (earning fees)")

    def _stake(self, pool: PoolState, token_id: int, runner: Runner, res: RebalanceResult, on_stage: StageHook) -> None:
        g = self.chain.gauge_contract(pool.gauge)
        r = runner.execute(
            [
                PlannedTx(
                    "npm.approve(gauge)", self.npm.address, self.npm.encode_abi("approve", args=[g.address, token_id])
                ),
                PlannedTx("gauge.deposit", g.address, g.encode_abi("deposit", args=[token_id])),
            ]
        )
        res.stages.append("stake")
        res.tx_hashes += r.tx_hashes
        res.staked = True
        on_stage("stake", res)

    def _wrap(self, op: str, res: RebalanceResult, runner: Runner, fn: Callable[[], None]) -> RebalanceResult:
        try:
            fn()
            self._finish(res, runner)
            return res
        except Exception as e:
            res.tx_hashes = list(getattr(runner, "sent_hashes", None) or res.tx_hashes)
            self._finish(res, runner)
            self._recover_mint(res, runner)
            where = res.stages[-1] if res.stages else "start"
            raise RebalanceError(f"{op} failed after stage '{where}': {e}", res) from e
        finally:
            if hasattr(runner, "finish_submission"):
                runner.finish_submission()

    # -------------------------------------------------------------- new positions and additions

    def deploy(
        self,
        pool: PoolState,
        new: Range,
        stake: bool,
        amount0: int,
        amount1: int,
        runner: Runner,
        usd0: float,
        usd1: float,
        on_stage: StageHook | None = None,
    ) -> RebalanceResult:
        """Open a new position from wallet funds: swap toward the range's ratio inside `pool`, mint, stake.

        Only `amount0`/`amount1` (plus what our own swaps turn them into) are used; other wallet funds are not.
        """
        res = RebalanceResult(None, False, [], [], {})
        hook = on_stage or (lambda stage, r: None)

        def go() -> None:
            start = runner.execute([]).balances
            slip = self.cfg.max_slippage_bps / 1e4

            def deadline() -> int:
                return runner.block_timestamp() + self.cfg.deadline_s

            t0, t1 = pool.token0.address, pool.token1.address

            funds = [amount0, amount1]

            def avail(r: StageResult) -> tuple[int, int]:
                return self._available(funds, (t0, t1), r, start, (amount0, amount1))

            a0, a1, sp = self._ratio_swap_loop(
                pool, new, runner, res, hook, avail, amount0, amount1, pool.sqrt_price_x96, usd0, usd1, deadline, slip
            )
            self._mint_and_stake(pool, new, stake, runner, res, hook, start, a0, a1, sp, deadline, slip)

        return self._wrap("deploy", res, runner, go)

    def topup(
        self,
        pos: PositionState,
        amount0: int,
        amount1: int,
        runner: Runner,
        usd0: float,
        usd1: float,
        on_stage: StageHook | None = None,
        *,
        include_unstake_proceeds: bool = True,
    ) -> RebalanceResult:
        """Add wallet funds to an existing position (compounding or reinforcing a winner).

        A staked NFT belongs to the gauge, so it is unstaked first (which also claims its AERO) and restaked
        after the increase. The same token id is kept. Set include_unstake_proceeds=False to spend only
        the designated amounts and leave any pool-token fees or rewards released by unstaking in the wallet.
        """
        res = RebalanceResult(pos.token_id, pos.staked, [], [], {})
        hook = on_stage or (lambda stage, r: None)
        pool = pos.pool
        rng = Range(pos.tick_lower, pos.tick_upper)

        def go() -> None:
            start = runner.execute([]).balances
            slip = self.cfg.max_slippage_bps / 1e4

            def deadline() -> int:
                return runner.block_timestamp() + self.cfg.deadline_s

            t0, t1 = pool.token0.address, pool.token1.address

            funds = [amount0, amount1]

            def avail(r: StageResult) -> tuple[int, int]:
                return self._available(funds, (t0, t1), r, start, (amount0, amount1))

            a0, a1, sp = amount0, amount1, pool.sqrt_price_x96
            try:
                if pos.staked:
                    g = self.chain.gauge_contract(pool.gauge)
                    r = runner.execute(
                        [PlannedTx("gauge.withdraw", g.address, g.encode_abi("withdraw", args=[pos.token_id]))]
                    )
                    res.stages.append("unstake")
                    res.staked = False
                    res.tx_hashes += r.tx_hashes
                    res.aero_claimed = token_delta(r.logs, addresses.AERO_TOKEN, self.owner)
                    hook("unstake", res)
                    sp = r.sqrt_price_x96 or sp
                    if include_unstake_proceeds:
                        a0, a1 = avail(r)
                    else:
                        a0, a1 = (
                            min(amount, max(0, amount + r.balances[t] - start[t]))
                            for amount, t in ((amount0, t0), (amount1, t1))
                        )
                        funds[:] = [a0, a1]
                    self._check_drift(pool, r.sqrt_price_x96)
                a0, a1, sp = self._ratio_swap_loop(
                    pool, rng, runner, res, hook, avail, a0, a1, sp, usd0, usd1, deadline, slip
                )
                sa, sb = clmath.get_sqrt_ratio_at_tick(pos.tick_lower), clmath.get_sqrt_ratio_at_tick(pos.tick_upper)
                liq = clmath.get_liquidity_for_amounts(sp, sa, sb, a0, a1)
                if liq <= 0:
                    raise RuntimeError("nothing to add: amounts give zero liquidity at the current price")
                e0, e1 = clmath.get_amounts_for_liquidity(sp, sa, sb, liq)
                params = (pos.token_id, a0, a1, int(e0 * (1 - slip)), int(e1 * (1 - slip)), deadline())
                r = runner.execute(
                    [
                        self._approve(t0, self.npm.address, a0),
                        self._approve(t1, self.npm.address, a1),
                        PlannedTx(
                            "increaseLiquidity",
                            self.npm.address,
                            self.npm.encode_abi("increaseLiquidity", args=[params]),
                        ),
                    ]
                )
                res.stages.append("increase")
                res.tx_hashes += r.tx_hashes
                res.amounts_in_position = increased_amounts(r.logs, self.npm.address, pos.token_id)
                hook("increase", res)
                if pos.staked:
                    self._stake(pool, pos.token_id, runner, res, hook)
            except Exception:
                self._recover_confirmed(res, runner)
                # A staked NFT that was unstaked must not stay out of the gauge (it would earn no AERO until
                # the next rebalance). Try once to put it back, then re-raise the original failure.
                if pos.staked and not res.staked and (res.stages or getattr(runner, "sent_hashes", None)):
                    try:
                        self._stake(pool, pos.token_id, runner, res, hook)
                        res.notes.append("topup failed; the position was restaked")
                    except Exception as e2:  # noqa: BLE001 - report both failures
                        res.notes.append(f"topup failed and the restake also failed: {e2}")
                raise

        return self._wrap("topup", res, runner, go)

    def claim(self, pos: PositionState, runner: Runner) -> RebalanceResult:
        """Claim AERO for a staked position to the wallet (no unstake)."""
        res = RebalanceResult(pos.token_id, pos.staked, [], [], {})

        def go() -> None:
            g = self.chain.gauge_contract(pos.pool.gauge)
            r = runner.execute(
                [
                    PlannedTx(
                        "gauge.claimEmissions",
                        g.address,
                        g.encode_abi("claimEmissions", args=[self.owner, self.owner, [pos.token_id]]),
                    )
                ]
            )
            res.stages.append("claim")
            res.tx_hashes += r.tx_hashes
            res.aero_claimed = token_delta(r.logs, addresses.AERO_TOKEN, self.owner)

        return self._wrap("claim", res, runner, go)

    def collect(self, pos: PositionState, runner: Runner) -> RebalanceResult:
        """Collect an unstaked position's fees to the wallet (liquidity untouched)."""
        res = RebalanceResult(pos.token_id, False, [], [], {})

        def go() -> None:
            r = runner.execute(
                [
                    PlannedTx(
                        "collect",
                        self.npm.address,
                        self.npm.encode_abi("collect", args=[(pos.token_id, self.owner, UINT128_MAX, UINT128_MAX)]),
                    )
                ]
            )
            t0, t1 = pos.pool.token0.address, pos.pool.token1.address
            res.stages.append("collect")
            res.tx_hashes += r.tx_hashes
            res.amounts_in_position = (token_delta(r.logs, t0, self.owner), token_delta(r.logs, t1, self.owner))

        return self._wrap("collect", res, runner, go)

    def swap_exact(
        self, pool: PoolState, token_in: str, amount_in: int, runner: Runner, min_out: int
    ) -> RebalanceResult:
        """One exactInputSingle on `pool` (used to turn an idle token into a target pool's token).

        `RebalanceResult.amount_out` comes from this swap's confirmed ERC20 transfer logs. Both runners
        report the same receipt evidence, so unrelated wallet transfers cannot inflate the output.
        """
        res = RebalanceResult(None, False, [], [], {})
        t0, t1 = pool.token0.address, pool.token1.address
        if token_in.lower() not in (t0.lower(), t1.lower()):
            raise ValueError(f"{token_in} is not a token of pool {pool.address}")
        if amount_in <= 0:
            raise ValueError("amount_in must be > 0")
        token_out = t1 if token_in.lower() == t0.lower() else t0

        def go() -> None:
            deadline = runner.block_timestamp() + self.cfg.deadline_s
            params = (token_in, token_out, pool.tick_spacing, self.owner, deadline, amount_in, min_out, 0)
            r = runner.execute(
                [
                    self._approve(token_in, self.router.address, amount_in),
                    PlannedTx(
                        f"swap {amount_in}",
                        self.router.address,
                        self.router.encode_abi("exactInputSingle", args=[params]),
                    ),
                ]
            )
            res.stages.append("swap")
            res.tx_hashes += r.tx_hashes
            res.amount_out = token_delta(r.logs, token_out, self.owner)
            if token_delta(r.logs, token_in, self.owner) != -amount_in or res.amount_out <= 0:
                raise RuntimeError("swap receipt does not prove the expected token transfers")

        return self._wrap("swap", res, runner, go)

    def unwrap_weth(self, amount: int, runner: Runner) -> RebalanceResult:
        """WETH -> native ETH, to keep a gas reserve without asking the owner to send ETH."""
        res = RebalanceResult(None, False, [], [], {})
        weth = self.chain.w3.eth.contract(address=Web3.to_checksum_address(addresses.WETH), abi=abi.WETH)

        def go() -> None:
            r = runner.execute([PlannedTx("weth.withdraw", weth.address, weth.encode_abi("withdraw", args=[amount]))])
            res.stages.append("unwrap")
            res.tx_hashes += r.tx_hashes

        return self._wrap("unwrap", res, runner, go)

    def swap_to_eth(
        self, pool: PoolState, token_in: str, amount_in: int, min_eth_out: int, runner: Runner
    ) -> RebalanceResult:
        """Swap `token_in` -> WETH held by the router, then `unwrapWETH9` to the owner, in one router multicall.

        For smart accounts (e.g. an EIP-7702-delegated EOA): WETH9.withdraw pays ETH with a 2300-gas
        `transfer`, which a delegated account cannot receive, so it reverts. The router's unwrapWETH9 pays
        with a full-gas `call` (TransferHelper.safeTransferETH). Recipient 0 makes the router keep the WETH
        between the two calls inside the same transaction, so nothing is left exposed across transactions.
        """
        res = RebalanceResult(None, False, [], [], {})
        weth = Web3.to_checksum_address(addresses.WETH)
        if weth not in (pool.token0.address, pool.token1.address):
            raise ValueError("swap_to_eth needs a pool that contains WETH")

        def go() -> None:
            deadline = runner.block_timestamp() + self.cfg.deadline_s
            zero = "0x0000000000000000000000000000000000000000"
            swap = self.router.encode_abi(
                "exactInputSingle",
                args=[(token_in, weth, pool.tick_spacing, zero, deadline, amount_in, min_eth_out, 0)],
            )
            unwrap = self.router.encode_abi("unwrapWETH9", args=[min_eth_out, self.owner])
            r = runner.execute(
                [
                    self._approve(token_in, self.router.address, amount_in),
                    PlannedTx(
                        f"router multicall: {amount_in} -> ETH (swap + unwrapWETH9)",
                        self.router.address,
                        self.router.encode_abi("multicall", args=[[HexBytes(swap), HexBytes(unwrap)]]),
                    ),
                ]
            )
            res.stages.append("swap_to_eth")
            res.tx_hashes += r.tx_hashes

        return self._wrap("swap_to_eth", res, runner, go)


def receipt_fee_wei(rcpt: Any) -> int:
    """Execution fee + OP-stack L1 data fee from a receipt (l1Fee may be hex, int or absent)."""
    fee = int(rcpt["gasUsed"]) * int(rcpt.get("effectiveGasPrice", 0) or 0)
    l1 = rcpt.get("l1Fee", 0) or 0
    fee += int(l1, 16) if isinstance(l1, str) else int(l1)
    return fee


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
