"""BIP32 public derivation, address encoding and the refusal of private keys, on published test vectors.

Every key here is a public test vector from BIP32 or BIP84, or is built in the test from filler bytes. None
is a real wallet.
"""

from __future__ import annotations

import json
import struct
import unittest

from soltui import hdwallet as h

# BIP32 test vector 2 (master) and its first non-hardened child; vector 1 m/0H and its child m/0H/1.
V2_M = "xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB"
V2_M0 = "xpub69H7F5d8KSRgmmdJg2KhpAK8SR3DjMwAdkxj3ZuxV27CprR9LgpeyGmXUbC6wb7ERfvrnKZjXoUmmDznezpbZb7ap6r1D3tgFxHmwMkQTPH"
V1_M0H = "xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw"
V1_M0H_1 = "xpub6ASuArnXKPbfEwhqN6e3mwBcDTgzisQN1wXN9BJcM47sSikHjJf3UFHKkNAWbWMiGj7Wf5uMash7SyYq527Hqck2AxYysAA7xmALppuCkwQ"
# BIP84 vector: account-0 zpub of the "abandon ... about" mnemonic and its first addresses.
BIP84_ZPUB = "zpub6rFR7y4Q2AijBEqTUquhVz398htDFrtymD9xYYfG1m4wAcvPhXNfE3EfH1r1ADqtfSdVCToUG868RvUUkgDKf31mGDtKsAYz2oz2AGutZYs"
BIP84_RECEIVE = ["bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu", "bc1qnjg0jd8228aq7egyzacy8cys3knf9xvrerkf9g"]
BIP84_CHANGE0 = "bc1q8c6fshw2dlwun7ekn9qwf37cu2rn755upcp6el"
G = bytes.fromhex("0279BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798")


def serialise(version: int, key: h.ExtendedPublicKey, index: int) -> str:
    raw = struct.pack(">I", version) + bytes([key.depth]) + b"\0\0\0\0" + struct.pack(">I", index) + key.chain_code + key.key
    return h.b58check_encode(raw)


class DerivationTests(unittest.TestCase):
    def test_child_matches_bip32_vector_2(self) -> None:
        master = h.parse_extended_key(V2_M, "btc")
        child = master.child(0)
        raw = (struct.pack(">I", 0x0488B21E) + bytes([1]) + h.hash160(master.key)[:4] + struct.pack(">I", 0)
               + child.chain_code + child.key)
        self.assertEqual(h.b58check_encode(raw), V2_M0)

    def test_child_matches_bip32_vector_1(self) -> None:
        parent = h.parse_extended_key(V1_M0H, "btc")
        child = parent.child(1)
        raw = (struct.pack(">I", 0x0488B21E) + bytes([2]) + h.hash160(parent.key)[:4] + struct.pack(">I", 1)
               + child.chain_code + child.key)
        self.assertEqual(h.b58check_encode(raw), V1_M0H_1)

    def test_bip84_addresses_from_a_zpub(self) -> None:
        key = h.parse_extended_key(BIP84_ZPUB, "btc")
        self.assertEqual(key.hint, "p2wpkh")
        got = [h.encode_address("btc", "p2wpkh", key.pubkey_at(0, i)) for i in (0, 1)]
        self.assertEqual(got, BIP84_RECEIVE)
        self.assertEqual(h.encode_address("btc", "p2wpkh", key.pubkey_at(1, 0)), BIP84_CHANGE0)

    def test_hardened_children_are_refused(self) -> None:
        with self.assertRaises(h.ExtKeyError):
            h.parse_extended_key(V2_M, "btc").child(0x80000000)


class AddressEncodingTests(unittest.TestCase):
    def test_bitcoin_styles_for_the_generator_point(self) -> None:
        self.assertEqual(h.encode_address("btc", "p2pkh", G), "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH")
        self.assertEqual(h.encode_address("btc", "p2sh-p2wpkh", G), "3JvL6Ymt8MVWiCNHC7oWU6nLeHNJKLZGLN")
        self.assertEqual(h.encode_address("btc", "p2wpkh", G), "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")

    def test_litecoin_and_dogecoin_use_their_own_prefixes(self) -> None:
        self.assertEqual(h.encode_address("ltc", "p2wpkh", G), "ltc1qw508d6qejxtdg4y5r3zarvary0c5xw7kgmn4n9")
        self.assertTrue(h.encode_address("ltc", "p2pkh", G).startswith("L"))
        self.assertTrue(h.encode_address("ltc", "p2sh-p2wpkh", G).startswith("M"))
        self.assertTrue(h.encode_address("doge", "p2pkh", G).startswith("D"))

    def test_dogecoin_has_no_segwit(self) -> None:
        with self.assertRaises(h.ExtKeyError):
            h.encode_address("doge", "p2wpkh", G)
        key = h.parse_extended_key(V2_M, "doge")
        self.assertEqual(h.script_types_for("doge", key), ("p2pkh",))

    def test_plain_xpub_tries_every_style_but_a_zpub_only_its_own(self) -> None:
        self.assertEqual(h.script_types_for("btc", h.parse_extended_key(V2_M, "btc")),
                         ("p2pkh", "p2sh-p2wpkh", "p2wpkh"))
        self.assertEqual(h.script_types_for("btc", h.parse_extended_key(BIP84_ZPUB, "btc")), ("p2wpkh",))

    def test_pure_ripemd160_agrees_with_the_library_vector(self) -> None:
        self.assertEqual(h._ripemd160_pure(b"a").hex(), "0bdc9d2d256b3ee9daae347be6f4dc835a467ffe")
        self.assertEqual(h._ripemd160_pure(b"").hex(), "9c1185a5c5e9fc54612808977ee8f548b2258d31")
        data = bytes(range(200))
        self.assertEqual(h._ripemd160_pure(data), h.ripemd160(data))


