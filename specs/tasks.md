# Implementation Tasks & Test-Driven Execution Plan: On-Chain Analytics Oracle

**Document Version:** 1.0.0  
**Status:** Approved for Implementation  
**Traceability Base:** `specs/design.md` & `specs/requirements.md`  

---

## Overview & Execution Tracks

The implementation plan is structured into **6 modular execution tracks**, organized with explicit dependencies, parallelism opportunities, and strict Test-Driven Development (TDD) gates.

```
                      TRACK 1: Setup & Security Hardening
                                       │
                  ┌────────────────────┴────────────────────┐
                  ▼                                         ▼
   TRACK 2: BigQuery SQL & ETL             TRACK 3: BQ Client & Cache
   (Data Model & Queries)                  (Circuit Breakers & SDK)
                  │                                         │
                  └────────────────────┬────────────────────┘
                                       │
                  ┌────────────────────┴────────────────────┐
                  ▼                                         ▼
   TRACK 4: Gemini NL Router               TRACK 5: uAgents Protocol
   (Intent & Param Mapping)                (Agentverse Integration)
                  │                                         │
                  └────────────────────┬────────────────────┘
                                       ▼
                     TRACK 6: E2E Verification & Deployment
```

---

## Track 1: Foundational Setup & Security Hardening

### Task 1.1: Project Environment & Dependency Configuration
* **Description:** Initialize Python 3.11 virtual environment, configure `pyproject.toml` with `uagents`, `google-cloud-bigquery`, `google-genai`, `pydantic`, `pytest`, `pytest-asyncio`, and `python-dotenv`.
* **Dependencies:** None.
* **Traceability:** NFR-3, COST-2.
* **Artifacts:** `pyproject.toml`, `.env.example`, `.gitignore`.

### Task 1.2 [TDD]: Security Hardening & Rate Limiter Tests
* **Description:** Write comprehensive unit tests for the Token Bucket / Leaky Bucket rate limiter and input sanitization before implementing the security layer.
* **Dependencies:** Task 1.1.
* **Traceability:** SEC-1, BDD-3.
* **Artifacts:** `tests/test_security.py`.

### Task 1.3: Security Layer Implementation
* **Description:** Implement `src/agent/security/rate_limiter.py` (token bucket per `agent_address`) and `src/agent/security/circuit_breaker.py` (input sanitization, schema assertion, dynamic SQL blocking).
* **Dependencies:** Task 1.2.
* **Traceability:** SEC-1, SEC-3, FR-2.2.
* **Artifacts:** `src/agent/security/rate_limiter.py`, `src/agent/security/circuit_breaker.py`.

---

## Track 2: BigQuery SQL Templates & Datamart ETL Pipeline

> [!TIP]
> **PARALLEL EXECUTION:** Track 2 (SQL & ETL) can be developed concurrently with Track 3 (BigQuery Client & Cache).

### Task 2.1: Bitcoin UTXO HODL Wave & Micro-Transaction SQL Templates
* **Description:** Author parameterized ANSI SQL templates for:
  1. `btc_utxo_hodl_waves.sql`: Extracts daily UTXO age distributions across 7 age bands (`<24h` to `>2y`).
  2. `btc_microtransaction_density.sql`: Calculates daily transaction counts bucketed by value (<$10, $10–$500, >$50k) and historical fee-to-value drag.
* **Dependencies:** Task 1.1.
* **Traceability:** FR-1.1, FR-1.2, FR-1.3, US-1.
* **Artifacts:** `src/bigquery/sql_queries/btc_utxo_hodl_waves.sql`, `src/bigquery/sql_queries/btc_microtransaction_density.sql`.

### Task 2.2: USDC Organic Volume & EOA Topology SQL Templates
* **Description:** Author parameterized ANSI SQL templates for:
  1. `usdc_organic_vs_noise.sql`: Implements the Visa/Artemis noise filter on USDC ERC-20 transfers (`0xa0b8...`), isolating organic volume from bot/MEV loops.
  2. `usdc_eoa_vs_contract.sql`: Segregates P2P/merchant transfers (EOA $\rightarrow$ EOA) from DeFi contract interactions.
* **Dependencies:** Task 1.1.
* **Traceability:** FR-1.4, FR-1.5, US-1.
* **Artifacts:** `src/bigquery/sql_queries/usdc_organic_vs_noise.sql`, `src/bigquery/sql_queries/usdc_eoa_vs_contract.sql`.

### Task 2.3: Batch Datamart ETL Pipeline Script
* **Description:** Build `src/bigquery/etl_pipelines.py` to automate table creation and data materialization for `crypto_analytics_mart.btc_daily_utxo_distribution` and `crypto_analytics_mart.usdc_daily_organic_metrics` with date partitioning.
* **Dependencies:** Task 2.1, Task 2.2.
* **Traceability:** FR-1.1, FR-1.4, COST-2.
* **Artifacts:** `src/bigquery/etl_pipelines.py`.

