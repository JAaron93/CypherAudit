# Implementation Tasks & Test-Driven Execution Plan: On-Chain Analytics Oracle

**Document Version:** 1.6.0  
**Status:** Approved for Implementation (Final Baseline)  
**Traceability Base:** `specs/foundation-spec/design.md` (v1.6.0) & `specs/foundation-spec/requirements.md` (v1.6.0)  
**LLM Engine:** Gemini 3.8 Flash (`gemini-3.8-flash`)  
**Time Horizon:** 2014–2026 Baseline Audit + Continuous Monthly Incremental Ingestion (2027+)  
**Scheduler & Hosting:** Google Cloud Scheduler (`0 0 1 * *` UTC) + Marimo WebAssembly / GitHub Pages / molab

---

## Overview & Execution Tracks

The implementation plan is organized into **8 modular execution tracks** with explicit dependencies, parallelism opportunities, and strict Test-Driven Development (TDD) gates.

```
                      TRACK 1: Setup & Security Hardening
                                       │
                  ┌────────────────────┴────────────────────┐
                  ▼                                         ▼
   TRACK 2: BigQuery SQL & ETL             TRACK 3: BQ Client & Cache
   (Data Model & GCP Scheduled Queries)    (Circuit Breakers & SDK)
                  │                                         │
                  └────────────────────┬────────────────────┘
                                       │
                  ┌────────────────────┴────────────────────┐
                  ▼                                         ▼
   TRACK 4: Gemini 3.8 Flash Router        TRACK 5: uAgents Protocol
   (Intent & Param Mapping)                (Agentverse Integration)
                  │                                         │
                  └────────────────────┬────────────────────┘
                                       │
                  ┌────────────────────┴────────────────────┐
                  ▼                                         ▼
   TRACK 6: E2E Verification & PR          TRACK 7: Marimo Notebooks & WASM
   (Integration Testing & Review)          (Interactive LaTeX & Web Deploy)
                                             │
                                             ▼
                     TRACK 8: Scheduled Housekeeping
                     (Freshness Probe & Usage Digest)
```

---

## Track 1: Foundational Setup & Security Hardening [COMPLETED]

### Task 1.1: Project Environment & Dependency Configuration [COMPLETED]
* **Description:** Initialize Python virtual environment, configure `pyproject.toml` with `uagents`, `google-cloud-bigquery`, `google-genai`, `pydantic`, `pytest`, `pytest-asyncio`, and `python-dotenv`.
* **Dependencies:** None.
* **Traceability:** NFR-3, COST-2.
* **Artifacts:** `pyproject.toml`, `.env.example`, `.gitignore`.

### Task 1.2 [TDD]: Security Hardening & Rate Limiter Tests [COMPLETED]
* **Description:** Write unit tests for Token Bucket rate limiter and input sanitization before implementing the security layer.
* **Dependencies:** Task 1.1.
* **Traceability:** SEC-1, BDD-3.
* **Artifacts:** `tests/test_security.py`.

### Task 1.3: Security Circuit Breaker & Rate Limiter Implementation [COMPLETED]
* **Description:** Implement `src/agent/security/rate_limiter.py` and `src/agent/security/circuit_breaker.py`.
* **Dependencies:** Task 1.2.
* **Traceability:** SEC-1, SEC-2, SEC-3.
* **Artifacts:** `src/agent/security/rate_limiter.py`, `src/agent/security/circuit_breaker.py`.

---

## Track 2: Curated Datamart Batch & Incremental ETL Pipelines [COMPLETED]

### Task 2.1: Bitcoin Historical & Monthly UTXO Distribution ETL [COMPLETED]
* **Description:** Implement `BTC_ETL_SQL` in `src/bigquery/etl_pipelines.py` calculating the 7 HODL age bands and transaction size distributions.
* **Dependencies:** Task 1.1.
* **Traceability:** FR-1.1, FR-1.2, FR-1.3, BDD-1.
* **Artifacts:** `src/bigquery/etl_pipelines.py`, `src/bigquery/sql_queries/btc_utxo_hodl_waves.sql`, `src/bigquery/sql_queries/btc_microtransaction_density.sql`.

