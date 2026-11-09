"""The semantic verifier: honest transactions pass; every malicious fixture is refused, each for its own reason."""

import base64
import struct

import pytest
from conftest import (
    ATTACKER,
    OTHER_MINT,
    POOL_STATE,
    UNKNOWN_PROGRAM,
    FakeRpc,
    ata_create,
    cu_limit,
    cu_price,
    delta_native,
    delta_token,
    fixture,
    ix,
    jupiter_ix,
    make_tx,
    meta,
    pool_account,
    swap_instructions,
    sys_transfer,
    token_account,
    wallet_account,
)
from solders.keypair import Keypair

from executor import txverify as tv
from executor.tokens import USDC_MINT, WSOL_MINT

AMOUNT = 10_000_000  # 0.01 SOL
MIN_OUT = 896_771
RESERVE = 5_000_000


def exp(owner, mint_in=WSOL_MINT, mint_out=USDC_MINT, amount=AMOUNT, min_out=MIN_OUT, max_prio=200_000):
    return tv.Expectation(owner, mint_in, mint_out, amount, min_out, max_prio, RESERVE)


def static(owner, instructions, payer=None, **kw):
    tx = make_tx(instructions, payer or owner)
    facts = tv.inspect_tx(tx, kw.pop("tables", {}))
    return tv.check_static(facts, exp(owner, **kw)), facts


def honest(owner):
    return swap_instructions(owner, WSOL_MINT, USDC_MINT, AMOUNT)


def has(problems, text):
    return any(text in p for p in problems)


# -- layer 1 ---------------------------------------------------------------------------------------------------


def test_honest_sol_to_usdc_passes(owner):
    (problems, info), facts = static(owner, honest(owner))
    assert problems == []
    assert info["fee_lamports"] == 5_000 + 5_000  # one signature + 100k CU at 50k micro-lamports
    assert info["system_out_lamports"] == AMOUNT
    assert set(info["programs"]) <= set(tv.PROGRAM_ALLOWLIST)


def test_honest_usdc_to_sol_passes(owner):
    ixs = swap_instructions(owner, USDC_MINT, WSOL_MINT, 1_000_000)
    (problems, _), _ = static(owner, ixs, mint_in=USDC_MINT, mint_out=WSOL_MINT, amount=1_000_000)
    assert problems == []


def test_foreign_fee_payer_is_refused(owner):
    attacker_kp = Keypair.from_seed(bytes([66] * 32))
    ixs = [*honest(owner)]
    # The attacker pays and the owner is a second signer: the owner's signature would authorise whatever follows.
    (problems, _), facts = static(owner, ixs, payer=str(attacker_kp.pubkey()))
    assert has(problems, "fee payer") and has(problems, "2 signatures")
    assert facts.fee_payer == str(attacker_kp.pubkey())


def test_unknown_program_is_refused(owner):
    ixs = [*honest(owner), ix(UNKNOWN_PROGRAM, b"\x01", meta(owner, True, True))]
    (problems, _), _ = static(owner, ixs)
    assert has(problems, f"program {UNKNOWN_PROGRAM} is not on the allowlist")


def test_sol_drain_via_system_transfer_to_attacker_is_refused(owner):
    ixs = [*honest(owner), sys_transfer(owner, ATTACKER, 5_000_000)]
    (problems, _), _ = static(owner, ixs)
    assert has(problems, "not the owner's wSOL account") and has(problems, "lamports out of the owner")


def test_sol_transfer_over_the_input_amount_is_refused(owner):
    ixs = honest(owner)
    wsol = tv.ata_address(owner, WSOL_MINT)
    ixs.insert(3, sys_transfer(owner, wsol, 1))  # an extra lamport above the input amount
    (problems, _), _ = static(owner, ixs)
    assert has(problems, "lamports out of the owner")


