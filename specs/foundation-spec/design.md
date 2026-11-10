# Architectural Design Specification: On-Chain Analytics Oracle & Blockchain Data Agent

**Document Version:** 1.6.0  
**Status:** Approved for Implementation (Final Baseline)  
**Target Platform:** Google Cloud BigQuery, Google Cloud Scheduler, Fetch.ai / ASI Agentverse, Marimo Notebooks (WASM / GitHub Pages / molab), Python 3.x (minimum version owned by `pyproject.toml` → `requires-python`)  
**LLM Engine:** Gemini 3.8 Flash (`gemini-3.8-flash`) via `google-genai`  
**Time Horizon:** 2014–2026 Baseline Audit + Continuous Monthly Incremental Ingestion (2027+)  
**Scheduler & Publishing:** Google Cloud Scheduler (`0 0 1 * *` UTC) + Automated Marimo Web Publishing

---

## 1. Executive Summary & Research Purpose

The primary objective of this project is to build an empirical, reproducible **Blockchain Data Engineering & Analytics Agent** that systematically audits 10+ years of Bitcoin (BTC) and USD Coin (USDC) transaction history. The agent evaluates whether cryptocurrency has achieved organic adoption as an everyday medium of exchange (replacing fiat currency) or whether its utility remains confined to speculative store-of-value accumulation and automated decentralized finance (DeFi) loops.