---

## Track 3: Parameterized BigQuery Client & LRU Cache

### Task 3.1 [TDD]: BigQuery Client & Byte Limit Tests
* **Description:** Write unit tests using BigQuery client mocks to verify:
  1. `maximum_bytes_billed` is strictly configured on every job.
  2. Byte-limit exceeded exceptions are caught safely.
  3. Dynamic SQL attempts are rejected.
  4. LRU cache returns identical query results with 0 API calls.
* **Dependencies:** Task 1.1.
* **Traceability:** FR-2.1, FR-2.2, FR-2.3, SEC-3, COST-1, BDD-3.
* **Artifacts:** `tests/test_bigquery_client.py`.

### Task 3.2: BigQuery Client Implementation & In-Memory LRU Cache
* **Description:** Implement `src/bigquery/client.py` with parameterized execution, BigQuery query caching, 50 MB hard ceilings, and thread-safe in-memory LRU caching.
* **Dependencies:** Task 3.1.
* **Traceability:** FR-2.1, FR-2.3, SEC-3, COST-1, NFR-1.
* **Artifacts:** `src/bigquery/client.py`.

---

## Track 4: Gemini Natural Language Query Router

> [!TIP]
> **PARALLEL EXECUTION:** Track 4 (NL Router) can be developed concurrently with Track 5 (uAgents Protocol).

### Task 4.1 [TDD]: Natural Language Semantic Router Tests
* **Description:** Write tests verifying that various user prompts correctly map to validated `AnalyticsQueryRequest` objects (with start/end dates and query types) and that out-of-scope prompts return guidance.
* **Dependencies:** Task 1.1.
* **Traceability:** FR-3.1, FR-3.2, FR-3.3.
* **Artifacts:** `tests/test_gemini_router.py`.

### Task 4.2: Gemini Flash Semantic Query Router Implementation
* **Description:** Implement `src/nl_parser/gemini_router.py` using `google-genai` (Gemini Flash) with structured JSON output schema to translate natural language prompts into typed analytical requests.
* **Dependencies:** Task 4.1.
* **Traceability:** FR-3.1, FR-3.2, FR-3.3.
* **Artifacts:** `src/nl_parser/gemini_router.py`.

---

## Track 5: uAgents Protocol & Agentverse Integration

### Task 5.1 [TDD]: Agentverse Message Protocol Tests
* **Description:** Write BDD tests for the `blockchain_analytics_protocol_v1` message handlers, testing successful request/response encoding, error handling, rate limiting integration, and empirical summary formatting.
* **Dependencies:** Task 1.3, Task 3.2.
* **Traceability:** FR-4.1, FR-4.2, FR-4.3, BDD-1, BDD-2.
* **Artifacts:** `tests/test_protocols.py`.

### Task 5.2: uAgents Protocol & Handler Implementation
* **Description:** Implement `src/agent/protocols/analytics_protocol.py` defining Pydantic models `AnalyticsQueryRequest` and `AnalyticsQueryResponse`, wiring the protocol handler to the security layer, NL router, and BigQuery client.
* **Dependencies:** Task 5.1.
* **Traceability:** FR-4.2, FR-4.3, SEC-1.
* **Artifacts:** `src/agent/protocols/analytics_protocol.py`.

### Task 5.3: Agent Main Runner & Agentverse Mailbox Registration
* **Description:** Implement `src/agent/main.py` configuring the `Agent` instance with cryptographic wallet seed, Agentverse Mailbox endpoint, and startup banner with endpoint metadata.
* **Dependencies:** Task 5.2.
* **Traceability:** FR-4.1, NFR-3, US-2.
* **Artifacts:** `src/agent/main.py`.

---

## Track 6: End-to-End Verification & Research Artifact Generation

### Task 6.1: Test Suite Execution & 100% Pass Verification
* **Description:** Execute `pytest` across all unit, security, and protocol test suites. Verify 100% pass rate and zero security regressions.
* **Dependencies:** Tasks 1.3, 2.3, 3.2, 4.2, 5.3.
* **Traceability:** SEC-1, COST-1, BDD-1, BDD-2, BDD-3.
* **Artifacts:** `tests/`.

### Task 6.2: Comprehensive Research Artifact & Documentation
* **Description:** Generate `README.md` and research documentation providing the complete empirical retrospective on 10+ years of Bitcoin and USDC data, deployment guide for Agentverse, and reproducible BigQuery instructions.
* **Dependencies:** Task 6.1.
* **Traceability:** US-1, US-2, US-3.
* **Artifacts:** `README.md`.
