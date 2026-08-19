# Architectural Design Specification: On-Chain Analytics Oracle & Blockchain Data Agent

**Document Version:** 1.0.0  
**Status:** Approved for Implementation  
**Target Platform:** Google Cloud BigQuery, Fetch.ai / ASI Agentverse, Python 3.11+  

---

## 1. Executive Summary & Research Purpose

The primary objective of this project is to build an empirical, reproducible **Blockchain Data Engineering & Analytics Agent** that systematically audits 10+ years of Bitcoin (BTC) and USD Coin (USDC) transaction history. The agent evaluates whether cryptocurrency has achieved organic adoption as an everyday medium of exchange (replacing fiat currency) or whether its utility remains confined to speculative store-of-value accumulation and automated decentralized finance (DeFi) loops.

Once the analytical datamarts and query engines are constructed, the agent is packaged as an autonomous **uAgent** and published to the **Artificial Superintelligence (ASI) Alliance's Agentverse** as a public, cost-protected **On-Chain Analytics Oracle**. This enables external researchers, trading agents, and DAO governance bots to query verified on-chain metrics without requiring their own BigQuery infrastructure or domain-specific SQL knowledge.

---

## 2. Core Research Hypotheses & Target Questions

The system is designed to provide empirical, data-backed answers to the following core questions:

