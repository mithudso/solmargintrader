"""Semantic transaction verifier: what the extension never had. Runs BEFORE anything is signed.

Jupiter's `/swap` returns a serialized transaction. That response is untrusted: a compromised or buggy API could
return a transaction that drains the wallet while still "being a swap". Nothing is signed until two layers pass.

Layer 1, `check_static` (pure, no network): reads the transaction itself.
  * the fee payer is the owner, and the owner is the only signer;
  * the fully decoded ExactIn route spends the approved input and enforces at least the approved minimum output;
  * every program id is on PROGRAM_ALLOWLIST, and each allowed program may run only the instructions listed for it;
  * compute-budget instructions are present and bound the priority fee;
  * SOL leaving the owner through System instructions is bounded by the input amount plus token-account rent;
  * ATA creation is only for the owner and only for the swap's mints;
  * no top-level token transfer, approve, set-authority, burn, or close-to-another-wallet.

Layer 2, `check_economics` (needs the pre-state and a `simulateTransaction` post-state of every writable account):
  * the simulation succeeded;
  * no writable token account owned by the owner other than the swap's own (input, output, wSOL) ATAs changed hands
    or balance, and no third-party wallet's lamports moved;
  * the owner's token / SOL deltas match the quote: input falls by exactly the amount, output rises by at least
    `minOut`, and SOL falls only by the fee, retained token-account rent, and the input when SOL is the input;
  * the owner keeps at least `min_sol_reserve_lamports`.

Any mismatch returns a problem string; the caller refuses. Anything the decoder does not recognise is a problem,
never skipped: an unknown instruction is exactly where a drain would hide.
"""

from __future__ import annotations

import base64
import hashlib
import struct
from dataclasses import dataclass, field
from typing import Any

from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from .jupiter_route import decode_route
from .tokens import WSOL_MINT

# --- Program allowlist. Each entry says why the program may appear and what it may do. ---------------------------
JUPITER_V6 = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
ATA_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
COMPUTE_BUDGET = "ComputeBudget111111111111111111111111111111"
SYSTEM_PROGRAM = "11111111111111111111111111111111"

PROGRAM_ALLOWLIST: dict[str, str] = {
    JUPITER_V6: "Jupiter v6 aggregator: the one swap instruction (route or shared_accounts_route, ExactIn only).",
    TOKEN_PROGRAM: "SPL Token: only SyncNative, CloseAccount to the owner, and the Initialize* of the owner's own account.",
    TOKEN_2022: "SPL Token-2022: same restricted set as SPL Token; no allowed mint uses it today, kept for wSOL-like flows.",
    ATA_PROGRAM: "Associated Token Account: Create / CreateIdempotent of the owner's ATA for the swap's mints only.",
    COMPUTE_BUDGET: "Compute Budget: SetComputeUnitLimit, SetComputeUnitPrice, SetLoadedAccountsDataSizeLimit.",
    SYSTEM_PROGRAM: "System: Transfer from the owner into the owner's wSOL account, and CreateAccountWithSeed for a wSOL temp account.",
}

# Anchor discriminators: sha256("global:<name>")[:8]. Only ExactIn routes are allowed.
JUPITER_ALLOWED_DISCRIMINATORS = {
    bytes.fromhex("e517cb977ae3ad2a"): "route",
    bytes.fromhex("c1209b3341d69c81"): "shared_accounts_route",
}

TOKEN_ACCOUNT_RENT_LAMPORTS = 2_039_280  # rent-exempt minimum of a 165-byte token account
BASE_FEE_PER_SIGNATURE = 5_000
MAX_INSTRUCTIONS = 14
MAX_COMPUTE_UNITS = 1_400_000


def ata_address(wallet: str, mint: str, token_program: str = TOKEN_PROGRAM) -> str:
    addr, _ = Pubkey.find_program_address(
        [bytes(Pubkey.from_string(wallet)), bytes(Pubkey.from_string(token_program)), bytes(Pubkey.from_string(mint))],
        Pubkey.from_string(ATA_PROGRAM),
    )
    return str(addr)


@dataclass
class Ix:
    program: str
    accounts: list[str]
    data: bytes


