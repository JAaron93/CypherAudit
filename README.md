# 🕵️‍♂️ CypherAudit: SignalChain Oracle

> **An autonomous, empirical on-chain analytics oracle auditing 10+ years of Bitcoin and USDC transaction data to test the "Medium of Exchange" vs. "Store of Value" thesis on ASI Agentverse.**

---

## 🎯 The Telos: Why CypherAudit Exists

Over fifteen years after the publication of the Bitcoin whitepaper, a central ideological promise of cryptocurrency remains hotly contested: **Has crypto become an everyday, peer-to-peer medium of exchange to replace fiat, or has it stagnated into a speculative store of value and decentralized finance (DeFi) trading collateral?**

**CypherAudit** is an open-source, empirical research framework and autonomous data agent (**SignalChain Oracle**) designed to answer this question with mathematical certainty. By conducting longitudinal SQL audits across a decade of Google Cloud BigQuery public blockchain datasets (`crypto_bitcoin` and `crypto_ethereum`), CypherAudit evaluates on-chain transaction velocity, fee drag, counterparty topology, and noise-filtered payment volume.

### The Core Research Inquiries

```
                                  CORE RESEARCH HYPOTHESES
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ 1. The Micro-Payment & Velocity Decay Hypothesis (Bitcoin):                            │
 │    Has the proportion of retail micro-purchases (<$10, <$500) on Bitcoin L1 decayed    │
 │    over the past decade as base-layer fees rendered everyday purchases irrational?     │
 ├────────────────────────────────────────────────────────────────────────────────────────┤
 │ 2. The Organic vs. Automated Noise Hypothesis (USDC / Stablecoins):                    │
 │    What exact percentage of stablecoin transfer volume represents genuine everyday     │
 │    commerce versus automated protocol loops (MEV bots, arbitrage, liquidity sweeps)?   │
 ├────────────────────────────────────────────────────────────────────────────────────────┤
 │ 3. The Counterparty Topology Hypothesis (EOA vs. Smart Contracts):                     │
 │    What fraction of stablecoin volume settles between peer/merchant wallets (EOA-EOA)  │
 │    versus smart contract routing (DEX routers, lending pools, algorithmic bots)?       │
 ├────────────────────────────────────────────────────────────────────────────────────────┤
 │ 4. Cold Storage & Holding vs. Active Velocity Heuristics:                              │
 │    How has the supply distribution of Bitcoin shifted into multi-year dormant UTXOs    │
 │    (HODL waves), proving long-term capital preservation over transactional velocity?   │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Literature Gap: Where Previous Analyses Fell Short

While several major institutions have researched crypto payment adoption, previous studies left critical methodology gaps:

| Previous Research | Methodology & Limitations | How CypherAudit Resolves It |
| :--- | :--- | :--- |
| **Federal Reserve (SHED Surveys)** | Relies solely on consumer self-reporting surveys (~1-2% payment adoption), lacking on-chain verification. | **Empirical Blockchain Ground Truth:** Directly analyzes raw UTXO spend intervals, transaction sizes, and counterparty entities. |
| **Visa / Artemis / Allium** | Published high-level aggregated dashboards, but underlying data models and custom ETL classifiers remain closed-source. | **100% Open & Reproducible SQL:** Fully open-source parameterized BigQuery scripts executable in BigQuery Studio without proprietary lock-in. |
| **Chainalysis / TRM Labs** | Enterprise black-box clustering software inaccessible to independent researchers and autonomous agents. | **Open Agent-to-Agent Oracle:** Accessible to any agent in the decentralized AI ecosystem via standard Fetch.ai `uagents` protocols. |
| **Qualitative Essays (patio11, Molly White)** | Highlight payment economics and merchant abandonment cases without longitudinal quantitative SQL metrics. | **Mathematical Proof of Fee Drag:** Measures historical fee-to-value drag across 10 years of transactions ($5–$50 retail baskets). |

---

## 🏗️ Architecture: Multi-Layer Curated Datamart Pattern

To enable high-speed queries for external agents while keeping Google Cloud query costs strictly at **$0.00/month** within GCP's Always-Free Tier (1 TB/month), CypherAudit decouples raw multi-terabyte scans from runtime queries across distinct deterministic and cognitive processing boundaries:

```
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                      GOOGLE CLOUD SCHEDULED CRON (`0 0 1 * *` UTC)                     │
 │                  (100% Serverless Cloud Scheduler / BigQuery Pipeline)                 │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             │ 1. Scoped Monthly MERGE INTO (< 25 GB Scanned)
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                         CURATED DATAMART: `crypto_analytics_mart`                      │
 │   • `btc_daily_utxo_distribution`: 2014–2026+ UTXO age bands & micro-tx density        │
 │   • `usdc_daily_organic_metrics`: 2018–2026+ Noise-filtered organic volume & topology  │
 └─────────────────────┬────────────────────────────────────────────────────┬─────────────┘
                       │                                                    │
                       │ 2. Scans < 5 MB Curated Data                       │ Automated Refresh
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
 │ │ • Gemini 3.7 Flash (`gemini-3.7-flash`)  │                                            
 │ │ • Modular Prompt: `oracle_instructions.md`│                                           
 │ │ • Empirical Macroeconomic Persona        │                                            
 │ │ • Statistical Confidence Interpretations │                                            
 │ │ • Mandatory Financial Disclaimers        │                                            
 │ └──────────────────────────────────────────┘                                            
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Continuous Ingestion Cron:** Cloud Scheduler triggers BigQuery Scheduled Queries on the 1st of every month to merge new blockchain blocks into `crypto_analytics_mart` serverlessly.
2. **Deterministic Layer (Python / `src/`):** Enforces hard limits, rate limiting, and parameter sanitization without LLM hallucinations.
3. **Cognitive Layer (Gemini 3.7 Flash / `oracle_instructions.md`):** Interprets structured data payloads into rigorous macroeconomic narratives.
4. **Interactive Research Hub (Marimo / WASM):** Renders reactive hypothesis models and Plotly visualizations published to GitHub Pages and molab at $0.00/mo.

