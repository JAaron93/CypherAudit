# AGENTS.md: SignalChain Oracle (CypherAudit) Agent Guidelines

This document governs the architecture, development principles, tool routing discipline, and security guardrails for any AI agent working on the **CypherAudit** repository (**SignalChain Oracle**).

---

## 1. Project Overview & Research Telos

* **Project Name:** CypherAudit
* **Agent Name:** SignalChain Oracle
* **Target Ecosystem:** Fetch.ai / ASI Agentverse Autonomous Analytics Oracle & Marimo Research Hub
* **LLM Engine:** Gemini 3.7 Flash (`gemini-3.7-flash`) via `google-genai`
* **Core Telos:** An empirical, reproducible data engineering and analytics system auditing 10+ years of Bitcoin (BTC) and USD Coin (USDC) transaction history (2014 to 2026+) to determine whether cryptocurrency functions as an everyday medium of exchange or has stagnated into speculative store-of-value accumulation and automated DeFi loops.

---

## 2. Technical Stack & Architecture

```
                                  SYSTEM ARCHITECTURE
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                      GOOGLE CLOUD SCHEDULED CRON (`0 0 1 * *` UTC)                     │
 │                     (100% Serverless BigQuery Scheduled Ingestion)                     │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │ Scoped Monthly MERGE INTO (<25 GB)
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                         CURATED DATAMART: `crypto_analytics_mart`                      │
 │   • `btc_daily_utxo_distribution`: 2014–2026+ UTXO age bands & micro-tx density        │
 │   • `usdc_daily_organic_metrics`: 2018–2026+ Noise-filtered organic volume & topology  │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
 ┌───────────────────────────────────────────┐ ┌──────────────────────────────────────────┐
 │    MARIMO REACTIVE RESEARCH NOTEBOOKS     │ │       ASI AGENTVERSE ANALYTICS ORACLE    │
 ├───────────────────────────────────────────┤ ├──────────────────────────────────────────┤
 │ • `notebooks/btc_analysis.py`             │ │ • `src/agent/main.py` (uAgents daemon)   │
 │ • `notebooks/usdc_analysis.py`            │ │ • `src/agent/protocols/` (Pydantic v2)   │
 │ • LaTeX formulas & Plotly visualizers     │ │ • `src/agent/security/` (Token Bucket)   │
 │ • Export: `marimo export html-wasm`       │ │ • `src/nl_parser/` (Gemini 3.7 Flash)    │
 │ • Deploy: GitHub Pages / molab ($0/mo)    │ │ • `src/bigquery/client.py` (LRU Cache)   │
 └───────────────────────────────────────────┘ └──────────────────────────────────────────┘
```

---

## 3. Mandatory Tool Routing Protocol

Always route investigations through specialized tools before running raw terminal commands:

1. **Codebase Exploration & Symbol Navigation:** Use `codebase-memory-mcp` tools (`search_graph`, `trace_path`, `get_code_snippet`, `query_graph`) to query the Abstract Syntax Tree (AST) graph. Never use unindexed raw file sweeps as a first resort.
2. **Syntax & API Documentation:** Use the `gemini-documentation-router` skill for Gemini API (`google-genai`), ADK, Google Cloud BigQuery, and uAgents syntax.
3. **PR & Code Review Iteration:** Use `greptile-greploop` to trigger reviews, resolve comments, and iterate until 5/5 confidence is achieved.

---

## 4. Cost Guardrails & Safety Boundaries ($0.00/Month Ceiling)

All code and queries MUST strictly comply with the **Always-Free Tier** ceilings:

* **Hard BigQuery Byte Limit:** All runtime queries in `src/bigquery/client.py` must enforce `maximum_bytes_billed = 50_000_000` (50 MB).
* **Batch/Monthly Ingestion Cap:** Monthly incremental ETL in `src/bigquery/etl_pipelines.py` must enforce `maximum_bytes_billed = 50_000_000_000` (50 GB).
* **Identifier Sanitization:** Never concatenate raw strings into SQL queries. Always validate `project_id` and `dataset_id` using `validate_identifier` (`^[a-zA-Z0-9_\-\.]+$`).
* **Rate Limiting:** Every incoming agent query must pass through the Token Bucket Rate Limiter (`5 req/min`, `30 req/day` per agent address).
* **Asynchronous Execution:** BigQuery execution within uAgents event handlers must use `await asyncio.to_thread(...)` to prevent blocking the async event loop.

---

## 5. Development & Test-Driven Verification (TDD)

* **Virtual Environment:** Always use the dedicated virtual environment:
  ```bash
  source .venv/bin/activate
  # or
  PYTHONPATH=. .venv/bin/pytest tests/ -v
  ```
* **Strict TDD Workflow:** Write or update failing unit tests in `tests/` before implementing features or bug fixes.
* **Progressive Commit Verification:** Run the full test suite after **every single commit**. Never batch multiple unverified commits.
* **File Manipulation Preferences:**
  * Use `rsync` for copying/moving files.
  * Use `tee` for file pipelines (`command | tee FILE`).
  * Never use blocked shell commands: `mv`, `cp`, `>`, or `>>`.

---

## 6. Directory Structure & Key Artifacts

```
CypherAudit/
├── AGENTS.md                          # This agent constitution file
├── README.md                          # Public research documentation & telos
├── pyproject.toml                     # Dependencies & package configuration
├── .greptile/
│   ├── config.json                    # Greptile review settings
│   └── rules.md                       # Greptile code review guidelines
├── specs/
│   ├── design.md                      # System architecture & mathematical formulations (v1.4.0)
│   ├── requirements.md                # Functional requirements & BDD acceptance tests (v1.4.0)
│   └── tasks.md                       # Modular execution tracks & task list (v1.4.0)
├── src/
│   ├── agent/
│   │   ├── main.py                    # uAgent main entrypoint & Agentverse registration
│   │   ├── protocols/
│   │   │   └── analytics_protocol.py  # Pydantic v2 request/response protocol
│   │   └── security/
│   │       ├── circuit_breaker.py     # Parameter validation & circuit breaker
│   │       └── rate_limiter.py        # Token bucket per-agent rate limiter
│   ├── bigquery/
│   │   ├── client.py                  # Parameterized client, weighted aggregator & LRU cache
│   │   ├── etl_pipelines.py           # Historical baseline & monthly incremental ETL
│   │   └── sql_queries/               # Parameterized SQL query templates
│   └── nl_parser/
│       └── gemini_router.py           # Gemini 3.7 Flash semantic intent router
├── notebooks/
│   ├── btc_analysis.py                # Marimo Bitcoin UTXO HODL & micro-payment notebook
│   └── usdc_analysis.py               # Marimo USDC organic volume & topology notebook
├── docs/                              # Compiled Marimo WebAssembly (WASM) static apps
└── tests/                             # Pytest test suites (100% pass required)
```