```
                                  CORE RESEARCH INQUIRIES
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ 1. The Velocity & Micro-Payment Decay Hypothesis (Bitcoin):                            │
 │    Has the proportion of micro-payments (<$10, <$50, <$100) on Bitcoin L1 decayed      │
 │    systematically over the past decade as fees rose, cementing BTC solely as a         │
 │    non-transactional "Store of Value"?                                                 │
 ├────────────────────────────────────────────────────────────────────────────────────────┤
 │ 2. The Organic vs. Noise Hypothesis (USDC / Stablecoins):                             │
 │    What exact percentage of stablecoin volume represents genuine everyday commerce      │
 │    versus automated protocol noise (MEV bots, flash loans, arbitrage, CEX sweeps)?     │
 ├────────────────────────────────────────────────────────────────────────────────────────┤
 │ 3. The Counterparty Topology Hypothesis (EOA vs. Smart Contracts):                     │
 │    What fraction of stablecoin transfers occur between peer/merchant wallets (EOA-EOA) │
 │    versus programmatic smart contract interactions (DEX routers, lending pools)?       │
 ├────────────────────────────────────────────────────────────────────────────────────────┤
 │ 4. The Layer 2 Retail Migration Hypothesis:                                           │
 │    Did everyday retail commerce migrate to low-fee Layer 2 networks (Base, Polygon,    │
 │    Arbitrum) or did retail transactional adoption fail to materialize entirely?        │
 ├────────────────────────────────────────────────────────────────────────────────────────┤
 │ 5. Cold Storage vs. Active Velocity Heuristics:                                        │
 │    Can behavioral heuristics (dormancy, UTXO age bands) distinguish long-term cold     │
 │    storage patterns from active transactional wallets?                                 │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Literature Gap Analysis: Where Prior Analyses Fell Short

While several organizations have touched upon crypto adoption, existing reports leave critical methodology gaps that this project directly resolves:

| Study / Institution | Previous Approach & Limitations | How This Project Overcomes It |
| :--- | :--- | :--- |
| **Federal Reserve (SHED Reports)** | Relies exclusively on consumer self-reporting surveys. Lacks granular, verifiable on-chain behavioral data. | **Empirical Blockchain Ground Truth:** Measures actual UTXO spend patterns, transaction sizes, and counterparty entities directly from the ledger. |
| **Visa / Artemis / Allium** | Published aggregated macro dashboards and filtered high-level metrics, but keep underlying classification datasets and custom ETL logic closed-source. | **100% Open & Reproducible SQL:** Fully open-source, parameterized BigQuery scripts that allow any researcher to audit the exact filtering logic. |
| **Chainalysis / TRM Labs** | Proprietary clustering algorithms and closed-source enterprise software inaccessible to independent researchers and autonomous agents. | **Standardized Agent-to-Agent Protocol:** Exposes analytical models directly via an open uAgents protocol on ASI Agentverse. |
| **Qualitative Critiques (patio11, Molly White)** | Provide compelling economic theory and historical merchant case studies, but lack longitudinal quantitative SQL metrics. | **Mathematical Proof of Fee Drag:** Quantifies historical fee-to-value drag ratios across 10 years of transactions ($5–$50 retail baskets). |

---

## 4. System Architecture: The Curated Datamart Pattern

To ensure ongoing BigQuery operational costs remain strictly at **$0.00/month** within Google Cloud's Always-Free Tier (1 TB/month query allocation), the system decouples heavy raw-data processing from runtime user queries via the **Curated Datamart Pattern**.

```
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                               PHASE 1: BATCH ETL PIPELINE                              │
 │  (Executes once / periodically against Google Cloud BigQuery Public Blockchain Data)   │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
          `bigquery-public-data.crypto_bitcoin`       `bigquery-public-data.crypto_ethereum`
             (Blocks, Transactions, Inputs,              (Token Transfers for USDC Contract:
                     Outputs: ~1.5 TB)                         0xa0b8...: ~800 GB)
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             │
                                             │ Filter Noise, Calculate UTXO Ages,
                                             │ Bucket Transaction Sizes
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                      PHASE 2: CURATED ANALYTICAL DATAMART (< 25 MB)                    │
 │                       (Dataset: `crypto_analytics_mart` in User GCP)                   │
 ├───────────────────────────────────────────┬────────────────────────────────────────────┤
 │ `btc_daily_utxo_distribution`             │ Daily UTXO age bands (HODL waves), average │
 │                                           │ transaction sizes, velocity.               │
 ├───────────────────────────────────────────┼────────────────────────────────────────────┤
 │ `usdc_daily_organic_metrics`              │ Noise-filtered volume, organic transfer    │
 │                                           │ counts, retail vs whale size breakdown.    │
 ├───────────────────────────────────────────┼────────────────────────────────────────────┤
 │ `counterparty_topology_breakdown`         │ EOA-to-EOA (P2P/Merchant) vs EOA-to-       │
 │                                           │ Contract (DeFi/MEV) ratios.                │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             │ Scans < 5 MB per query (< $0.00003)
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                     PHASE 3: uAGENTS / AGENTVERSE ANALYTICS ORACLE                     │
 ├────────────────────────────────────────────────────────────────────────────────────────┤
 │  • In-Memory Leaky Bucket Rate Limiter (Max 5 req/min per agent)                       │
 │  • BigQuery Client with Hard Circuit Breakers (`maximum_bytes_billed = 50 MB`)         │
 │  • Gemini Flash Semantic Query Mapper (Maps NL -> Parameterized SQL)                   │
 │  • LRU Result Cache (Duplicate requests answered in 0ms with 0 BQ scans)               │
 │  • ASI Agentverse Registration & Almanac Manifest                                      │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Curated Datamart Schemas

### 5.1 `btc_daily_utxo_distribution`
Aggregates Bitcoin unspent outputs into standard HODL age bands:
* `date` (DATE, Partition Key): Calendar day (UTC).
* `total_active_utxos` (INT64): Count of distinct active UTXOs on that date.
* `band_under_1d` (FLOAT64): % of BTC supply unspent for < 24 hours.
* `band_1d_to_1w` (FLOAT64): % of BTC supply unspent for 1 day to 1 week.
* `band_1w_to_1m` (FLOAT64): % of BTC supply unspent for 1 week to 1 month.
* `band_1m_to_6m` (FLOAT64): % of BTC supply unspent for 1 month to 6 months.
* `band_6m_to_1y` (FLOAT64): % of BTC supply unspent for 6 months to 1 year.
* `band_1y_to_2y` (FLOAT64): % of BTC supply unspent for 1 to 2 years.
* `band_over_2y` (FLOAT64): % of BTC supply unspent for > 2 years (Dormant / Cold Storage).
* `micro_tx_count_under_10usd` (INT64): Transactions with output value < $10.
* `retail_tx_count_10_to_500usd` (INT64): Transactions between $10 and $500.
* `whale_tx_count_over_50kusd` (INT64): Transactions > $50,000.
* `avg_fee_usd` (FLOAT64): Average transaction fee in USD equivalent.

