"""Public-key-only BIP32 derivation and address encoding. Stdlib only, no private keys anywhere.

An extended PUBLIC key (xpub and its SLIP-132 cousins) is enough to derive every receive and change
address of a wallet, so the console can watch a wallet without ever holding anything that can spend.
This module is the whole of that: Base58Check, the secp256k1 point arithmetic CKDpub needs, and the
P2PKH, P2SH-P2WPKH and P2WPKH encoders for Bitcoin, Litecoin and Dogecoin.

## Private keys are refused, loudly

`parse_extended_key` and `refuse_private_material` reject an `xprv`-family key, a WIF key, a raw
64-hex string and a Solana secret-key array with a message that does not echo the value. Settings
must never be a place a spending key can land, by typo or by paste.

## Honest limits

* Hardened children cannot be derived from a public key. A wallet exported at its account level
  (`m/44'/0'/0'`, the usual xpub) has non-hardened receive (0) and change (1) chains below it, which
  is all this needs.
* The version bytes do not say which address style a wallet uses. `ypub`/`zpub`-style versions do
  (BIP49, BIP84) and a plain `xpub` does not; the caller tries each style for a plain one.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import struct
from dataclasses import dataclass

# -- secp256k1 ----------------------------------------------------------------------------------------

_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
      0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)

Point = "tuple[int, int] | None"


def _add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0]:
        if (a[1] + b[1]) % _P == 0:
            return None
        lam = 3 * a[0] * a[0] * pow(2 * a[1], -1, _P) % _P
    else:
        lam = (b[1] - a[1]) * pow(b[0] - a[0], -1, _P) % _P
    x = (lam * lam - a[0] - b[0]) % _P
    return x, (lam * (a[0] - x) - a[1]) % _P


def _mul(k: int, pt):
    out = None
    while k:
        if k & 1:
            out = _add(out, pt)
        pt = _add(pt, pt)
        k >>= 1
    return out


def _decompress(key: bytes):
    if len(key) != 33 or key[0] not in (2, 3):
        raise ExtKeyError("public key is not a 33-byte compressed point")
    x = int.from_bytes(key[1:], "big")
    if x >= _P:
        raise ExtKeyError("public key is not on the curve")
    y = pow((pow(x, 3, _P) + 7) % _P, (_P + 1) // 4, _P)
    if y * y % _P != (pow(x, 3, _P) + 7) % _P:
        raise ExtKeyError("public key is not on the curve")
    if (y & 1) != (key[0] & 1):
        y = _P - y
    return x, y


def _compress(pt) -> bytes:
    return bytes([2 + (pt[1] & 1)]) + pt[0].to_bytes(32, "big")


# -- Base58Check --------------------------------------------------------------------------------------

_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_INDEX = {c: i for i, c in enumerate(_ALPHABET)}


def b58encode(raw: bytes) -> str:
    n = int.from_bytes(raw, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = _ALPHABET[r] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + out


def b58decode(text: str) -> bytes:
    n = 0
    for ch in text:
        if ch not in _INDEX:
            raise ExtKeyError("not Base58 (a character is outside the alphabet)")
        n = n * 58 + _INDEX[ch]
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return b"\0" * (len(text) - len(text.lstrip("1"))) + body


def _checksum(raw: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(raw).digest()).digest()[:4]


def b58check_encode(payload: bytes) -> str:
    return b58encode(payload + _checksum(payload))


def b58check_decode(text: str) -> bytes:
    raw = b58decode(text)
    if len(raw) < 5 or _checksum(raw[:-4]) != raw[-4:]:
        raise ExtKeyError("Base58Check checksum does not match (a character was mistyped)")
    return raw[:-4]


# -- hashes -------------------------------------------------------------------------------------------


def _rol(x: int, n: int) -> int:
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF


def _ripemd160_pure(data: bytes) -> bytes:
    """RIPEMD-160 for builds whose OpenSSL has dropped it (OpenSSL 3 legacy provider)."""
    r1 = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 7, 4, 13, 1, 10, 6, 15, 3, 12, 0, 9, 5, 2, 14,
          11, 8, 3, 10, 14, 4, 9, 15, 8, 1, 2, 7, 0, 6, 13, 11, 5, 12, 1, 9, 11, 10, 0, 8, 12, 4, 13, 3, 7, 15,
          14, 5, 6, 2, 4, 0, 5, 9, 7, 12, 2, 10, 14, 1, 3, 8, 11, 6, 15, 13]
    r2 = [5, 14, 7, 0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12, 6, 11, 3, 7, 0, 13, 5, 10, 14, 15, 8, 12, 4, 9,
          1, 2, 15, 5, 1, 3, 7, 14, 6, 9, 11, 8, 12, 2, 10, 0, 4, 13, 8, 6, 4, 1, 3, 11, 15, 0, 5, 12, 2, 13, 9,
          7, 10, 14, 12, 15, 10, 4, 1, 5, 8, 7, 6, 2, 13, 14, 0, 3, 9, 11]
    s1 = [11, 14, 15, 12, 5, 8, 7, 9, 11, 13, 14, 15, 6, 7, 9, 8, 7, 6, 8, 13, 11, 9, 7, 15, 7, 12, 15, 9, 11, 7,
          13, 12, 11, 13, 6, 7, 14, 9, 13, 15, 14, 8, 13, 6, 5, 12, 7, 5, 11, 12, 14, 15, 14, 15, 9, 8, 9, 14, 5,
          6, 8, 6, 5, 12, 9, 15, 5, 11, 6, 8, 13, 12, 5, 12, 13, 14, 11, 8, 5, 6]
    s2 = [8, 9, 9, 11, 13, 15, 15, 5, 7, 7, 8, 11, 14, 14, 12, 6, 9, 13, 15, 7, 12, 8, 9, 11, 7, 7, 12, 7, 6, 15,
          13, 11, 9, 7, 15, 11, 8, 6, 6, 14, 12, 13, 5, 14, 13, 13, 7, 5, 15, 5, 8, 11, 14, 14, 6, 14, 6, 9, 12,
          9, 12, 5, 15, 8, 8, 5, 12, 9, 12, 5, 14, 6, 8, 13, 6, 5, 15, 13, 11, 11]
    k1 = [0, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E]
    k2 = [0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x7A6D76E9, 0]

    def f(j: int, x: int, y: int, z: int) -> int:
        if j < 16:
            return x ^ y ^ z
        if j < 32:
            return (x & y) | (~x & 0xFFFFFFFF & z)
        if j < 48:
            return (x | (~y & 0xFFFFFFFF)) ^ z
        if j < 64:
            return (x & z) | (y & ~z & 0xFFFFFFFF)
        return x ^ (y | (~z & 0xFFFFFFFF))

    h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0]
    msg = data + b"\x80" + b"\0" * ((55 - len(data)) % 64) + struct.pack("<Q", len(data) * 8)
    for off in range(0, len(msg), 64):
        x = struct.unpack("<16I", msg[off:off + 64])
        a1, b1, c1, d1, e1 = h
        a2, b2, c2, d2, e2 = h
        for j in range(80):
            t = (_rol((a1 + f(j, b1, c1, d1) + x[r1[j]] + k1[j // 16]) & 0xFFFFFFFF, s1[j]) + e1) & 0xFFFFFFFF
            a1, e1, d1, c1, b1 = e1, d1, _rol(c1, 10), b1, t
            t = (_rol((a2 + f(79 - j, b2, c2, d2) + x[r2[j]] + k2[j // 16]) & 0xFFFFFFFF, s2[j]) + e2) & 0xFFFFFFFF
            a2, e2, d2, c2, b2 = e2, d2, _rol(c2, 10), b2, t
        t = (h[1] + c1 + d2) & 0xFFFFFFFF
        h = [t, (h[2] + d1 + e2) & 0xFFFFFFFF, (h[3] + e1 + a2) & 0xFFFFFFFF, (h[4] + a1 + b2) & 0xFFFFFFFF,
             (h[0] + b1 + c2) & 0xFFFFFFFF]
    return struct.pack("<5I", *h)


def ripemd160(data: bytes) -> bytes:
    try:
        return hashlib.new("ripemd160", data).digest()
    except ValueError:
        return _ripemd160_pure(data)


def hash160(data: bytes) -> bytes:
    return ripemd160(hashlib.sha256(data).digest())


# -- bech32 (BIP-173, witness version 0 only) ---------------------------------------------------------

_BECH = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _polymod(values: list[int]) -> int:
    gen = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    chk = 1
    for v in values:
        top = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= gen[i] if (top >> i) & 1 else 0
    return chk


def segwit_v0_address(hrp: str, program: bytes) -> str:
    """The bech32 address for a witness-v0 program (20 bytes for P2WPKH)."""
    acc, bits, data = 0, 0, [0]
    for byte in program:
        acc = (acc << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            data.append((acc >> bits) & 31)
    if bits:
        data.append((acc << (5 - bits)) & 31)
    expand = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
    mod = _polymod(expand + data + [0] * 6) ^ 1
    check = [(mod >> 5 * (5 - i)) & 31 for i in range(6)]
    return hrp + "1" + "".join(_BECH[d] for d in data + check)


# -- coins --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Coin:
    key: str
    name: str
    symbol: str
    p2pkh: int
    p2sh: int
    hrp: str | None  # None: the coin has no segwit addresses (Dogecoin)
    # Public extended-key version -> the address style it announces (None for a plain xpub).
    public_versions: dict[int, str | None]


XPUB, YPUB, ZPUB = 0x0488B21E, 0x049D7CB2, 0x04B24746
COINS: dict[str, Coin] = {
    "btc": Coin("btc", "Bitcoin", "BTC", 0x00, 0x05, "bc", {XPUB: None, YPUB: "p2sh-p2wpkh", ZPUB: "p2wpkh"}),
    "ltc": Coin("ltc", "Litecoin", "LTC", 0x30, 0x32, "ltc",
                {XPUB: None, 0x019DA462: None, 0x01B26EF6: "p2sh-p2wpkh", ZPUB: "p2wpkh"}),
    "doge": Coin("doge", "Dogecoin", "DOGE", 0x1E, 0x16, None, {XPUB: None, 0x02FACAFD: None}),
}
SCRIPT_TYPES = ("p2pkh", "p2sh-p2wpkh", "p2wpkh")

# Version bytes of PRIVATE extended keys and of testnet ones, only so they can be named and refused.
_PRIVATE_VERSIONS = {0x0488ADE4, 0x049D7878, 0x04B2430C, 0x04358394, 0x044A4E28, 0x045F18BC, 0x019D9CFE,
                     0x01B26792, 0x02FAC398}
_TESTNET_VERSIONS = {0x043587CF, 0x044A5262, 0x045F1CF6}


class ExtKeyError(ValueError):
    """A key or address that cannot be used. The message never contains the value itself."""


PRIVATE_MESSAGE = ("this looks like a private key. Private keys do not belong in settings: the console only "
                   "needs public addresses and public extended keys (xpub)")
_PRIVATE_PREFIXES = ("xprv", "yprv", "zprv", "tprv", "uprv", "vprv", "Ltpv", "Mtpv", "dgpv")


def refuse_private_material(text: str) -> None:
    """Raise ExtKeyError when `text` looks like any kind of spending key. Never echoes `text`."""
    t = text.strip()
    if t.startswith(_PRIVATE_PREFIXES):
        raise ExtKeyError(PRIVATE_MESSAGE)
    if re.fullmatch(r"(0x)?[0-9a-fA-F]{64}", t):
        raise ExtKeyError(PRIVATE_MESSAGE)
    if t.startswith("[") and t.endswith("]"):
        try:
            arr = json.loads(t)
        except ValueError:
            arr = None
        if isinstance(arr, list) and len(arr) in (32, 64) and all(isinstance(v, int) for v in arr):
            raise ExtKeyError(PRIVATE_MESSAGE)
    # A Solana secret key as Base58 is 64 bytes (87-88 characters); a WIF key is 51-52 characters.
    if re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{87,88}", t) or re.fullmatch(r"[5KL][1-9A-HJ-NP-Za-km-z]{50,51}", t):
        raise ExtKeyError(PRIVATE_MESSAGE)


@dataclass(frozen=True)
class ExtendedPublicKey:
    coin: str
    version: int
    hint: str | None  # the script type the version announces, or None
    depth: int
    chain_code: bytes
    key: bytes  # 33-byte compressed point

    def child(self, index: int) -> "ExtendedPublicKey":
        """CKDpub for a non-hardened `index`."""
        if index < 0 or index >= 0x80000000:
            raise ExtKeyError("a hardened child cannot be derived from a public key")
        digest = hmac.new(self.chain_code, self.key + struct.pack(">I", index), hashlib.sha512).digest()
        il = int.from_bytes(digest[:32], "big")
        if il >= _N:
            raise ExtKeyError("derived key is invalid for this index")
        point = _add(_mul(il, _G), _decompress(self.key))
        if point is None:
            raise ExtKeyError("derived key is invalid for this index")
        return ExtendedPublicKey(self.coin, self.version, self.hint, self.depth + 1, digest[32:], _compress(point))

    def pubkey_at(self, chain: int, index: int) -> bytes:
        return self.child(chain).child(index).key


def parse_extended_key(text: str, coin: str) -> ExtendedPublicKey:
    """Validate `text` as a public extended key for `coin`: Base58Check, 78 bytes, version bytes, a real point."""
    if coin not in COINS:
        raise ExtKeyError(f"unknown coin {coin!r}")
    spec = COINS[coin]
    t = (text or "").strip()
    if not t:
        raise ExtKeyError("empty")
    refuse_private_material(t)
    raw = b58check_decode(t)
    if len(raw) != 78:
        raise ExtKeyError("not an extended key (wrong length)")
    version = struct.unpack(">I", raw[:4])[0]
    if version in _PRIVATE_VERSIONS or raw[45] == 0:
        raise ExtKeyError(PRIVATE_MESSAGE)
    if version in _TESTNET_VERSIONS:
        raise ExtKeyError(f"this is a testnet key; {spec.name} needs a mainnet public key")
    if version not in spec.public_versions:
        raise ExtKeyError(f"the version bytes are not a {spec.name} public extended key "
                          "(a key for another coin was pasted?)")
    key = raw[45:78]
    _decompress(key)  # raises when the point is not on the curve
    return ExtendedPublicKey(coin, version, spec.public_versions[version], raw[4], raw[13:45], key)


def redact(text: str) -> str:
    """A prefix safe to print: the first six characters and an ellipsis."""
    t = (text or "").strip()
    return "" if not t else t[:6] + "…"


def encode_address(coin: str, script: str, pubkey: bytes) -> str:
    spec = COINS[coin]
    h = hash160(pubkey)
    if script == "p2pkh":
        return b58check_encode(bytes([spec.p2pkh]) + h)
    if script == "p2sh-p2wpkh":
        return b58check_encode(bytes([spec.p2sh]) + hash160(b"\x00\x14" + h))
    if script == "p2wpkh":
        if spec.hrp is None:
            raise ExtKeyError(f"{spec.name} has no segwit addresses")
        return segwit_v0_address(spec.hrp, h)
    raise ExtKeyError(f"unknown script type {script!r}")


def script_types_for(coin: str, key: ExtendedPublicKey) -> tuple[str, ...]:
    """Which address styles to try. A plain xpub says nothing, so every style the coin has is tried."""
    if key.hint:
        return (key.hint,)
    return ("p2pkh",) if COINS[coin].hrp is None else SCRIPT_TYPES


def validate_evm_address(text: str) -> None:
    refuse_private_material(text)
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", text.strip()):
        raise ExtKeyError("not an Ethereum address (0x followed by 40 hex digits)")


def validate_solana_address(text: str) -> None:
    refuse_private_material(text)
    t = text.strip()
    if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", t):
        raise ExtKeyError("not a Solana address (32 to 44 Base58 characters)")
    if len(b58decode(t)) != 32:
        raise ExtKeyError("not a Solana address (it does not decode to 32 bytes)")