def test_system_assign_and_other_system_instructions_are_refused(owner):
    assign = ix(tv.SYSTEM_PROGRAM, struct.pack("<I", 1) + bytes(32), meta(owner, True, True))
    (problems, _), _ = static(owner, [*honest(owner), assign])
    assert has(problems, "System instruction type 1 is not allowed")


@pytest.mark.parametrize(
    "kind,data",
    [
        (3, struct.pack("<BQ", 3, 1_000_000)),  # Transfer
        (12, struct.pack("<BQB", 12, 1_000_000, 6)),  # TransferChecked
        (4, struct.pack("<BQ", 4, 10**12)),  # Approve (hands an attacker a spending allowance)
        (6, bytes([6, 0, 1]) + bytes(32)),  # SetAuthority
        (8, struct.pack("<BQ", 8, 1)),  # Burn
    ],
)
def test_top_level_token_movements_are_refused(owner, kind, data):
    victim = tv.ata_address(owner, USDC_MINT)
    bad = ix(tv.TOKEN_PROGRAM, data, meta(victim, False, True), meta(ATTACKER, False, True), meta(owner, True, False))
    (problems, _), _ = static(owner, [*honest(owner), bad])
    assert has(problems, f"Token instruction type {kind} is not allowed")


def test_close_account_to_another_wallet_is_refused(owner):
    wsol = tv.ata_address(owner, WSOL_MINT)
    bad = ix(
        tv.TOKEN_PROGRAM, bytes([9]), meta(wsol, False, True), meta(ATTACKER, False, True), meta(owner, True, False)
    )
    (problems, _), _ = static(owner, [*honest(owner), bad])
    assert has(problems, "CloseAccount with a destination or authority other than the owner")


def test_close_of_a_foreign_token_account_is_refused(owner):
    victim = tv.ata_address(owner, OTHER_MINT)
    bad = ix(
        tv.TOKEN_PROGRAM, bytes([9]), meta(victim, False, True), meta(owner, False, True), meta(owner, True, False)
    )
    (problems, _), _ = static(owner, [*honest(owner), bad])
    assert has(problems, "not part of this swap")


def test_ata_creation_for_other_wallet_or_mint_is_refused(owner):
    (p1, _), _ = static(owner, [*honest(owner), ata_create(owner, USDC_MINT, wallet=ATTACKER)])
    (p2, _), _ = static(owner, [*honest(owner), ata_create(owner, OTHER_MINT)])
    assert has(p1, "other than the owner") and has(p2, "not part of this swap")


def test_ata_creation_with_wrong_address_is_refused(owner):
    wrong = ix(
        tv.ATA_PROGRAM, b"\x01",
        meta(owner, True, True), meta(ATTACKER, False, True), meta(owner), meta(USDC_MINT), meta(tv.SYSTEM_PROGRAM), meta(tv.TOKEN_PROGRAM),
    )  # fmt: skip
    (problems, _), _ = static(owner, [*honest(owner), wrong])
    assert has(problems, "not the derived associated address")


def test_jupiter_discriminator_must_be_an_exact_in_route(owner):
    ixs = honest(owner)
    ixs[-2] = jupiter_ix(
        owner, WSOL_MINT, USDC_MINT, data=bytes.fromhex("d033ef977b2bed5c") + b"\x00" * 28
    )  # exact_out_route
    (problems, _), _ = static(owner, ixs)
    assert has(problems, "not an ExactIn route")


def test_exactly_one_jupiter_instruction(owner):
    (p0, _), _ = static(owner, [i for i in honest(owner) if str(i.program_id) != tv.JUPITER_V6])
    (p2, _), _ = static(owner, [*honest(owner), jupiter_ix(owner, WSOL_MINT, USDC_MINT)])
    assert has(p0, "found 0") and has(p2, "found 2")