### Task 2.2: Ethereum / USDC Organic vs. Noise Filter ETL [COMPLETED]
* **Description:** Implement `USDC_ETL_SQL` in `src/bigquery/etl_pipelines.py` implementing the Visa/Artemis noise filter and counterparty topology segregation.
* **Dependencies:** Task 1.1.
* **Traceability:** FR-1.4, FR-1.5, BDD-1.
* **Artifacts:** `src/bigquery/etl_pipelines.py`, `src/bigquery/sql_queries/usdc_organic_vs_noise.sql`, `src/bigquery/sql_queries/usdc_eoa_vs_contract.sql`.

### Task 2.3: Datamart Pipeline CLI & Dry-Run Runner [COMPLETED]
* **Description:** Build the CLI harness in `src/bigquery/etl_pipelines.py` to support `--dry-run` and live execution with partition and clustering specifications.
* **Dependencies:** Tasks 2.1, 2.2.
* **Traceability:** FR-1.1, FR-1.4, COST-1.
* **Artifacts:** `src/bigquery/etl_pipelines.py`.

### Task 2.4: Google Cloud Scheduled Ingestion Pipeline Configuration [COMPLETED]
* **Description:** Create deployment configurations and instructions for Google Cloud Scheduler (`0 0 1 * *` UTC) and BigQuery Scheduled Queries using scoped monthly `MERGE INTO` SQL templates.
* **Dependencies:** Tasks 2.1, 2.2, 2.3.
* **Traceability:** FR-1.6, BDD-2, US-3.
* **Artifacts:** `src/bigquery/etl_pipelines.py` (`BTC_MONTHLY_MERGE_SQL`, `USDC_MONTHLY_MERGE_SQL`), `README.md`.

---

## Track 3: Parameterized BigQuery Client & LRU Cache [COMPLETED]

### Task 3.1 [TDD]: BigQuery Client & Byte Limit Tests [COMPLETED]
* **Description:** Write unit tests verifying `maximum_bytes_billed = 50_000_000`, identifier validation, weighted ratio calculations, and in-memory LRU caching.
* **Dependencies:** Task 1.1.
* **Traceability:** FR-2.1, FR-2.2, FR-2.3, FR-2.4, SEC-3, COST-1, BDD-3.
* **Artifacts:** `tests/test_bigquery_client.py`.

### Task 3.2: BigQuery Client Implementation & In-Memory LRU Cache [COMPLETED]
* **Description:** Implement `src/bigquery/client.py` with parameterized execution, BigQuery query caching, 50 MB hard ceilings, and thread-safe in-memory LRU caching.
* **Dependencies:** Task 3.1.
* **Traceability:** FR-2.1, FR-2.3, FR-2.4, SEC-3, COST-1, NFR-1.
* **Artifacts:** `src/bigquery/client.py`.

---

## Track 4: Gemini 3.8 Flash Natural Language Query Router [COMPLETED]

### Task 4.1 [TDD]: Natural Language Semantic Router Tests [COMPLETED]
* **Description:** Write tests verifying prompt mapping to `AnalyticsQueryRequest` and out-of-scope guidance handling.
* **Dependencies:** Task 1.1.
* **Traceability:** FR-3.1, FR-3.2.
* **Artifacts:** `tests/test_gemini_router.py`.

### Task 4.2: Gemini 3.8 Flash Semantic Query Router Implementation [COMPLETED]
* **Description:** Implement `src/nl_parser/gemini_router.py` using `google-genai` with model `gemini-3.8-flash` and structured JSON output schema.
* **Dependencies:** Task 4.1.
* **Traceability:** FR-3.1, FR-3.2.
* **Artifacts:** `src/nl_parser/gemini_router.py`.

---

## Track 5: uAgents Protocol & Agentverse Registration Engine [COMPLETED]

