# Current YOLO open verifier

The current-format open verifier accepts a deliberately narrow observed transaction: one Pyth Lazer `UpdatePrice`, one SDK 0.6.0 `OpenPosition`, and bounded compute-budget instructions. It pins the observed upgradeable YOLO and Pyth ProgramData account hashes and slots. It allows the observed service signer or the live Config keeper, verifies the canonical signed BTC/ZEC Pyth feed against the currently unexpired on-chain trusted ECDSA signer, and checks the exact market, price PDA, intent and account bindings. It simulates the original unsigned message and blockhash, then checks the position, price, collateral and lamport deltas. The verifier repeats these checks before execution. RPC errors, changed deployment pins and unsupported layouts fail closed.

This is an experimental known subset, not a source verification of the deployed YOLO or Pyth binaries. Both programs are upgradeable: a hash read cannot atomically prevent an upgrade after verification. Simulation does not guarantee a later fill or state. RPC providers can lag or rate-limit; a concurrent price update may cause the exact post-state check to refuse a build. No live funded transaction has been tested by this verifier. The current two-instruction close is blocked because claim and payout authorization are not established; the earlier legacy verifier is unchanged.

The Pyth envelope and payload layout follows the public Pyth Lazer protocol source pinned at commit `f8c8a9565c77953124369c73b9195a10449a2075`:

- https://github.com/pyth-network/pyth-lazer-public/blob/f8c8a9565c77953124369c73b9195a10449a2075/sdk/rust/protocol/src/message.rs
- https://github.com/pyth-network/pyth-lazer-public/blob/f8c8a9565c77953124369c73b9195a10449a2075/sdk/rust/protocol/src/payload/standard.rs
- https://github.com/pyth-network/pyth-lazer-public/blob/f8c8a9565c77953124369c73b9195a10449a2075/contracts/solana/programs/pyth-lazer-solana-contract/src/lib.rs

`@noble/curves` 1.9.7 and `@noble/hashes` 1.8.0 are exact direct SDK dependencies used for secp256k1 recovery and Keccak. Both packages use the MIT license. Their public APIs are documented at https://github.com/paulmillr/noble-curves/tree/1.9.7 and https://github.com/paulmillr/noble-hashes/tree/1.8.0 . The package advisory requested a dependency reviewer, but that tool was unavailable in this session; independent dependency and security review remains required before merging or funded use.