def test_priority_fee_over_cap_and_missing_compute_budget(owner):
    ixs = honest(owner)
    ixs[1] = cu_price(10_000_000)  # 100k units * 10M micro = 1,000,000 lamports
    (p1, _), _ = static(owner, ixs)
    (p2, _), _ = static(owner, [i for i in honest(owner) if str(i.program_id) != tv.COMPUTE_BUDGET])
    ixs3 = honest(owner)
    ixs3[0] = cu_limit(2_000_000)
    (p3, _), _ = static(owner, ixs3)
    assert has(p1, "priority fee") and has(p2, "both required") and has(p3, "exceeds 1400000")


def test_unknown_compute_budget_instruction_is_refused(owner):
    heap = ix(tv.COMPUTE_BUDGET, bytes([1]) + struct.pack("<I", 32768))
    (problems, _), _ = static(owner, [*honest(owner), heap])
    assert has(problems, "compute-budget instruction type 1")


def test_too_many_instructions(owner):
    (problems, _), _ = static(owner, [*honest(owner), *[cu_limit(100_000)] * 20])
    assert has(problems, "exceeds the limit")


def test_jupiter_instruction_must_involve_owner(owner):
    ixs = honest(owner)
    ixs[-2] = ix(tv.JUPITER_V6, bytes.fromhex("c1209b3341d69c81") + b"\x00" * 28, meta(ATTACKER, True, True))
    (problems, _), _ = static(owner, ixs)
    assert has(problems, "does not involve the owner")


# -- real recorded transaction, with its address lookup table --------------------------------------------------


def real_tx_and_tables():
    sw = fixture("jup_swap_sol_usdc.json")
    tx = tv.decode_b64(sw["swapTransaction"])
    alts = fixture("alt_accounts.json")
    tables = {k: tv.lookup_table_addresses(base64.b64decode(v["data"][0])) for k, v in alts.items()}
    return tx, tables


REAL_OWNER = "EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV"


def test_real_jupiter_transaction_passes_the_static_check():
    tx, tables = real_tx_and_tables()
    facts = tv.inspect_tx(tx, tables)
    problems, info = tv.check_static(facts, exp(REAL_OWNER))
    assert problems == [], problems
    assert facts.version == "v0" and facts.lookup_tables and not facts.unresolved_tables
    assert info["system_out_lamports"] == AMOUNT


def test_real_transaction_without_its_lookup_table_is_refused():
    tx, _ = real_tx_and_tables()
    problems, _ = tv.check_static(tv.inspect_tx(tx, {}), exp(REAL_OWNER))
    assert has(problems, "lookup table(s) could not be resolved")


def test_real_transaction_for_a_different_owner_is_refused():
    tx, tables = real_tx_and_tables()
    problems, _ = tv.check_static(tv.inspect_tx(tx, tables), exp(str(Keypair.from_seed(bytes([5] * 32)).pubkey())))
    assert has(problems, "fee payer")


# -- layer 2 ---------------------------------------------------------------------------------------------------


def econ_setup(owner, mint_in=WSOL_MINT, mint_out=USDC_MINT, amount=AMOUNT, min_out=MIN_OUT, instructions=None):
    chain = FakeRpc()
    chain.state[owner] = wallet_account(1_000_000_000)
    chain.state[tv.ata_address(owner, USDC_MINT)] = token_account(USDC_MINT, owner, 100_000_000)
    chain.state[tv.ata_address(owner, WSOL_MINT)] = None
    for a in (POOL_STATE,):
        chain.state[a] = pool_account()
    from conftest import POOL_VAULT_IN, POOL_VAULT_OUT

    chain.state[POOL_VAULT_IN] = pool_account()
    chain.state[POOL_VAULT_OUT] = pool_account()
    ixs = instructions or swap_instructions(owner, mint_in, mint_out, amount)
    tx = make_tx(ixs, owner)
    facts = tv.inspect_tx(tx, {})
    e = exp(owner, mint_in, mint_out, amount, min_out)
    problems, info = tv.check_static(facts, e)
    assert problems == [], problems
    return chain, facts, e, info