### 5.2 `usdc_daily_organic_metrics`
Applies the Visa/Artemis noise filter to USDC transfers:
* `date` (DATE, Partition Key): Calendar day (UTC).
* `raw_transfer_count` (INT64): Total ERC-20 transfer events.
* `raw_volume_usd` (NUMERIC): Total nominal volume transferred.
* `organic_transfer_count` (INT64): Transfers excluding high-frequency bots (>1,000 tx/month) and smart contract loops.
* `organic_volume_usd` (NUMERIC): Volume from organic transfers.
* `organic_volume_ratio` (FLOAT64): `organic_volume_usd / raw_volume_usd`.
* `retail_volume_under_500usd` (NUMERIC): Volume from transfers < $500.
* `eoa_to_eoa_volume_usd` (NUMERIC): Volume between Externally Owned Accounts (P2P/Commerce).
* `eoa_to_contract_volume_usd` (NUMERIC): Volume sent to smart contracts (DeFi/Trading).

---

## 6. Security Hardening & Cost Protection (Defense-in-Depth)

To prevent resource exhaustion, malicious quota draining, or script kiddie abuse on Agentverse:

```
[Incoming Request] ──► [Rate Limiter (Token Bucket)] ──► [Input Sanitizer & Schema Validator]
                                                                    │
                             ┌──────────────────────────────────────┘
                             ▼
                 [In-Memory LRU Cache Check]
                  ├── Match Found ──► Return Cached JSON (0ms, $0.00 BQ cost)
                  └── Cache Miss
                             │
                             ▼
                 [Strict Parameterized SQL Builder] (Zero dynamic string concatenation)
                             │
                             ▼
                 [BigQuery Client Execution]
                  ├── `maximum_bytes_billed = 50,000,000` (50 MB hard cap)
                  ├── `use_query_cache = true`
                  └── Read-Only GCP Service Account (roles/bigquery.dataViewer)
```

1. **Hard Byte Limit (`maximum_bytes_billed`):** Set to 50 MB on every BigQuery job configuration. If an unexpected query attempts to scan 51 MB, BigQuery rejects the job immediately without charging.
2. **Strict Query Parameterization:** Zero string formatting or dynamic SQL execution. Incoming queries are mapped to predefined SQL templates with strict type validation (`int`, `date`, `float`).
3. **Leaky Bucket Rate Limiting:** Each caller (`sender` address or IP) is restricted to a maximum of 5 requests per minute and 30 requests per day.
4. **Least-Privilege GCP IAM:** The service account JSON used by the agent possesses only `roles/bigquery.dataViewer` on `crypto_analytics_mart` and `roles/bigquery.jobUser` on the project. It has zero administrative or billing permissions.
5. **GCP Project Quota Ceiling:** A daily project query cap (e.g., 10 GB/day) is configured in Cloud Console to guarantee never exceeding the 1,000 GB monthly free tier.

---

## 7. ASI Agentverse & uAgents Protocol Specification

The agent communicates using Fetch.ai's `uagents` protocol.

### 7.1 Protocol Identifier
`blockchain_analytics_protocol_v1`

### 7.2 Message Schemas
```python
class AnalyticsQueryRequest(Model):
    query_type: str  # "btc_hodl_waves", "btc_microtransactions", "usdc_organic_volume", "eoa_topology"
    start_date: str  # "YYYY-MM-DD"
    end_date: str    # "YYYY-MM-DD"
    granularity: str # "daily", "monthly", "yearly"

class AnalyticsQueryResponse(Model):
    status: str      # "SUCCESS" or "ERROR"
    query_type: str
    timeframe: str
    bytes_scanned_mb: float
    data_points: list[dict]
    empirical_summary: str
    reproducible_sql: str
```
