# Requirements Specification: On-Chain Analytics Oracle & Blockchain Data Agent

**Document Version:** 1.0.0  
**Status:** Approved for Implementation  
**Traceability Base:** `specs/design.md`  

---

## 1. User Stories

### US-1: Empirical Blockchain Researcher
> *As a* cryptocurrency researcher or data scientist,  
> *I want to* inspect a decade of Bitcoin UTXO age distributions and USDC organic transaction metrics,  
> *So that I can* empirically prove whether crypto is functioning as an everyday medium of exchange or purely as a speculative store of value.

### US-2: ASI Agentverse Autonomous Consumer
> *As an* autonomous trading or governance agent on Fetch.ai's Agentverse,  
> *I want to* send structured or natural language analytical queries to the Analytics Oracle,  
> *So that I can* retrieve noise-filtered on-chain volume and retail ratios without running heavy cloud infrastructure or SQL pipelines myself.

### US-3: System Owner & Cost Administrator
> *As the* GCP project owner,  
> *I want* multi-layered security circuit breakers, hard BigQuery byte limits (50 MB), and rate limiters,  
> *So that* malicious actors, bots, or script kiddies on Agentverse cannot drain my GCP billing account or exceed the free tier.

---

## 2. Functional Requirements (FR)

### FR-1: Curated Datamart Batch ETL Pipelines
* **FR-1.1:** The system shall provide a BigQuery batch ETL script (`src/bigquery/etl_pipelines.py`) that queries `bigquery-public-data.crypto_bitcoin` to generate the `crypto_analytics_mart.btc_daily_utxo_distribution` table.
* **FR-1.2:** The Bitcoin ETL shall categorize all unspent outputs into 7 standard HODL age bands (`<24h`, `1d-1w`, `1w-1m`, `1m-6m`, `6m-1y`, `1y-2y`, `>2y`) for each calendar day from 2014 to present.
* **FR-1.3:** The Bitcoin ETL shall bucket transaction output values into Micro (<$10), Retail ($10–$500), and Whale (>$50,000) counts, and compute the average fee-to-value drag ratio.
* **FR-1.4:** The system shall provide an Ethereum batch ETL script that queries `bigquery-public-data.crypto_ethereum.token_transfers` for USDC contract `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` to generate `crypto_analytics_mart.usdc_daily_organic_metrics`.
* **FR-1.5:** The USDC ETL shall apply the Visa/Artemis noise filter (excluding wallets with >1,000 tx/month or >$10M monthly volume) to compute organic vs. raw volume and EOA-to-EOA (retail) vs. EOA-to-Contract (DeFi) volume.

### FR-2: Parameterized BigQuery Client & Guardrails
* **FR-2.1:** The BigQuery client (`src/bigquery/client.py`) shall enforce parameterized query execution for all analytical templates (`btc_hodl_waves`, `btc_microtransactions`, `usdc_organic_volume`, `eoa_topology`).
* **FR-2.2:** The client shall strictly forbid dynamic SQL string formatting to ensure total immunity to SQL injection.
* **FR-2.3:** The client shall configure `QueryJobConfig(maximum_bytes_billed=50_000_000, use_query_cache=True)` on every execution.

### FR-3: Natural Language Query Router
* **FR-3.1:** The system shall provide a natural language parser (`src/nl_parser/gemini_router.py`) powered by Gemini Flash via `google-genai`.
* **FR-3.2:** The router shall map incoming user/agent prompts (e.g. *"Show me the percentage of Bitcoin unspent for over 2 years in 2025"*) into a structured `AnalyticsQueryRequest` with strict type validation.
* **FR-3.3:** If an incoming prompt cannot be mapped to an authorized analytical template, the router shall return a helpful schema clarification without executing any cloud query.

### FR-4: ASI Agentverse / uAgents Protocol
* **FR-4.1:** The agent (`src/agent/main.py`) shall instantiate a Fetch.ai `Agent` with persistent cryptographic identity and Mailbox connectivity.
* **FR-4.2:** The agent shall register the `blockchain_analytics_protocol_v1` protocol handling `AnalyticsQueryRequest` and returning `AnalyticsQueryResponse`.
* **FR-4.3:** The agent shall include human-readable empirical interpretations, key statistical metrics, bytes scanned, and the reproducible SQL template in every successful response.