def run_econ(chain, facts, e, info):
    watch = tv.watch_list(facts, e)
    pre = chain.accounts(watch)
    sim = chain.simulate("x", watch, False, True)
    return tv.check_economics(facts, e, info, watch, pre, sim)


def honest_sell_mods(chain, owner, out=900_000, native=-(AMOUNT + 10_000)):
    chain.mods[owner] = delta_native(native)
    chain.mods[tv.ata_address(owner, USDC_MINT)] = delta_token(out, USDC_MINT, owner)


def test_honest_sol_to_usdc_economics_pass(owner):
    chain, facts, e, info = econ_setup(owner)
    honest_sell_mods(chain, owner)
    problems, ev = run_econ(chain, facts, e, info)
    assert problems == [], problems
    assert ev["output_token_delta_raw"] == 900_000 and ev["native_delta_lamports"] == -(AMOUNT + 10_000)


def test_honest_usdc_to_sol_economics_pass(owner):
    chain, facts, e, info = econ_setup(owner, USDC_MINT, WSOL_MINT, 1_000_000, 11_000_000)
    chain.mods[owner] = delta_native(11_100_000 - 10_000)  # receives 0.0111 SOL, pays the fee
    chain.mods[tv.ata_address(owner, USDC_MINT)] = delta_token(-1_000_000, USDC_MINT, owner)
    problems, _ = run_econ(chain, facts, e, info)
    assert problems == [], problems


def test_simulation_error_refuses(owner):
    chain, facts, e, info = econ_setup(owner)
    chain.sim_err = {"InstructionError": [3, {"Custom": 6001}]}
    problems, _ = run_econ(chain, facts, e, info)
    assert has(problems, "simulation failed")


def test_output_below_min_out_refuses(owner):
    chain, facts, e, info = econ_setup(owner)
    honest_sell_mods(chain, owner, out=MIN_OUT - 1)
    problems, _ = run_econ(chain, facts, e, info)
    assert has(problems, "below minOut")


def test_balance_delta_mismatch_input_token_refuses(owner):
    chain, facts, e, info = econ_setup(owner, USDC_MINT, WSOL_MINT, 1_000_000, 11_000_000)
    chain.mods[owner] = delta_native(11_100_000 - 10_000)
    chain.mods[tv.ata_address(owner, USDC_MINT)] = delta_token(-1_500_000, USDC_MINT, owner)  # takes more than quoted
    problems, _ = run_econ(chain, facts, e, info)
    assert has(problems, "expected exactly -1000000")


def test_sol_drain_beyond_input_and_fee_refuses(owner):
    chain, facts, e, info = econ_setup(owner)
    honest_sell_mods(chain, owner, native=-(AMOUNT + 10_000 + 3_000_000))
    problems, _ = run_econ(chain, facts, e, info)
    assert has(problems, "more than input + fee + rent")


def test_sol_drain_when_selling_a_token_refuses(owner):
    chain, facts, e, info = econ_setup(owner, USDC_MINT, WSOL_MINT, 1_000_000, 11_000_000)
    chain.mods[owner] = delta_native(11_100_000 - 10_000 - 400_000)  # output arrives but 0.0004 SOL goes missing
    chain.mods[tv.ata_address(owner, USDC_MINT)] = delta_token(-1_000_000, USDC_MINT, owner)
    problems, _ = run_econ(chain, facts, e, info)
    assert has(problems, "below minOut")


def test_input_not_spent_refuses(owner):
    chain, facts, e, info = econ_setup(owner)
    honest_sell_mods(chain, owner, native=-10_000)  # only the fee leaves: the quote's input is not being paid
    problems, _ = run_econ(chain, facts, e, info)
    assert has(problems, "is not being spent")


