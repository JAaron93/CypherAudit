# Architectural Design Specification: On-Chain Analytics Oracle & Blockchain Data Agent

**Document Version:** 1.3.0  
**Status:** Approved for Implementation  
**Target Platform:** Google Cloud BigQuery, Google Cloud Scheduler, Fetch.ai / ASI Agentverse, Marimo Notebooks, Python 3.11+  
**LLM Engine:** Gemini 3.7 Flash (`gemini-3.7-flash`) via `google-genai`  
**Time Horizon:** 2014–2026 Baseline Audit + Continuous Monthly Incremental Ingestion (2027+)

---

## 1. Executive Summary & Research Purpose

The primary objective of this project is to build an empirical, reproducible **Blockchain Data Engineering & Analytics Agent** that systematically audits 10+ years of Bitcoin (BTC) and USD Coin (USDC) transaction history. The agent evaluates whether cryptocurrency has achieved organic adoption as an everyday medium of exchange (replacing fiat currency) or whether its utility remains confined to speculative store-of-value accumulation and automated decentralized finance (DeFi) loops.

The project operates through three coordinated delivery surfaces:
1. **Interactive Marimo Research Notebooks:** High-performance, reactive Python notebooks (`marimo`) executing BigQuery queries, performing statistical hypothesis tests with rich \(\LaTeX\) documentation, and rendering publication-quality interactive visualizations.
2. **Autonomous ASI Agentverse Oracle:** A deployed **uAgent** powered by **Gemini 3.7 Flash (`gemini-3.7-flash`)** that acts as a public, cost-protected **On-Chain Analytics Oracle** for external agents and researchers on Fetch.ai's Agentverse.
3. **Google Cloud Managed Ingestion Cron (2027+ Future-Proofing):** A serverless recurring data pipeline managed directly by **Google Cloud Scheduler / BigQuery Scheduled Queries** running on the 1st of every month (`0 0 1 * *` UTC) to ingest new transaction records automatically within GCP.

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

## 3. System Architecture: GCP Managed Scheduling & Analytics Flow

```
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                      GOOGLE CLOUD SCHEDULED CRON (`0 0 1 * *` UTC)                     │
 │                  (Managed natively by GCP Cloud Scheduler / BigQuery)                  │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
          `bigquery-public-data.crypto_bitcoin`       `bigquery-public-data.crypto_ethereum`
             (Scoped Month M-1 Extract)                  (Scoped Month M-1 Extract)
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             │
                                             │ Serverless MERGE INTO (< 25 GB Scanned)
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
 │ • Plotly Publication Charts               │ │ • BigQuery Client (`max_bytes=50MB`)     │
 └───────────────────────────────────────────┘ └──────────────────────────────────────────┘
```

---

## 4. Google Cloud Native Scheduling Architecture

By leveraging **Google Cloud Scheduler** and **BigQuery Scheduled Queries**, the pipeline achieves:
1. **100% Serverless Reliability:** Ingestion does not depend on local machines or long-running python daemons remaining online.
2. **Deterministic Schedule:** Triggers on the 1st of every month at `00:00 UTC` (`0 0 1 * *`).
3. **Automated Partition Updates:** Scopes execution dynamically to `DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)`, ensuring zero manual configuration month-to-month.
4. **Cost Containment:** Each monthly run scans only \(\sim 20\text{--}25\text{ GB}\) per month (\(<\$0.15\)), well within the **1,000 GB Always-Free monthly tier**.