---

## 🛡️ Defense-in-Depth Security & Cost Hardening

CypherAudit enforces strict security guardrails to protect against API abuse, opportunistic adversaries, and billing exhaustion:

* **Hard BigQuery Byte Cap:** Every query sets `maximum_bytes_billed = 50_000_000` (50 MB ceiling). Any query exceeding this threshold is immediately aborted by BigQuery before incurring charges.
* **Zero Dynamic SQL:** Zero string interpolation or raw SQL execution. Queries strictly use `bigquery.ScalarQueryParameter` with input whitelisting.
* **Token Bucket Rate Limiting:** Limits incoming agent requests to **5 req/min** and **30 req/day** per caller address/IP.
* **In-Memory LRU Cache:** Repeated queries are served in `< 5ms` with zero BigQuery API calls.

---

## 📡 ASI Agentverse & uAgents Integration

SignalChain Oracle registers the `blockchain_analytics_protocol_v1` on Fetch.ai's **Agentverse** to serve as a decentralized analytics oracle for trading bots, DAO governance agents, and macro researchers.

### Protocol Message Schemas

```python
class AnalyticsQueryRequest(BaseModel):
    query_type: str  # "btc_hodl_waves", "btc_microtransactions", "usdc_organic_volume", "usdc_eoa_topology"
    start_date: str  # "YYYY-MM-DD"
    end_date: str    # "YYYY-MM-DD"
    granularity: str # "daily", "monthly", "yearly"

class AnalyticsQueryResponse(BaseModel):
    status: str      # "SUCCESS", "RATE_LIMITED", or "ERROR"
    query_type: str
    timeframe: str
    bytes_scanned_mb: float
    data_points: list[dict]
    empirical_summary: str
    reproducible_sql: str
```

---

## 📁 Repository Structure

```
CypherAudit/
├── specs/
│   └── foundation-spec/
│       ├── design.md          # Architectural design & literature gap analysis
│       ├── requirements.md    # Functional, security & BDD requirements
│       └── tasks.md           # Test-driven implementation plan
├── src/
│   ├── agent/
│   │   ├── main.py            # uAgents daemon & Agentverse registration
│   │   ├── prompts/
│   │   │   └── oracle_instructions.md # Decoupled Oracle research persona & synthesis prompt
│   │   ├── protocols/         # Message schemas & protocol handlers
│   │   └── security/          # Rate limiters & circuit breaker guardrails
│   ├── bigquery/
│   │   ├── client.py          # Parameterized client with 50MB byte ceiling & LRU cache
│   │   ├── etl_pipelines.py   # Batch ETL pipeline for curated datamarts
│   │   └── sql_queries/       # Parameterized SQL query templates
│   └── nl_parser/
│       └── gemini_router.py   # Gemini Flash natural language query router
├── tests/
│   ├── test_agent_main.py     # Main runner, prompt ingestion & agent initialization tests
│   ├── test_security.py       # Rate limiting & circuit breaker tests
│   ├── test_bigquery_client.py# Byte limit & LRU cache tests
│   ├── test_gemini_router.py  # NL routing & heuristic fallback tests
│   └── test_protocols.py      # Agentverse protocol schema tests
├── .greptile/                 # Greptile automated code review guidelines
├── pyproject.toml             # Python dependencies & configuration
├── .env.example               # Environment variables template
└── README.md
```

---

## 🚀 Getting Started

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/JAaron93/CypherAudit.git
cd CypherAudit

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Configuration
Copy `.env.example` to `.env` and fill in your credentials (`AGENT_SEED` is required for cryptographic identity derivation):
```bash
cp .env.example .env
```

### 3. Run the Test Suite
```bash
PYTHONPATH=. pytest -v
```

### 4. Launch SignalChain Oracle Daemon
```bash
python -m src.agent.main
```

---

## 📜 License
MIT License. Open-source and reproducible for all blockchain researchers and agent builders.