@dataclass
class TxFacts:
    version: str
    fee_payer: str
    required_signers: int
    static_keys: list[str]
    keys: list[str]  # static + loaded from lookup tables
    writable: set[str]
    instructions: list[Ix]
    lookup_tables: list[str]
    unresolved_tables: list[str] = field(default_factory=list)
    program_index_errors: list[str] = field(default_factory=list)
    cu_limit: int | None = None
    cu_price_micro: int | None = None

    @property
    def programs(self) -> list[str]:
        return [ix.program for ix in self.instructions]

    @property
    def priority_fee_lamports(self) -> int:
        if self.cu_limit is None or self.cu_price_micro is None:
            return 0
        return -(-self.cu_limit * self.cu_price_micro // 1_000_000)  # ceil

    @property
    def fee_lamports(self) -> int:
        return BASE_FEE_PER_SIGNATURE * self.required_signers + self.priority_fee_lamports


def decode_b64(tx_b64: str) -> VersionedTransaction:
    return VersionedTransaction.from_bytes(base64.b64decode(tx_b64, validate=True))


def lookup_table_addresses(data: bytes) -> list[str]:
    """Addresses stored in an address-lookup-table account (56-byte header, then 32-byte keys)."""
    body = data[56:]
    return [str(Pubkey.from_bytes(body[i : i + 32])) for i in range(0, len(body) - len(body) % 32, 32)]


def inspect_tx(tx: VersionedTransaction, tables: dict[str, list[str]] | None = None) -> TxFacts:
    """Decode a transaction into facts. `tables` maps lookup-table address -> its addresses (from RPC)."""
    tables = tables or {}
    msg = tx.message
    static = [str(k) for k in msg.account_keys]
    hdr = msg.header
    n, n_sig = len(static), hdr.num_required_signatures
    writable = set()
    for i, key in enumerate(static):
        if i < n_sig - hdr.num_readonly_signed_accounts or n_sig <= i < n - hdr.num_readonly_unsigned_accounts:
            writable.add(key)
    loaded_w: list[str] = []
    loaded_r: list[str] = []
    table_keys: list[str] = []
    unresolved: list[str] = []
    version = "legacy"
    lookups = getattr(msg, "address_table_lookups", None)
    if lookups is not None:
        version = "v0"
        for lk in lookups:
            tk = str(lk.account_key)
            table_keys.append(tk)
            addrs = tables.get(tk)
            if addrs is None:
                unresolved.append(tk)
                continue
            try:
                loaded_w += [addrs[i] for i in bytes(lk.writable_indexes)]
                loaded_r += [addrs[i] for i in bytes(lk.readonly_indexes)]
            except IndexError:
                unresolved.append(tk)
    keys = static + loaded_w + loaded_r
    writable.update(loaded_w)
    facts = TxFacts(version, static[0] if static else "", n_sig, static, keys, writable, [], table_keys, unresolved)
    for ix in msg.instructions:
        if ix.program_id_index >= len(static):
            facts.program_index_errors.append("a program id is loaded from a lookup table")
            continue
        try:
            accts = [keys[i] for i in bytes(ix.accounts)]
        except IndexError:
            facts.program_index_errors.append("an instruction references an account index out of range")
            continue
        facts.instructions.append(Ix(static[ix.program_id_index], accts, bytes(ix.data)))
    for ix in facts.instructions:
        if ix.program == COMPUTE_BUDGET and ix.data:
            if ix.data[0] == 2 and len(ix.data) == 5:
                facts.cu_limit = struct.unpack("<I", ix.data[1:5])[0]
            elif ix.data[0] == 3 and len(ix.data) == 9:
                facts.cu_price_micro = struct.unpack("<Q", ix.data[1:9])[0]
    return facts


@dataclass(frozen=True)
class Expectation:
    owner: str
    mint_in: str
    mint_out: str
    amount_in: int
    min_out: int
    max_priority_fee_lamports: int
    min_sol_reserve_lamports: int

    @property
    def watched_mints(self) -> set[str]:
        return {self.mint_in, self.mint_out, WSOL_MINT}

    def expected_token_accounts(self) -> dict[str, str]:
        """ATA address -> mint, for the owner's token accounts this swap is allowed to touch."""
        return {ata_address(self.owner, m): m for m in sorted(self.watched_mints)}


def check_static(facts: TxFacts, exp: Expectation) -> tuple[list[str], dict[str, Any]]:
    """Layer 1. Returns (problems, info). `info` is evidence for the journal."""
    problems: list[str] = list(facts.program_index_errors)
    owner = exp.owner
    expected_tokens = exp.expected_token_accounts()
    if facts.unresolved_tables:
        problems.append("address lookup table(s) could not be resolved: cannot inspect every account")
    if facts.fee_payer != owner:
        problems.append(f"fee payer is {facts.fee_payer}, not the owner")
    if facts.required_signers != 1:
        problems.append(f"transaction needs {facts.required_signers} signatures; only the owner signs")
    if len(facts.instructions) > MAX_INSTRUCTIONS:
        problems.append(f"{len(facts.instructions)} instructions exceeds the limit {MAX_INSTRUCTIONS}")
    seed_accounts: set[str] = set()
    system_out = 0
    created_atas: list[dict[str, str]] = []
    jupiter_ixs = 0
    jupiter_route: dict[str, Any] = {}
    for ix in facts.instructions:
        if ix.program not in PROGRAM_ALLOWLIST:
            problems.append(f"program {ix.program} is not on the allowlist")
            continue
        if ix.program == JUPITER_V6:
            jupiter_ixs += 1
            kind = JUPITER_ALLOWED_DISCRIMINATORS.get(ix.data[:8])
            if kind is None:
                problems.append("Jupiter instruction is not an ExactIn route")
            else:
                try:
                    bound = decode_route(ix.data, kind)
                    jupiter_route = vars(bound)
                    if bound.amount_in != exp.amount_in:
                        problems.append("Jupiter route input does not match the approved amount")
                    if exp.min_out <= 0 or bound.minimum_out < exp.min_out:
                        problems.append("Jupiter route minimum output is below the approved minOut")
                except ValueError as error:
                    problems.append(str(error))
            if owner not in ix.accounts:
                problems.append("Jupiter instruction does not involve the owner")
        elif ix.program == COMPUTE_BUDGET:
            _check_compute_ix(ix, problems)
        elif ix.program == SYSTEM_PROGRAM:
            system_out += _check_system_ix(ix, owner, expected_tokens, seed_accounts, problems)
        elif ix.program in (TOKEN_PROGRAM, TOKEN_2022):
            _check_token_ix(ix, owner, expected_tokens, seed_accounts, problems)
        elif ix.program == ATA_PROGRAM:
            _check_ata_ix(ix, owner, exp, created_atas, problems)
    if jupiter_ixs != 1:
        problems.append(f"expected exactly one Jupiter instruction, found {jupiter_ixs}")
    if facts.cu_limit is None or facts.cu_price_micro is None:
        problems.append("compute-unit limit and price instructions are both required to bound the fee")
    else:
        if facts.cu_limit > MAX_COMPUTE_UNITS:
            problems.append(f"compute-unit limit {facts.cu_limit} exceeds {MAX_COMPUTE_UNITS}")
        if facts.priority_fee_lamports > exp.max_priority_fee_lamports:
            problems.append(
                f"priority fee {facts.priority_fee_lamports} lamports exceeds max_priority_fee_lamports "
                f"{exp.max_priority_fee_lamports}"
            )
    allowed_system_out = (exp.amount_in if exp.mint_in == WSOL_MINT else 0) + TOKEN_ACCOUNT_RENT_LAMPORTS * len(
        seed_accounts
    )
    if system_out > allowed_system_out:
        problems.append(
            f"System instructions move {system_out} lamports out of the owner; at most {allowed_system_out} allowed"
        )
    info = {
        "version": facts.version,
        "programs": sorted(set(facts.programs)),
        "instruction_count": len(facts.instructions),
        "fee_lamports": facts.fee_lamports,
        "priority_fee_lamports": facts.priority_fee_lamports,
        "system_out_lamports": system_out,
        "created_atas": created_atas,
        "lookup_tables": facts.lookup_tables,
        "writable_account_count": len(facts.writable),
        "jupiter_route": jupiter_route,
    }
    return problems, info


def _check_compute_ix(ix: Ix, problems: list[str]) -> None:
    d = ix.data
    kind = d[0] if d else -1
    if kind == 2 and len(d) == 5:
        return
    if kind == 3 and len(d) == 9:
        return
    if kind == 4 and len(d) == 5:
        return
    problems.append(f"compute-budget instruction type {kind} is not allowed")


def _check_system_ix(
    ix: Ix, owner: str, expected_tokens: dict[str, str], seed_accounts: set[str], problems: list[str]
) -> int:
    d = ix.data
    kind = struct.unpack("<I", d[:4])[0] if len(d) >= 4 else -1
    if kind == 2 and len(d) == 12 and len(ix.accounts) >= 2:  # Transfer
        src, dst = ix.accounts[0], ix.accounts[1]
        lamports = struct.unpack("<Q", d[4:12])[0]
        if src != owner:
            problems.append("System transfer from an account other than the owner")
            return 0
        wsol_ata = ata_address(owner, WSOL_MINT)
        if dst != wsol_ata and dst not in seed_accounts:
            problems.append(f"System transfer of {lamports} lamports to {dst}, which is not the owner's wSOL account")
        return lamports
    if kind == 3 and len(ix.accounts) >= 2:  # CreateAccountWithSeed: from, created, [base]
        try:
            seed_len = struct.unpack("<Q", d[36:44])[0]
            off = 44 + seed_len
            lamports, space = struct.unpack("<QQ", d[off : off + 16])
            new_owner = str(Pubkey.from_bytes(d[off + 16 : off + 48]))
        except (struct.error, ValueError):
            problems.append("System CreateAccountWithSeed is malformed")
            return 0
        if ix.accounts[0] != owner:
            problems.append("System CreateAccountWithSeed funded by an account other than the owner")
            return 0
        if new_owner != TOKEN_PROGRAM or space != 165:
            problems.append("System CreateAccountWithSeed creates something other than a 165-byte token account")
            return 0
        seed_accounts.add(ix.accounts[1])
        return lamports
    problems.append(f"System instruction type {kind} is not allowed")
    return 0


def _check_token_ix(
    ix: Ix, owner: str, expected_tokens: dict[str, str], seed_accounts: set[str], problems: list[str]
) -> None:
    d = ix.data
    kind = d[0] if d else -1
    mine = set(expected_tokens) | seed_accounts
    a = ix.accounts
    if kind == 17 and len(a) >= 1:  # SyncNative
        if a[0] not in mine:
            problems.append("SyncNative on an account that is not the owner's wSOL account")
    elif kind == 9 and len(a) >= 3:  # CloseAccount: account, destination, authority
        if a[1] != owner or a[2] != owner:
            problems.append("CloseAccount with a destination or authority other than the owner")
        if a[0] not in mine:
            problems.append("CloseAccount of an account that is not part of this swap")
    elif kind == 1 and len(a) >= 3:  # InitializeAccount: account, mint, owner
        if a[2] != owner:
            problems.append("InitializeAccount assigns a token account to someone other than the owner")
    elif kind in (16, 18) and len(d) >= 33 and len(a) >= 1:  # InitializeAccount2/3: owner in data
        try:
            who = str(Pubkey.from_bytes(d[1:33]))
        except ValueError:
            who = "?"
        if who != owner:
            problems.append("InitializeAccount assigns a token account to someone other than the owner")
    elif kind in (21, 22):
        return
    else:
        problems.append(
            f"Token instruction type {kind} is not allowed (no top-level transfer, approve, burn or set-authority)"
        )


def _check_ata_ix(ix: Ix, owner: str, exp: Expectation, created: list[dict[str, str]], problems: list[str]) -> None:
    if ix.data not in (b"", b"\x00", b"\x01"):
        problems.append("Associated Token instruction is not Create or CreateIdempotent")
        return
    if len(ix.accounts) < 6:
        problems.append("Associated Token instruction has too few accounts")
        return
    payer, ata, wallet, mint, _system, token_prog = ix.accounts[:6]
    if payer != owner or wallet != owner:
        problems.append("ATA creation for or paid by an account other than the owner")
    if mint not in exp.watched_mints:
        problems.append(f"ATA creation for mint {mint}, which is not part of this swap")
    if token_prog != TOKEN_PROGRAM:
        problems.append("ATA creation under a token program other than SPL Token")
    elif ata != ata_address(wallet, mint):
        problems.append("ATA creation target is not the derived associated address")
    created.append({"ata": ata, "mint": mint})


# --- Layer 2 ------------------------------------------------------------------------------------------------


def parse_token_account(acc: dict[str, Any] | None) -> tuple[str, str, int] | None:
    """(mint, owner, amount) of a SPL token account, or None if it is not one."""
    if not acc or acc.get("owner") not in (TOKEN_PROGRAM, TOKEN_2022):
        return None
    data = acc["data"]
    if len(data) < 165:
        return None
    return str(Pubkey.from_bytes(data[0:32])), str(Pubkey.from_bytes(data[32:64])), struct.unpack("<Q", data[64:72])[0]


def watch_list(facts: TxFacts, exp: Expectation) -> list[str]:
    """Every address whose pre and post state the economic check needs, in a stable order."""
    seen = {exp.owner, *exp.expected_token_accounts(), *facts.writable}
    return [exp.owner] + sorted(seen - {exp.owner})


def check_economics(
    facts: TxFacts,
    exp: Expectation,
    info: dict[str, Any],
    watch: list[str],
    pre: list[dict[str, Any] | None],
    sim: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    """Layer 2: compare pre-state with the simulated post-state of every writable account."""
    problems: list[str] = []
    if sim.get("err") is not None:
        return [f"simulation failed: {str(sim['err'])[:200]}"], {
            "sim_err": sim.get("err"),
            "logs": (sim.get("logs") or [])[-6:],
        }
    post = sim.get("accounts") or []
    if len(post) != len(watch) or len(pre) != len(watch):
        return ["simulation did not return the watched accounts"], {}
    pre_by = dict(zip(watch, pre, strict=True))
    post_by = dict(zip(watch, post, strict=True))
    owner, expected = exp.owner, exp.expected_token_accounts()
    in_ata, out_ata, wsol_ata = (ata_address(owner, m) for m in (exp.mint_in, exp.mint_out, WSOL_MINT))

    for addr in watch:
        if addr == owner:
            continue
        before, after = pre_by[addr], post_by[addr]
        for label, acc in (("before", before), ("after", after)):
            tok = parse_token_account(acc)
            if tok and tok[1] == owner and addr not in expected:
                problems.append(f"swap touches the owner's token account {addr} ({label}), which is not part of it")
        if addr in expected and after is not None:
            tok = parse_token_account(after)
            if tok is not None and tok[1] != owner:
                problems.append(f"owner token account {addr} changes owner")
        for acc in (before, after):
            if acc is not None and acc["owner"] == SYSTEM_PROGRAM and addr in facts.writable:
                b = before["lamports"] if before else 0
                a = after["lamports"] if after else 0
                if a != b:
                    problems.append(f"lamports of wallet {addr} change by {a - b}: a third party is paid")
                break

    def amount(acc: dict[str, Any] | None) -> int:
        tok = parse_token_account(acc)
        return tok[2] if tok and tok[1] == owner else 0

    own_pre, own_post = pre_by[owner], post_by[owner]
    if own_pre is None or own_post is None:
        return ["owner account is missing from pre/post state"], {}
    native_delta = own_post["lamports"] - own_pre["lamports"]
    fee = facts.fee_lamports

    def rent_total(accounts):
        total = 0
        for addr in expected:
            acc = accounts.get(addr)
            tok = parse_token_account(acc)
            if tok and tok[1] == owner:
                rent = acc["lamports"] - (tok[2] if tok[0] == WSOL_MINT else 0)
                if rent < 0:
                    problems.append("wrapped-SOL account has inconsistent lamports and token balance")
                total += rent
        return total

    rent_delta = rent_total(post_by) - rent_total(pre_by)
    retained_rent = max(0, rent_delta)
    wrapped_delta = amount(post_by.get(wsol_ata)) - amount(pre_by.get(wsol_ata))
    # Moving native SOL into WSOL or releasing old WSOL/rent changes no owned swap value.
    sol_delta = native_delta + wrapped_delta + fee + rent_delta
    d_in = amount(post_by[in_ata]) - amount(pre_by[in_ata])
    d_out = amount(post_by[out_ata]) - amount(pre_by[out_ata])
    evidence: dict[str, Any] = {
        "native_delta_lamports": native_delta,
        "fee_lamports": fee,
        "retained_rent_lamports": retained_rent,
        "rent_delta_lamports": rent_delta,
        "wrapped_sol_delta_raw": wrapped_delta,
        "economic_sol_delta_raw": sol_delta,
        "input_token_delta_raw": d_in,
        "output_token_delta_raw": d_out,
        "owner_lamports_after": own_post["lamports"],
        "units_consumed": sim.get("unitsConsumed"),
    }

    if exp.mint_in == WSOL_MINT:
        if sol_delta < -exp.amount_in:
            problems.append(f"SOL spend {-sol_delta} is more than input + fee + rent permits ({exp.amount_in} input)")
        if sol_delta > -exp.amount_in:
            problems.append(f"SOL input {exp.amount_in} is not being spent exactly (actual {-sol_delta})")
    else:
        if pre_by[in_ata] is None:
            problems.append("owner has no input token account")
        if d_in != -exp.amount_in:
            problems.append(f"input token changes by {d_in}, expected exactly {-exp.amount_in}")
        if sol_delta < 0:
            problems.append(f"SOL falls by {-sol_delta}, more than fee + rent")
    if exp.mint_out == WSOL_MINT:
        if sol_delta < exp.min_out:
            problems.append(f"SOL received {sol_delta} is below minOut {exp.min_out}")
    elif d_out < exp.min_out:
        problems.append(f"output token rises by {d_out}, below minOut {exp.min_out}")
    if own_post["lamports"] < exp.min_sol_reserve_lamports:
        problems.append(
            f"owner would keep {own_post['lamports']} lamports, below min_sol_reserve_lamports {exp.min_sol_reserve_lamports}"
        )
    return problems, evidence


def message_hash(tx: VersionedTransaction) -> str:
    """Hash of the message bytes: proves the signed transaction carries the message that was verified."""
    return hashlib.sha256(bytes(tx.message)).hexdigest()