def test_third_party_wallet_lamports_moving_refuses(owner):
    chain, facts, e, info = econ_setup(owner)
    honest_sell_mods(chain, owner)
    bad_ix = list(swap_instructions(owner, WSOL_MINT, USDC_MINT, AMOUNT))
    bad_ix[-2] = ix(
        tv.JUPITER_V6, jupiter_ix(owner, WSOL_MINT, USDC_MINT).data,
        meta(owner, True, False), meta(ATTACKER, False, True),
    )  # fmt: skip
    tx = make_tx(bad_ix, owner)
    facts = tv.inspect_tx(tx, {})
    chain.state[ATTACKER] = wallet_account(5_000)
    chain.mods[ATTACKER] = delta_native(+999)
    e2 = exp(owner)
    problems, info2 = tv.check_static(facts, e2)
    assert problems == []
    p2, _ = run_econ(chain, facts, e2, info2)
    assert has(p2, "a third party is paid")


def test_touching_an_owner_token_account_outside_the_swap_refuses(owner):
    chain, facts, e, info = econ_setup(owner)
    victim = tv.ata_address(owner, OTHER_MINT)
    chain.state[victim] = token_account(OTHER_MINT, owner, 50_000_000)
    bad_ix = list(swap_instructions(owner, WSOL_MINT, USDC_MINT, AMOUNT))
    bad_ix[-2] = ix(
        tv.JUPITER_V6, jupiter_ix(owner, WSOL_MINT, USDC_MINT).data,
        meta(owner, True, False), meta(victim, False, True),
    )  # fmt: skip
    facts = tv.inspect_tx(make_tx(bad_ix, owner), {})
    honest_sell_mods(chain, owner)
    chain.mods[victim] = delta_token(-50_000_000, OTHER_MINT, owner)
    problems, info2 = tv.check_static(facts, e)
    assert problems == []
    p2, _ = run_econ(chain, facts, e, info2)
    assert has(p2, "touches the owner's token account")


def test_owner_token_account_changing_owner_refuses(owner):
    chain, facts, e, info = econ_setup(owner)
    honest_sell_mods(chain, owner)
    usdc_ata = tv.ata_address(owner, USDC_MINT)
    base = delta_token(900_000, USDC_MINT, owner)

    def stolen(acc):
        out = base(acc)
        data = bytearray(out["data"])
        data[32:64] = bytes(Keypair.from_seed(bytes([66] * 32)).pubkey())
        return {**out, "data": bytes(data)}

    chain.mods[usdc_ata] = stolen
    problems, _ = run_econ(chain, facts, e, info)
    assert has(problems, "changes owner")


def test_sol_reserve_breach_refuses(owner):
    chain, facts, e, info = econ_setup(owner)
    chain.state[owner] = wallet_account(AMOUNT + 10_000 + 4_000_000)  # would leave 4,000,000 < 5,000,000
    honest_sell_mods(chain, owner)
    problems, _ = run_econ(chain, facts, e, info)
    assert has(problems, "min_sol_reserve_lamports")


def test_retained_ata_rent_is_accounted_not_ignored(owner):
    ixs = swap_instructions(owner, USDC_MINT, WSOL_MINT, 1_000_000)
    chain, facts, e, info = econ_setup(owner, USDC_MINT, WSOL_MINT, 1_000_000, 11_000_000, instructions=ixs)
    wsol_ata = tv.ata_address(owner, WSOL_MINT)
    # The wSOL ATA persists after the swap (a route that does not close it): its rent is retained, not lost.
    chain.mods[wsol_ata] = lambda acc: token_account(WSOL_MINT, owner, 0)
    chain.mods[owner] = delta_native(11_100_000 - 10_000 - 2_039_280)
    chain.mods[tv.ata_address(owner, USDC_MINT)] = delta_token(-1_000_000, USDC_MINT, owner)
    problems, ev = run_econ(chain, facts, e, info)
    assert ev["retained_rent_lamports"] == 2_039_280
    assert problems == [], problems


def test_lookup_table_account_parse_roundtrip():
    tx, tables = real_tx_and_tables()
    facts = tv.inspect_tx(tx, tables)
    assert len(facts.keys) > len(facts.static_keys)
    assert tv.message_hash(tx) == tv.message_hash(tx)