The project operates through four coordinated delivery surfaces:
1. **Interactive Marimo Research Notebooks:** Reactive Python notebooks (`marimo`) executing BigQuery queries, performing statistical hypothesis tests with rich \(\LaTeX\) documentation, and rendering publication-quality interactive visualizations.
2. **Automated Cloud Hosting & Web Publishing:** Following each monthly data ingestion on the 1st of the month, the pipeline automatically compiles the Marimo notebooks into interactive, standalone WebAssembly web applications (`marimo export html-wasm --mode run`) hosted for free on **GitHub Pages** / **molab** (Marimo's official cloud environment).
3. **Autonomous ASI Agentverse Oracle:** A deployed **uAgent** powered by **Gemini 3.8 Flash (`gemini-3.8-flash`)** acting as a public, cost-protected **On-Chain Analytics Oracle** on Fetch.ai's Agentverse, driven by modular research persona instructions (`src/agent/prompts/oracle_instructions.md`).
4. **Google Cloud Managed Ingestion Cron (2027+ Future-Proofing):** A serverless recurring data pipeline managed directly by **Google Cloud Scheduler / BigQuery Scheduled Queries** running on the 1st of every month (`0 0 1 * *` UTC).

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

## 3. Comprehensive Multi-Layer System Architecture

```
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                      GOOGLE CLOUD SCHEDULED CRON (`0 0 1 * *` UTC)                     │
 │                  (100% Serverless Cloud Scheduler / BigQuery Pipeline)                 │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             │ Scoped Monthly MERGE INTO (< 25 GB)
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                         CURATED DATAMART: `crypto_analytics_mart`                      │
 │   • `btc_daily_utxo_distribution`: 2014–2026+ UTXO age bands & micro-tx density        │
 │   • `usdc_daily_organic_metrics`: 2018–2026+ Noise-filtered organic volume & topology  │
 └─────────────────────┬────────────────────────────────────────────────────┬─────────────┘
                       │                                                    │
                       │ Query Data (< 5 MB)                                │ Trigger Ingestion
                       ▼                                                    ▼
 ┌──────────────────────────────────────────────┐ ┌───────────────────────────────────────┐
 │         DETERMINISTIC LAYER (Python)         │ │   MARIMO INTERACTIVE RESEARCH HUB     │
 │ ├──────────────────────────────────────────┤ │ ├─────────────────────────────────────┤ │
 │ │ • Parameterized SQL Client (`client.py`) │ │ │ • `notebooks/btc_analysis.py`       │ │
 │ │ • 50 MB Hard Billing Cap (`COST-1`)      │ │ │ • `notebooks/usdc_analysis.py`      │ │
 │ │ • In-Memory LRU Cache (0ms latency)      │ │ │ • LaTeX Hypotheses & Plotly Charts  │ │
 │ │ • Token Bucket Rate Limiter (`5 req/min`)│ │ │ • `marimo export html-wasm`         │ │
 │ │ • Pydantic v2 A2A Protocols (`uAgents`)  │ │ │ • Hosted on GitHub Pages & molab    │ │
 │ └────────────────────┬─────────────────────┘ │ └─────────────────────────────────────┘ │
 │                      │ Filtered Data Payload │                                         │
 │                      ▼                       └─────────────────────────────────────────┘
 │ ┌──────────────────────────────────────────┐                                            
 │ │          COGNITIVE LAYER (Gemini)        │                                            
 │ ├──────────────────────────────────────────┤                                            
 │ │ • Gemini 3.8 Flash (`gemini-3.8-flash`)  │                                            
 │ │ • Modular Prompt: `oracle_instructions.md`│                                           
 │ │ • Empirical Macroeconomic Persona        │                                            
 │ │ • Statistical Confidence Interpretations │                                            
 │ │ • Mandatory Financial Disclaimers        │                                            
 │ └──────────────────────────────────────────┘                                            
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Marimo Hosting & Publishing Architecture

### 4.1 Automated WebAssembly (WASM) Deployment
* **Command:** `marimo export html-wasm notebooks/btc_analysis.py -o docs/index.html --mode run`
* **Hosting Surface:** GitHub Pages (serving directly from the `docs/` directory of the `CypherAudit` repository) and Marimo's official cloud platform (**molab**).
* **Cost & Ops:** **$0.00/month**. The notebook runs client-side in the browser via Pyodide/WASM, rendering all reactive sliders, Plotly charts, and LaTeX equations instantly without any standing server.

---

## 5. Security Hardening & Cost Protection

1. **Hard Byte Limit (`maximum_bytes_billed`):** 50 MB ceiling on analytical queries; 50 GB ceiling on incremental monthly batch ETL.
2. **Strict Query Parameterization:** Zero dynamic SQL string concatenation.
3. **Leaky Bucket Rate Limiting:** 5 req/min and 30 req/day per agent.
4. **Least-Privilege GCP IAM:** Read-only data viewer on datamart.
5. **In-Memory LRU Cache:** 0ms cached query responses.

---

## 6. Scheduled Housekeeping & Datamart Freshness Monitoring

### 6.1 Motivation & Ownership Boundary
Ingestion ownership remains 100% serverless in GCP (Cloud Scheduler `0 0 1 * *` UTC → BigQuery scheduled `MERGE INTO`). The agent never writes to the datamart and never runs ETL. What the agent *can* do — as the datamart's always-on consumer — is detect when that serverless pipeline silently stops producing rows and report its own runtime health. `src/agent/housekeeping.py` therefore contains read-only, fail-soft monitoring only.

### 6.2 Scheduling Primitives (uAgents; version floor owned by `pyproject.toml`)
Both handlers register through the uAgents cron scheduler (`Agent.on_schedule`, powered by `cronsim`, evaluated in UTC by default):

| Handler | Cron (UTC) | Surface |
| :--- | :--- | :--- |
| Datamart freshness probe | `0 6 * * *` | `MAX(date)` per curated datamart table |
| Daily usage/health digest | `30 6 * * *` | One aggregated log line |

### 6.3 Freshness Evaluation Model
For each table `t ∈ {btc_daily_utxo_distribution, usdc_daily_organic_metrics}` (both `PARTITION BY date`):
* **Expected ceiling** `C(today)` = last day of the previous calendar month — the partition the monthly MERGE must already have produced.
* **Observed ceiling** `M(t)` = `SELECT MAX(date) AS max_date`, executed via `BigQueryAnalyticsClient.fetch_table_max_date` under the inherited 50 MB `maximum_bytes_billed` ceiling (metadata-pruned on the partitioned & clustered `date` column).
* **State machine** (grace `g` = 2 days):
  * `FRESH` when `M ≥ C`
  * `PENDING` when `M ≥ C_prev` (end of the month before last) and `today.day ≤ g` — the current monthly cycle may still be in flight
  * `STALE` otherwise, reporting `days_behind = (C − M).days`
* Probes execute via `asyncio.to_thread` (async event-loop non-blocking invariant); every failure path logs without raising.

### 6.4 Usage Digest Counters
A thread-safe `UsageDigest` accumulates counters at the security and execution boundaries — rate-limit rejections, security violations, query errors, queries served, and Gemini→rule-based fallback degradations — and emits a single INFO log line daily, resetting after each emission.