class ValidationTests(unittest.TestCase):
    def test_a_good_key_parses_and_redacts(self) -> None:
        self.assertEqual(h.parse_extended_key(V2_M, "ltc").coin, "ltc")
        self.assertEqual(h.redact(V2_M), "xpub66…")
        self.assertNotIn(V2_M[8:], h.redact(V2_M))

    def test_a_mistyped_character_fails_the_checksum(self) -> None:
        bad = V2_M[:-1] + ("A" if V2_M[-1] != "A" else "B")
        with self.assertRaisesRegex(h.ExtKeyError, "checksum"):
            h.parse_extended_key(bad, "btc")

    def test_wrong_length_and_version_and_coin(self) -> None:
        with self.assertRaisesRegex(h.ExtKeyError, "length"):
            h.parse_extended_key(h.b58check_encode(b"\x04\x88\xb2\x1e" + b"\1" * 40), "btc")
        key = h.parse_extended_key(V2_M, "btc")
        testnet = serialise(0x043587CF, key, 0)
        with self.assertRaisesRegex(h.ExtKeyError, "testnet"):
            h.parse_extended_key(testnet, "btc")
        doge_only = serialise(0x02FACAFD, key, 0)
        with self.assertRaisesRegex(h.ExtKeyError, "another coin"):
            h.parse_extended_key(doge_only, "btc")
        self.assertEqual(h.parse_extended_key(doge_only, "doge").coin, "doge")

    def test_a_point_off_the_curve_is_refused(self) -> None:
        key = h.parse_extended_key(V2_M, "btc")
        raw = struct.pack(">I", 0x0488B21E) + bytes([0]) + b"\0" * 8 + key.chain_code + b"\x02" + b"\xff" * 32
        with self.assertRaisesRegex(h.ExtKeyError, "curve"):
            h.parse_extended_key(h.b58check_encode(raw), "btc")

    def test_every_kind_of_private_key_is_refused_without_echoing_it(self) -> None:
        filler = bytes([0x00]) + b"\x11" * 32
        xprv = h.b58check_encode(struct.pack(">I", 0x0488ADE4) + bytes([0]) + b"\0" * 8 + b"\x22" * 32 + filler)
        zprv = h.b58check_encode(struct.pack(">I", 0x04B2430C) + bytes([0]) + b"\0" * 8 + b"\x22" * 32 + filler)
        wif = h.b58check_encode(b"\x80" + b"\x11" * 32 + b"\x01")
        self.assertIn(wif[0], "5KL")
        samples = {
            "xprv": xprv, "zprv": zprv, "hex": "ab" * 32, "0xhex": "0x" + "cd" * 32, "wif": wif,
            "solana array": json.dumps(list(range(64))),
            "solana base58": h.b58encode(bytes(range(1, 65))),
        }
        for name, secret in samples.items():
            for fn, args in ((h.parse_extended_key, (secret, "btc")), (h.validate_evm_address, (secret,)),
                             (h.validate_solana_address, (secret,))):
                with self.subTest(kind=name, fn=fn.__name__):
                    with self.assertRaises(h.ExtKeyError) as ctx:
                        fn(*args)
                    msg = str(ctx.exception)
                    self.assertIn("Private keys do not belong in settings", msg)
                    self.assertNotIn(secret[:12], msg)

    def test_a_private_version_is_refused_even_when_the_prefix_text_is_unrecognised(self) -> None:
        filler = bytes([0x00]) + b"\x11" * 32
        odd = h.b58check_encode(struct.pack(">I", 0x019D9CFE) + bytes([0]) + b"\0" * 8 + b"\x22" * 32 + filler)
        with self.assertRaisesRegex(h.ExtKeyError, "private key"):
            h.parse_extended_key(odd, "ltc")

    def test_addresses(self) -> None:
        h.validate_evm_address("0x" + "ab" * 20)
        h.validate_solana_address("EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV")
        for bad in ("0x123", "ab" * 20, "0x" + "zz" * 20):
            with self.assertRaises(h.ExtKeyError):
                h.validate_evm_address(bad)
        for bad in ("nope", "0" * 44, "1" * 33):
            with self.assertRaises(h.ExtKeyError):
                h.validate_solana_address(bad)


if __name__ == "__main__":
    unittest.main()