### Task 5.1 [TDD]: Agentverse Message Protocol Tests [COMPLETED]
* **Description:** Write tests for `blockchain_analytics_protocol_v1` schemas (`AnalyticsQueryRequest`, `AnalyticsQueryResponse`).
* **Dependencies:** Task 1.3, Task 3.2.
* **Traceability:** FR-4.1, FR-4.2, FR-4.3, BDD-1.
* **Artifacts:** `tests/test_protocols.py`.

### Task 5.2: uAgents Protocol & Handler Implementation [COMPLETED]
* **Description:** Implement `src/agent/protocols/analytics_protocol.py` defining Pydantic models, rate limiter integration, and non-blocking `asyncio.to_thread` BigQuery execution.
* **Dependencies:** Task 5.1.
* **Traceability:** FR-4.2, FR-4.3, SEC-1.
* **Artifacts:** `src/agent/protocols/analytics_protocol.py`.

### Task 5.3: Agent Main Runner & Agentverse Mailbox Registration [COMPLETED]
* **Description:** Implement `src/agent/main.py` configuring the `Agent` instance with cryptographic wallet seed, Agentverse Mailbox endpoint, and startup banner with endpoint metadata.
* **Dependencies:** Task 5.2.
* **Traceability:** FR-4.1, NFR-3, US-2, US-3.
* **Artifacts:** `src/agent/main.py`.

### Task 5.4: SignalChain Oracle Persona & Modular Instructions File [COMPLETED]
* **Description:** Create `src/agent/prompts/oracle_instructions.md` decoupling system prompts, research persona, statistical interpretation standards, \(\LaTeX\) rendering rules, and financial disclaimers from Python code, and update `gemini_router.py` / `main.py` to dynamically ingest this instructions file.
* **Dependencies:** Task 5.3.
* **Traceability:** FR-4.4, US-1, US-2.
* **Artifacts:** `src/agent/prompts/oracle_instructions.md`.

---

## Track 6: End-to-End Verification & Research Documentation [COMPLETED]

### Task 6.1: Test Suite Execution & 100% Pass Verification [COMPLETED]
* **Description:** Execute `pytest` across all unit, security, and protocol test suites.
* **Dependencies:** Tasks 1.3, 2.3, 3.2, 4.2, 5.2.
* **Traceability:** SEC-1, COST-1, BDD-1, BDD-3.
* **Artifacts:** `tests/`.

### Task 6.2: Comprehensive Research Artifact & Documentation [COMPLETED]
* **Description:** Generate `README.md` and research documentation providing the complete empirical retrospective on 10+ years of Bitcoin and USDC data.
* **Dependencies:** Task 6.1.
* **Traceability:** US-1, US-2, US-3.
* **Artifacts:** `README.md`.

### Task 6.3: Comprehensive Multi-Layer Architecture & Pipeline Diagram in README.md [COMPLETED]
* **Description:** Embed the comprehensive multi-layer architectural diagram into `README.md` clearly contrasting the Deterministic Layer, Cognitive Layer, Datamart Ingestion Pipeline, and Marimo Research Hub.
* **Dependencies:** Task 6.2.
* **Traceability:** FR-6.2, US-1, US-2.
* **Artifacts:** `README.md`.

---

## Track 7: Marimo Interactive Research Notebooks & Cloud/WASM Publishing

### Task 7.1: Marimo & Visualization Dependency Configuration
* **Description:** Update `pyproject.toml` with `marimo`, `plotly`, `pandas`, and `scipy` dependencies.
* **Dependencies:** Task 1.1.
* **Traceability:** FR-5.1, US-1.
* **Artifacts:** `pyproject.toml`.

### Task 7.2: Bitcoin Macro & Micro-Payment Decay Marimo Notebook
* **Description:** Implement reactive notebook `notebooks/btc_analysis.py` with explanatory \(\LaTeX\) cells, BigQuery data loading, and Plotly stacked area HODL wave charts.
* **Dependencies:** Task 2.1, Task 3.2, Task 7.1.
* **Traceability:** FR-5.1, FR-5.2, FR-5.3, US-1, BDD-2.
* **Artifacts:** `notebooks/btc_analysis.py`.

