/**
 * The small slice of EVM ABI encoding the market reads need, in BigInt.
 *
 * Kept by hand rather than pulling in viem or ethers: the extension has zero
 * runtime dependencies (CLAUDE.md, house style), and the reads here are a
 * handful of fixed-shape view calls. Selectors are the first four bytes of the
 * keccak-256 of the signature; each one below was computed with web3.py's
 * Web3.keccak and is checked against a live call in test/market.test.js
 * fixtures.
 */

export const SELECTOR = Object.freeze({
  balanceOf: '0x70a08231', // balanceOf(address)
  decimals: '0x313ce567', // decimals()
  symbol: '0x95d89b41', // symbol()
  getPool: '0x28af8d0b', // getPool(address,address,int24) — Slipstream CLFactory
  tickSpacings: '0x9cbbbe86', // tickSpacings() — Slipstream CLFactory
  slot0: '0x3850c7bd', // slot0() — Slipstream pool: (sqrtPriceX96, tick, ...)
  liquidity: '0x1a686502', // liquidity()
  fee: '0xddca3f43', // fee() — uint24 in hundredths of a basis point
});

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;

export const isAddress = (value) => typeof value === 'string' && ADDRESS.test(value);

/** Left-pad an address to one 32-byte ABI word (no 0x). */
export function word(address) {
  if (!isAddress(address)) throw new TypeError('not an EVM address');
  return address.slice(2).toLowerCase().padStart(64, '0');
}

/** A signed integer (int24 and friends) as one two's-complement ABI word. */
export function intWord(n) {
  const v = BigInt(n);
  const twos = v < 0n ? (1n << 256n) + v : v;
  return twos.toString(16).padStart(64, '0');
}

const HEX = /^0x[0-9a-fA-F]*$/;

/** A JSON-RPC quantity or data string as BigInt; null for anything that is not hex. */
export function hexToBigInt(hex) {
  return typeof hex === 'string' && HEX.test(hex) && hex.length > 2 ? BigInt(hex) : null;
}

/** The 32-byte words of an ABI return value, as BigInt. Empty for `0x` or non-hex. */
export function words(hex) {
  // An endpoint answering junk must not throw a SyntaxError out of BigInt and
  // take the other chain's read down with it.
  if (typeof hex !== 'string' || !HEX.test(hex)) return [];
  const body = hex.slice(2);
  const out = [];
  for (let i = 0; i + 64 <= body.length; i += 64) out.push(BigInt(`0x${body.slice(i, i + 64)}`));
  return out;
}

/** Unsigned integer result, or null when the call returned nothing usable. */
export function uint(hex) {
  const w = words(hex);
  return w.length ? w[0] : null;
}

/** Interpret a word as a signed integer of `bits` width. */
export function signed(value, bits = 256) {
  const v = BigInt.asUintN(bits, value);
  return v >= 1n << BigInt(bits - 1) ? v - (1n << BigInt(bits)) : v;
}

/** An ABI-encoded address return value. */
export function addressOf(hex) {
  const w = uint(hex);
  if (w === null) return null;
  return `0x${w.toString(16).padStart(40, '0')}`;
}

export const ZERO_ADDRESS = '0x0000000000000000000000000000000000000000';

/** A dynamic `int24[]` (or any int array) return value. */
export function intArray(hex) {
  const w = words(hex);
  if (w.length < 2) return [];
  const offset = Number(w[0] / 32n);
  const length = Number(w[offset] ?? 0n);
  return w.slice(offset + 1, offset + 1 + length).map((x) => Number(signed(x, 24)));
}

/**
 * ABI string, or the bytes32 some old tokens return. Null when it is neither.
 * Token names are untrusted data: callers render them with textContent only.
 */
export function abiString(hex) {
  if (typeof hex !== 'string' || !hex.startsWith('0x') || hex.length < 66) return null;
  const bytes = hexBytes(hex.slice(2));
  const decode = (arr) => new TextDecoder('utf-8', { fatal: false }).decode(arr).replace(/\u0000+$/, '');
  if (bytes.length >= 96) {
    const len = Number(BigInt(`0x${hex.slice(2 + 64, 2 + 128)}`));
    if (len > 0 && len <= bytes.length - 64) return decode(bytes.slice(64, 64 + len)) || null;
  }
  return decode(bytes.slice(0, 32)) || null;
}

function hexBytes(hex) {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  return out;
}

/** Base units (BigInt) to a decimal number. Loses precision past ~15 digits, which a display can afford. */
export function toUnits(raw, decimals) {
  if (raw == null) return null;
  const v = BigInt(raw);
  const scale = 10n ** BigInt(decimals);
  const whole = v / scale;
  const frac = v % scale;
  return Number(whole) + Number(frac) / Number(scale);
}

/**
 * A decimal string to base units, exactly. "1.5" with 6 decimals is 1500000n.
 * Refuses more fractional digits than the token has, rather than rounding a
 * user's amount behind their back.
 */
export function fromUnits(text, decimals) {
  const s = String(text).trim();
  if (!/^\d+(\.\d+)?$/.test(s)) throw new RangeError('amount must be a plain positive decimal');
  const [whole, frac = ''] = s.split('.');
  if (frac.length > decimals) throw new RangeError(`amount has more than ${decimals} decimal places`);
  return BigInt(whole) * 10n ** BigInt(decimals) + BigInt((frac + '0'.repeat(decimals)).slice(0, decimals) || '0');
}
