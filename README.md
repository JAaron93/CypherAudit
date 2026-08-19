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

## 🏗️ Architecture: The Curated Datamart Pattern

To enable high-speed queries for external agents while keeping Google Cloud query costs strictly at **$0.00/month** within GCP's Always-Free Tier (1 TB/month), CypherAudit decouples raw multi-terabyte scans from runtime queries:

```
                                  Agentverse User / External Agent
                                                 │
                                                 │ 1. Request (Natural Language or JSON-RPC)
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │       Security Hardening Layer        │
                             │  • Token Bucket Rate Limiter          │
                             │  • Input Validator & Circuit Breaker  │
                             │  • In-Memory Result Cache (LRU)       │
                             └───────────────────┬───────────────────┘
                                                 │ (Cache Miss & Validated)
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │      uAgents / FastAPI Agent Core     │
                             │  • Gemini Flash Intent & Param Parser │
                             │  • Parameterized SQL Builder          │
                             │  • BigQuery Client (50MB Hard Cap)    │
                             └───────────────────┬───────────────────┘
                                                 │
                                                 │ 2. Scans < 5MB Data
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │    Curated Datamart (GCP BigQuery)    │
                             │  • btc_daily_utxo_distribution        │
                             │  • usdc_daily_organic_metrics         │
                             │  • counterparty_topology_breakdown    │
                             └───────────────────────────────────────┘
```

1. **Batch ETL Pipeline (`src/bigquery/etl_pipelines.py`):** Runs once to aggregate 10+ years of raw Bitcoin and Ethereum logs into compact (<25 MB), date-partitioned datamart tables (`crypto_analytics_mart`).
2. **SignalChain Oracle (`src/agent/`):** Answers runtime inquiries by querying only the compact summary datamart, scanning **< 5 MB per query** (< $0.00003).

---

## 🛡️ Defense-in-Depth Security & Cost Hardening

CypherAudit enforces strict security guardrails to protect against API abuse, script kiddies, and billing exhaustion:

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
│   ├── design.md              # Architectural design & literature gap analysis
│   ├── requirements.md        # Functional, security & BDD requirements
│   └── tasks.md               # Test-driven implementation plan
├── src/
│   ├── agent/
│   │   ├── main.py            # uAgents daemon & Agentverse registration
│   │   ├── protocols/         # Message schemas & protocol handlers
│   │   └── security/          # Rate limiters & circuit breaker guardrails
│   ├── bigquery/
│   │   ├── client.py          # Parameterized client with 50MB byte ceiling & LRU cache
│   │   ├── etl_pipelines.py   # Batch ETL pipeline for curated datamarts
│   │   └── sql_queries/       # Parameterized SQL query templates
│   └── nl_parser/
│       └── gemini_router.py   # Gemini Flash natural language query router
├── tests/
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
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

### 3. Run the Test Suite
```bash
PYTHONPATH=. pytest -v
```

---

## 📜 License
MIT License. Open-source and reproducible for all blockchain researchers and agent builders.
