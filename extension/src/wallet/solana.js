/**
 * Minimal Solana wire-format helpers.
 *
 * Hand-rolled instead of pulling in @solana/web3.js because the extension needs
 * exactly two things — base58 and inserting a signature into an already-built
 * transaction — and shipping a megabyte of bundled dependencies into a service
 * worker for that is a poor trade.
 *
 * The transaction itself is always built by Jupiter; we never construct
 * instructions. That keeps this file to parsing far enough into the bytes to
 * find our signature slot.
 */

const B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
const B58_MAP = (() => {
  const m = new Map();
  for (let i = 0; i < B58_ALPHABET.length; i++) m.set(B58_ALPHABET[i], i);
  return m;
})();

export function base58Encode(bytes) {
  if (bytes.length === 0) return '';
  // Count leading zeros: each becomes a literal '1'.
  let zeros = 0;
  while (zeros < bytes.length && bytes[zeros] === 0) zeros++;

  // Starts empty, NOT [0]: seeding a zero digit emits a phantom leading '1',
  // so an all-zero input (the system program, an uninitialised pubkey) would
  // encode to 33 characters instead of 32.
  const digits = [];
  for (let i = zeros; i < bytes.length; i++) {
    let carry = bytes[i];
    for (let j = 0; j < digits.length; j++) {
      carry += digits[j] << 8;
      digits[j] = carry % 58;
      carry = (carry / 58) | 0;
    }
    while (carry > 0) {
      digits.push(carry % 58);
      carry = (carry / 58) | 0;
    }
  }

  let out = '1'.repeat(zeros);
  for (let i = digits.length - 1; i >= 0; i--) out += B58_ALPHABET[digits[i]];
  return out;
}

export function base58Decode(str) {
  if (str.length === 0) return new Uint8Array(0);
  let zeros = 0;
  while (zeros < str.length && str[zeros] === '1') zeros++;

  // Empty for the same reason as the encoder: '1'.repeat(32) must decode to 32
  // zero bytes, not 33.
  const bytes = [];
  for (let i = zeros; i < str.length; i++) {
    const value = B58_MAP.get(str[i]);
    if (value === undefined) throw new RangeError(`invalid base58 character "${str[i]}"`);
    let carry = value;
    for (let j = 0; j < bytes.length; j++) {
      carry += bytes[j] * 58;
      bytes[j] = carry & 0xff;
      carry >>= 8;
    }
    while (carry > 0) {
      bytes.push(carry & 0xff);
      carry >>= 8;
    }
  }

  const out = new Uint8Array(zeros + bytes.length);
  for (let i = 0; i < bytes.length; i++) out[zeros + i] = bytes[bytes.length - 1 - i];
  return out;
}

export function base64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export function bytesToBase64(bytes) {
  let bin = '';
  // Chunked to stay clear of the argument-count limit on large transactions.
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}

/**
 * Decode a compact-u16 ("shortvec") length prefix.
 * @returns {{value:number, size:number}}
 */
export function decodeShortVec(bytes, offset = 0) {
  let value = 0;
  let size = 0;
  for (;;) {
    if (offset + size >= bytes.length) throw new RangeError('truncated shortvec');
    const byte = bytes[offset + size];
    value |= (byte & 0x7f) << (size * 7);
    size += 1;
    if ((byte & 0x80) === 0) break;
    if (size > 3) throw new RangeError('shortvec longer than 3 bytes');
  }
  return { value, size };
}

export function encodeShortVec(value) {
  const out = [];
  let v = value;
  for (;;) {
    let byte = v & 0x7f;
    v >>= 7;
    if (v === 0) {
      out.push(byte);
      break;
    }
    out.push(byte | 0x80);
  }
  return Uint8Array.from(out);
}

/**
 * Split a serialized transaction into its signature array and message bytes.
 *
 * Layout: [shortvec sigCount][64 * sigCount signature bytes][message...]
 * The message is what gets signed, so it is returned as a subarray view.
 */
export function parseTransaction(txBytes) {
  const { value: sigCount, size } = decodeShortVec(txBytes, 0);
  const sigStart = size;
  const messageStart = sigStart + sigCount * 64;
  if (messageStart > txBytes.length) throw new RangeError('truncated signature array');

  const signatures = [];
  for (let i = 0; i < sigCount; i++) {
    signatures.push(txBytes.subarray(sigStart + i * 64, sigStart + (i + 1) * 64));
  }

  return {
    sigCount,
    sigStart,
    signatures,
    message: txBytes.subarray(messageStart),
    messageStart,
  };
}

/**
 * The signer pubkeys of a transaction message, in signature-slot order.
 *
 * Handles both legacy and v0 messages: a v0 message starts with a version byte
 * that has the high bit set, which a legacy message's first byte (the number of
 * required signatures, always < 128) never does.
 */
export function messageSigners(message) {
  let o = 0;
  const versioned = (message[0] & 0x80) !== 0;
  if (versioned) o += 1;

  const numRequiredSignatures = message[o];
  o += 3; // numRequiredSignatures, numReadonlySigned, numReadonlyUnsigned

  const { value: numKeys, size } = decodeShortVec(message, o);
  o += size;
  if (numRequiredSignatures > numKeys) throw new RangeError('more signers than account keys');

  const signers = [];
  for (let i = 0; i < numRequiredSignatures; i++) {
    const start = o + i * 32;
    if (start + 32 > message.length) throw new RangeError('truncated account keys');
    signers.push(base58Encode(message.subarray(start, start + 32)));
  }
  return { signers, versioned, numRequiredSignatures, numKeys };
}

/**
 * Write a signature into the slot belonging to `pubkeyBs58`.
 *
 * Returns a new byte array; the input is not mutated, so a failed sign attempt
 * cannot leave a half-signed transaction behind.
 */
export function withSignature({ txBytes, pubkeyBs58, signature }) {
  if (signature.length !== 64) {
    throw new RangeError(`signature must be 64 bytes, got ${signature.length}`);
  }
  const parsed = parseTransaction(txBytes);
  const { signers } = messageSigners(parsed.message);
  const index = signers.indexOf(pubkeyBs58);
  if (index === -1) {
    throw new Error(
      `${pubkeyBs58} is not a required signer of this transaction (signers: ${signers.join(', ')})`,
    );
  }

  const out = Uint8Array.from(txBytes);
  out.set(signature, parsed.sigStart + index * 64);
  return out;
}
