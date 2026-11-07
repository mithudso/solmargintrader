/**
 * Chains, endpoints and the known-token lists the market reads use.
 *
 * Base: chain id 8453 (0x2105), public RPC https://mainnet.base.org
 * (docs.base.org network table), with base-rpc.publicnode.com first because
 * soltui/wallet.py found it less throttled. Since Denim (Base mainnet,
 * 2026-11-05) the `pending` tag no longer returns preconfirmation state, so
 * every read here uses `latest`.
 *
 * Token addresses are the ones soltui/wallet.py KNOWN_BASE_TOKENS and
 * liquidity/src/aero_lp/metrics.py KNOWN_TOKENS already agree on. Without an
 * indexer, a token outside this list cannot be discovered by balanceOf alone;
 * the holdings read says so instead of implying it saw everything, and the
 * soltui deep scan (portfolio.scan) covers the rest.
 */

export const BASE = Object.freeze({
  chainId: 8453,
  chainIdHex: '0x2105',
  rpcs: Object.freeze(['https://base-rpc.publicnode.com', 'https://mainnet.base.org']),
  explorer: 'https://basescan.org',
  // Aero Slipstream CLFactory, from liquidity/src/aero_lp/addresses.py, where
  // it is held to that file's two-independent-sources rule.
  clFactory: '0x9CB220581b91b0C83223012FE69688b92aD07a76',
});

export const SOLANA = Object.freeze({
  rpcs: Object.freeze(['https://api.mainnet-beta.solana.com']),
  explorer: 'https://solscan.io',
  tokenProgram: 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',
  token2022Program: 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb',
  wsol: 'So11111111111111111111111111111111111111112',
});

export const ENDPOINTS = Object.freeze({
  llamaPrices: 'https://coins.llama.fi/prices/current/',
  llamaYields: 'https://yields.llama.fi/pools',
  jupiterPrice: 'https://lite-api.jup.ag/price/v3',
  // Metis Swap API: quotes only. The swap itself is signed on jup.ag.
  jupiterQuote: 'https://lite-api.jup.ag/swap/v1/quote',
  // Ultra API holdings: a read of the wallet's token accounts. Used because the
  // public Solana RPC answers 403 to any request carrying an extension Origin.
  jupiterHoldings: 'https://lite-api.jup.ag/ultra/v1/holdings/',
});

/** Base URLs of the Jupiter APIs above, for the licence attribution (src/jupiter/attribution.js). */
export const JUPITER_MARKET_BASES = Object.freeze({
  metis: 'https://lite-api.jup.ag/swap/v1',
  ultraHoldings: 'https://lite-api.jup.ag/ultra/v1/holdings',
});

/** Base ERC-20s checked by balanceOf. `native` marks the pseudo-entry for ETH. */
export const BASE_TOKENS = Object.freeze([
  { symbol: 'ETH', address: null, decimals: 18, native: true, stable: false },
  { symbol: 'WETH', address: '0x4200000000000000000000000000000000000006', decimals: 18, stable: false },
  { symbol: 'USDC', address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', decimals: 6, stable: true },
  { symbol: 'USDbC', address: '0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA', decimals: 6, stable: true },
  { symbol: 'USDT', address: '0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2', decimals: 6, stable: true },
  { symbol: 'DAI', address: '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb', decimals: 18, stable: true },
  { symbol: 'EURC', address: '0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42', decimals: 6, stable: false },
  { symbol: 'cbBTC', address: '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf', decimals: 8, stable: false },
  { symbol: 'cbETH', address: '0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22', decimals: 18, stable: false },
  { symbol: 'wstETH', address: '0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452', decimals: 18, stable: false },
  { symbol: 'weETH', address: '0x04C0599Ae5A44757c0af6F9eC3b93da8976c150A', decimals: 18, stable: false },
  { symbol: 'rETH', address: '0xB6fe221Fe9EeF5aBa221c348bA20A1Bf5e73624c', decimals: 18, stable: false },
  { symbol: 'AERO', address: '0x3f5bF3EdAc59d650D8fDf9657a71F2f904A3a4Ee', decimals: 18, stable: false },
]);

/** Solana mints offered in the swap picker. Holdings list every mint the wallet holds. */
export const SOLANA_TOKENS = Object.freeze([
  { symbol: 'SOL', address: 'So11111111111111111111111111111111111111112', decimals: 9, stable: false },
  { symbol: 'USDC', address: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', decimals: 6, stable: true },
  { symbol: 'USDT', address: 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB', decimals: 6, stable: true },
  { symbol: 'JitoSOL', address: 'J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn', decimals: 9, stable: false },
  { symbol: 'mSOL', address: 'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So', decimals: 9, stable: false },
  { symbol: 'JupSOL', address: 'jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v', decimals: 9, stable: false },
  { symbol: 'JUP', address: 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN', decimals: 6, stable: false },
]);

export const CHAINS = Object.freeze(['base', 'solana']);

export const tokensFor = (chain) => (chain === 'base' ? BASE_TOKENS : chain === 'solana' ? SOLANA_TOKENS : []);

/** Look a token up by symbol or address on one chain. Case-insensitive; null when unknown. */
export function findToken(chain, ref) {
  if (typeof ref !== 'string' || !ref.trim()) return null;
  const want = ref.trim();
  const lower = want.toLowerCase();
  return tokensFor(chain).find((t) =>
    t.symbol.toLowerCase() === lower || (t.address && (chain === 'base' ? t.address.toLowerCase() === lower : t.address === want)),
  ) ?? null;
}

const SOLANA_ADDRESS = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
export const isSolanaAddress = (value) => typeof value === 'string' && SOLANA_ADDRESS.test(value);
