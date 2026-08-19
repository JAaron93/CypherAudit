# Architectural Design Specification: On-Chain Analytics Oracle & Blockchain Data Agent

**Document Version:** 1.2.0  
**Status:** Approved for Implementation  
**Target Platform:** Google Cloud BigQuery, Fetch.ai / ASI Agentverse, Marimo Notebooks, Python 3.11+  
**LLM Engine:** Gemini 3.7 Flash (`gemini-3.7-flash`) via `google-genai`  
**Time Horizon:** 2014–2026 Baseline Audit + Continuous Monthly Incremental Ingestion (2027+)

---

## 1. Executive Summary & Research Purpose

The primary objective of this project is to build an empirical, reproducible **Blockchain Data Engineering & Analytics Agent** that systematically audits 10+ years of Bitcoin (BTC) and USD Coin (USDC) transaction history. The agent evaluates whether cryptocurrency has achieved organic adoption as an everyday medium of exchange (replacing fiat currency) or whether its utility remains confined to speculative store-of-value accumulation and automated decentralized finance (DeFi) loops.

The project operates through dual delivery surfaces:
1. **Interactive Marimo Research Notebooks:** High-performance, reactive Python notebooks (`marimo`) that execute BigQuery queries, perform statistical hypothesis tests with rich \(\LaTeX\) documentation, and render publication-quality interactive visualizations.
2. **Autonomous ASI Agentverse Oracle:** A deployed **uAgent** powered by **Gemini 3.7 Flash (`gemini-3.7-flash`)** that acts as a public, cost-protected **On-Chain Analytics Oracle** for external agents and researchers on Fetch.ai's Agentverse.
3. **Continuous Monthly Data Pipeline (Post-Deployment Future-Proofing):** An automated incremental ETL pipeline scheduled on the 1st of each month to ingest new transaction records, ensuring the oracle remains up to date for 2027, 2028, and beyond without requiring full multi-terabyte table rescans.

---

## 2. Core Research Hypotheses & Mathematical Formulations

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

### Mathematical & Statistical Formulations

#### A. Velocity of Money (\(V\))
\[
V = \frac{Y}{M} = \frac{\sum_{i=1}^{N} \text{TxValue}_i}{\text{CirculatingSupply}}
\]

#### B. Fee Drag on Retail Commerce
\[
\text{FeeDrag}_{\text{basket}} = \left( \frac{\text{Fee}_{\text{avg}}}{\text{BasketValue}_{\text{USD}}} \right) \times 100\%
\]

#### C. Stablecoin Organic Adoption Ratio (\(\Phi_{\text{organic}}\))
\[
\Phi_{\text{organic}} = \frac{\sum V_{\text{organic}}}{\sum V_{\text{raw}}} = \frac{\sum_{j \in \text{Organic}} v_j}{\sum_{k \in \text{All}} v_k}
\]

#### D. Counterparty Topology Ratio (\(\Omega_{\text{retail}}\))
\[
\Omega_{\text{retail}} = \frac{\sum V_{\text{EOA}\rightarrow\text{EOA}}}{\sum V_{\text{EOA}\rightarrow\text{EOA}} + \sum V_{\text{EOA}\rightarrow\text{Contract}}}
\]

---

## 3. System Architecture & Dual Ingestion Lifecycle

The data engineering lifecycle consists of two distinct phases:

```
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                      LIFECYCLE PHASE 1: HISTORICAL BASELINE ETL                        │
 │  • Timeframe: 2014-01-01 to 2026-01-01 (12+ Year Longitudinal Dataset)                │
 │  • Process: One-time batch partition materialization into `crypto_analytics_mart`      │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
 ┌───────────────────────────────────────────┴────────────────────────────────────────────┐
 │                  LIFECYCLE PHASE 2: CONTINUOUS MONTHLY INCREMENTAL INGESTION           │
 │  • Frequency: Monthly on the 1st day (e.g. at 00:00 UTC)                               │
 │  • Scope: Single previous calendar month delta (e.g. Month M-1)                        │
 │  • Efficiency: Scans ONLY ~25 GB data (< $0.15, absorbed by 1 TB/mo Always-Free tier)  │
 │  • Mutation: BigQuery `MERGE INTO` or Partition Overwrite                              │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                      CURATED ANALYTICAL DATAMART (< 30 MB Total)                       │
 │                       (Dataset: `crypto_analytics_mart` in User GCP)                   │
 ├───────────────────────────────────────────┬────────────────────────────────────────────┤
 │ `btc_daily_utxo_distribution`             │ 2014–2026+ Daily UTXO age bands, micro-tx  │
 │                                           │ counts, fee drag.                          │
 ├───────────────────────────────────────────┼────────────────────────────────────────────┤
 │ `usdc_daily_organic_metrics`              │ 2018–2026+ Noise-filtered volume, organic  │
 │                                           │ counts, EOA vs contract volumes.           │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
 ┌───────────────────────────────────────────┐ ┌──────────────────────────────────────────┐
 │    MARIMO REACTIVE RESEARCH NOTEBOOKS     │ │  uAGENTS / AGENTVERSE ANALYTICS ORACLE   │
 ├───────────────────────────────────────────┤ ├──────────────────────────────────────────┤
 │ • Interactive UI & Parameter Sliders      │ │ • Gemini 3.7 Flash (`gemini-3.7-flash`)  │
 │ • LaTeX Statistical Formulations          │ │ • In-Memory Rate Limiter (Token Bucket)  │
 │ • Plotly Publication Charts               │ │ • Auto-Scheduled Monthly Ingestion Cron  │
 └───────────────────────────────────────────┘ └──────────────────────────────────────────┘
```

---

## 4. Incremental Monthly Ingestion Logic

To avoid re-scanning multi-terabyte raw tables, the incremental pipeline executes a scoped `MERGE INTO` targeting only the previous month's date bounds:

```sql
MERGE `{project_id}.{dataset_id}.btc_daily_utxo_distribution` T
USING (
  -- Monthly incremental aggregated delta
  SELECT date, total_active_utxos, ...
  FROM raw_monthly_extract
) S
ON T.date = S.date
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED THEN INSERT ...;
```

---

## 5. Security Hardening & Cost Protection

1. **Hard Byte Limit (`maximum_bytes_billed`):** 50 MB ceiling on analytical queries; 50 GB ceiling on incremental monthly batch ETL.
2. **Strict Query Parameterization:** Zero dynamic SQL string concatenation.
3. **Leaky Bucket Rate Limiting:** 5 req/min and 30 req/day per agent.
4. **Least-Privilege GCP IAM:** Read-only data viewer on datamart.
5. **In-Memory LRU Cache:** 0ms cached query responses.
