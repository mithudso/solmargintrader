# DefiLlama Verified `llms-full.txt` Entities: Risk, Hack & Elimination Analysis

## 1. High Risk / Fraud / Reserve Manipulation (Immediate Elimination Candidates)

| Entity Name | `llms-full.txt` URL | Risk Type | Details & Rationale for Elimination |
| :--- | :--- | :--- | :--- |
| **PinkSale** | [docs.pinksale.finance/llms-full.txt](https://docs.pinksale.finance/llms-full.txt) | **Scam/Rugpull Enabler** | Permissionless token launchpad notoriously used as the primary launch vehicle for thousands of honeypots, liquidity drains, and presale exit scams across EVM chains. Not a broken contract itself, but structurally synonymous with retail fraud. |
| **USDD** | [docs.usdd.io/llms-full.txt](https://docs.usdd.io/llms-full.txt) | **Reserve Manipulation / Depeg** | TRON/Justin Sun collateralized stablecoin. In August 2024, Justin Sun quietly withdrew **12,000 BTC (~$730M)** from USDD's backing reserves without TRON DAO Reserve approval. History of recurring depegs and arbitrary, opaque reserve management. |
| **WBTC** | [wbtc.network/llms-full.txt](https://wbtc.network/llms-full.txt) | **Custodial Governance Risk** | In August 2024, BitGo transferred custody control to BiT Global (affiliated with Justin Sun). Due to opacity and previous reserve controversies with TUSD/USDD: **MakerDAO/Sky voted to completely offboard WBTC** from collateral engines, and **Aave capped its LTV and onboarding**. |

---

## 2. Sanctions & Regulatory Blacklisting Exposure

| Entity Name | `llms-full.txt` URL | Risk Type | Details & Rationale |
| :--- | :--- | :--- | :--- |
| **Railgun** | [docs.railgun.org/llms-full.txt](https://docs.railgun.org/llms-full.txt) | **State Laundering Scrutiny (OFAC/FBI)** | Privacy ZK-SNARK protocol. Extensively investigated by the FBI and blockchain forensic firms (Elliptic) after North Korea’s **Lazarus Group** laundered tens of millions in stolen crypto (including funds from the $100M Harmony Horizon bridge exploit) through Railgun. Carries severe compliance, freezing, and blacklisting risk for institutional entities. |
| **Polymarket** | [docs.polymarket.com/llms-full.txt](https://docs.polymarket.com/llms-full.txt) | **CFTC Sanctions / US Ban** | Fined $1.4M by the US CFTC in 2022 for operating an unregistered derivatives platform; banned from US operations, with continuous federal DOJ/FBI inquiry. |

---

## 3. Major Historic Hacks (Exploited, Remediated, or Relaunched)

These protocols suffered catastrophic security exploits but have since recovered, compensated victims, or completely redesigned their architecture:

| Entity Name | `llms-full.txt` URL | Historical Loss | Exploit Mechanism & Remediation |
| :--- | :--- | :--- | :--- |
| **Euler Finance (Euler V2)** | [docs.euler.finance/llms-full.txt](https://docs.euler.finance/llms-full.txt) | **$197 Million** (March 2023) | Flash loan exploit in Euler V1's `donateToReserves` and liquidation logic. Attacker returned all funds after on-chain negotiation. Euler completely deprecated V1 and rebuilt the system from scratch as **Euler V2**. |
| **Curve Finance** | [docs.curve.finance/llms-full.txt](https://docs.curve.finance/llms-full.txt) | **$61.7 Million** (July 2023) + $140M Debt Liquidation (June 2024) | Reentrancy lock failure in legacy Vyper compilers (0.2.15–0.3.0) drained multiple liquidity pools (alETH, pETH, CRV/ETH). In June 2024, founder Michael Egorov's $140M CRV-backed debt position experienced a massive cascading liquidation across multiple lending protocols. |
| **Raydium AMM** | [docs.raydium.io/llms-full.txt](https://docs.raydium.io/llms-full.txt) | **$4.4 Million** (Dec 2022) | Trojan malware compromised the deployment administrator's private key, granting unauthorized access to withdraw pool liquidity. The protocol reimbursed affected pools from treasury funds and shifted authority to multisig. |
| **Yearn Finance** | [docs.yearn.fi/llms-full.txt](https://docs.yearn.fi/llms-full.txt) | **$11 Million** (Feb 2021) + $1.4M (Dec 2023) | Repeated flash loan arbitrage and accounting logic exploits across v1 DAI vault and legacy yUSDT contracts. |

---

## 4. Opaque Architecture & Point-Farming / Mercenary TVL

| Entity Name | `llms-full.txt` URL | Risk Type | Details |
| :--- | :--- | :--- | :--- |
| **Merlin's Seal (Merlin Chain)** | [docs.merlinchain.io/llms-full.txt](https://docs.merlinchain.io/llms-full.txt) | **Opaque Custody / Mercenary TVL** | Bitcoin L2 bridge criticized for high centralization, opaque multisig custody over locked BTC, and slow withdrawal friction following point farming events. |
| **Aster DEX / Bridge** | [docs.asterdex.com/llms-full.txt](https://docs.asterdex.com/llms-full.txt) | **Wash Volume / Opacity** | Offshore perpetual protocol exhibiting anomalous, rapid TVL spikes and frequent allegations of wash-trading driven by short-term token incentives. |