### Task 7.3: USDC Organic Volume & Counterparty Topology Marimo Notebook
* **Description:** Implement reactive notebook `notebooks/usdc_analysis.py` with explanatory \(\LaTeX\) cells, noise filtering, and EOA vs. Contract charts.
* **Dependencies:** Task 2.2, Task 3.2, Task 7.1.
* **Traceability:** FR-5.1, FR-5.2, FR-5.3, US-1, BDD-2.
* **Artifacts:** `notebooks/usdc_analysis.py`.

### Task 7.4: Marimo Reactive Graph Verification & Export Tests
* **Description:** Write unit tests to verify that `notebooks/btc_analysis.py` and `notebooks/usdc_analysis.py` instantiate valid Marimo `App` dependency graphs and execute cleanly.
* **Dependencies:** Task 7.2, Task 7.3.
* **Traceability:** FR-5.4, NFR-2.
* **Artifacts:** `tests/test_notebooks.py`.

### Task 7.5: Automated Marimo WASM Export & GitHub Pages / molab Publishing Pipeline
* **Description:** Create `scripts/export_marimo_wasm.py` to automate compiling notebooks into zero-cost standalone interactive WebAssembly apps (`marimo export html-wasm --mode run`) into `docs/` for instant deployment to GitHub Pages and molab.
* **Dependencies:** Task 7.2, Task 7.3, Task 7.4.
* **Traceability:** FR-5.5, US-1, US-3, BDD-2.
* **Artifacts:** `scripts/export_marimo_wasm.py`.

---

## Track 8: Scheduled Housekeeping & Datamart Freshness Monitoring [IN PROGRESS]

### Task 8.1 [TDD]: Datamart Freshness Evaluation & Probe Tests
* **Description:** Write failing unit tests for the freshness state machine (`FRESH`/`PENDING`/`STALE`, 2-day grace window, calendar-year boundaries) and for `BigQueryAnalyticsClient.fetch_table_max_date` (50 MB ceiling inheritance, empty table → `None`, error wrapping, identifier validation).
* **Dependencies:** Track 3 (BQ Client & Cache).
* **Traceability:** FR-7.1, FR-7.2, FR-7.3, FR-7.4, BDD-4.
* **Artifacts:** `tests/test_housekeeping.py`, `tests/test_bigquery_client.py`.
* - [ ] Failing tests authored and verified red

### Task 8.2: Freshness Probe Implementation
* **Description:** Implement `fetch_table_max_date` (template-substituted read-only `MAX(date)` with inherited byte ceiling) and the `src/agent/housekeeping.py` evaluation core (`expected_data_ceiling`, `evaluate_freshness`, `run_freshness_probe`).
* **Dependencies:** Task 8.1.
* **Traceability:** FR-7.1, FR-7.2, FR-7.3, FR-7.4.
* **Artifacts:** `src/bigquery/client.py`, `src/agent/housekeeping.py`.
* - [ ] Implementation green; full suite passes

### Task 8.3 [TDD]: Usage Digest Counters & Instrumentation
* **Description:** Write failing unit tests for the thread-safe `UsageDigest` (accumulate, render, reset) and Gemini fallback degradation counting; implement `run_usage_digest` and instrument the analytics protocol security/execution boundaries and the Gemini router fallback paths.
* **Dependencies:** Task 8.2.
* **Traceability:** FR-7.4, FR-7.5, BDD-4.
* **Artifacts:** `src/agent/housekeeping.py`, `src/agent/protocols/analytics_protocol.py`, `src/nl_parser/gemini_router.py`.
* - [ ] Failing tests verified red, then implementation green; full suite passes

### Task 8.4: uAgents on_schedule Wiring & Startup Banner
* **Description:** Register the freshness probe (`0 6 * * *` UTC) and usage digest (`30 6 * * *` UTC) handlers in `src/agent/main.py` via `agent.on_schedule`, and extend the startup banner with the housekeeping schedule.
* **Dependencies:** Task 8.2, Task 8.3.
* **Traceability:** FR-7.1, FR-7.5.
* **Artifacts:** `src/agent/main.py`.
* - [ ] Full suite passes on wired tree; PR opened