---

## 3. Security & Cost Requirements (SEC & COST)

* **SEC-1 (Token Bucket Rate Limiting):** The agent shall enforce a rate limit of maximum 5 requests per minute and 30 requests per day per caller address/IP. Requests exceeding this threshold shall receive a structured `RATE_LIMITED` error response without triggering BigQuery.
* **SEC-2 (Least-Privilege IAM):** The runtime GCP credentials must only possess `roles/bigquery.dataViewer` on the `crypto_analytics_mart` dataset and `roles/bigquery.jobUser` on the project.
* **SEC-3 (Result Caching):** The agent shall maintain an in-memory LRU cache (capacity 500 entries, TTL 24 hours). Identical parameter requests shall be served from cache in < 5ms with zero BigQuery scans.
* **COST-1 (Bytes Billed Ceiling):** BigQuery queries must never exceed 50 MB scanned per query job. If a query attempts to scan > 50 MB, the client will immediately trap the BigQuery rejection error and return a safe error message.
* **COST-2 (Monthly Free Tier Compliance):** Total monthly storage of the curated datamart shall remain under 100 MB, and monthly query scan volume shall remain under 10 GB (well below the GCP 1,000 GB Always-Free quota).

---

## 4. Non-Functional Requirements (NFR)

* **NFR-1 (Latency):** Cached queries shall return in < 10ms; uncached datamart queries shall return in < 2.5 seconds.
* **NFR-2 (Reproducibility):** All SQL templates must be standard ANSI SQL executable in BigQuery Studio without proprietary dependencies.
* **NFR-3 (Availability):** The uAgent process must support running as a continuous background daemon with automatic reconnection to the Agentverse Mailbox.

---

## 5. Behavior-Driven Development (BDD) Acceptance Criteria

### BDD-1: Querying Bitcoin UTXO HODL Waves
```gherkin
Feature: Bitcoin UTXO Age Distribution Analysis
  Scenario: External agent requests 2024-2026 Bitcoin HODL age bands
    Given an external agent sends an AnalyticsQueryRequest for "btc_hodl_waves" from "2024-01-01" to "2026-01-01"
    When the query passes rate limiting and input validation
    And the BigQuery client executes the parameterized query against crypto_analytics_mart.btc_daily_utxo_distribution
    Then the response status is "SUCCESS"
    And bytes_scanned_mb is less than 10.0 MB
    And the response contains percentage bands for "<24h", "1y-2y", and ">2y"
    And the empirical summary highlights the proportion of dormant supply (>2y)
```

### BDD-2: Querying USDC Organic vs. Bot Volume
```gherkin
Feature: USDC Organic Payment Volume Filtering
  Scenario: External agent requests organic vs noise breakdown
    Given a request for "usdc_organic_volume" for year "2025"
    When the query is executed against crypto_analytics_mart.usdc_daily_organic_metrics
    Then the response status is "SUCCESS"
    And organic_volume_ratio is returned between 0.15 and 0.40
    And the response explicitly differentiates EOA-to-EOA commerce volume from EOA-to-Contract DeFi volume
```

### BDD-3: Defense-in-Depth Malicious Flood & Byte Limit Protection
```gherkin
Feature: Security Hardening and Billing Protection
  Scenario: Malicious actor attempts to spam the agent with 20 requests in 5 seconds
    Given an unauthorized script sends 20 rapid requests from a single agent_address
    When the first 5 requests are processed
    Then the subsequent 15 requests are immediately rejected with status "RATE_LIMITED"
    And zero BigQuery jobs are initiated for the rejected requests

  Scenario: Query exceeds 50 MB byte limit
    Given an abnormal query configuration that would scan 200 MB
    When BigQuery evaluates maximum_bytes_billed = 50_000_000
    Then the BigQuery job is aborted by the GCP engine before execution
    And the agent returns a safe error without incurring billing charges
```
