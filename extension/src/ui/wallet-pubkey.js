/**
 * "Use soltui Solana address": fill the Wallet pubkey field from the address saved in soltui.
 *
 * The address comes through the same bridge as every other soltui call: the page sends `soltuiCall` for the
 * read-only `wallet.addresses` command, which returns the public Solana and EVM addresses and nothing else
 * (never an extended public key, never key material). The reply is checked here as a Solana pubkey before
 * it touches the field. The page does not save it: the owner still clicks Save, and nothing in this file
 * writes chrome.storage. Messages and results are written with textContent only.
 */

import { base58Decode } from '../wallet/solana.js';

const B58 = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;

/** True for a Solana public key: Base58 that decodes to exactly 32 bytes. */
export function isSolanaPubkey(text) {
  if (typeof text !== 'string' || !B58.test(text)) return false;
  try {
    return base58Decode(text).length === 32;
  } catch {
    return false;
  }
}

/**
 * Ask soltui for the saved Solana address.
 * `send` is the extension's message function ({ ok, result: <soltui envelope> } | { ok:false, error }).
 * Returns { ok:true, address } or { ok:false, message } with a sentence for the person at the form.
 */
export async function fetchSolanaAddress(send) {
  let res;
  try {
    res = await send({ type: 'soltuiCall', command: 'wallet.addresses', params: {} });
  } catch (err) {
    return { ok: false, message: `Could not reach the extension: ${err.message}` };
  }
  const envelope = res?.result;
  if (!res?.ok || !envelope?.ok) {
    return { ok: false, message: envelope?.error?.message ?? res?.error ?? 'soltui is not available.' };
  }
  const address = envelope.result?.solana_address;
  if (typeof address !== 'string' || address === '') {
    return { ok: false, message: 'soltui has no Solana address saved. Add one in the SolTUI Settings tab.' };
  }
  if (!isSolanaPubkey(address)) {
    return { ok: false, message: 'The address soltui returned is not a valid Solana public key, so it was not used.' };
  }
  return { ok: true, address };
}

/** Wire the button. Fills the field and says so; never submits or saves. */
export function mountWalletPubkeyButton(root, send) {
  const button = root.querySelector('#useSoltuiAddress');
  const field = root.querySelector('#configForm [name="userPubkey"]');
  const status = root.querySelector('#useSoltuiStatus');
  if (!button || !field || !status) return;
  button.addEventListener('click', async () => {
    button.disabled = true;
    status.textContent = 'Asking soltui…';
    try {
      const out = await fetchSolanaAddress(send);
      if (out.ok) {
        field.value = out.address;
        field.dispatchEvent(new Event('input', { bubbles: true }));
        status.textContent = 'Filled from soltui. Click Save to keep it.';
      } else {
        status.textContent = out.message;
      }
    } finally {
      button.disabled = false;
    }
  });
}
