# Requirements Specification: On-Chain Analytics Oracle & Blockchain Data Agent

**Document Version:** 1.3.0  
**Status:** Approved for Implementation  
**Traceability Base:** `specs/design.md` (v1.3.0)  
**LLM Engine:** Gemini 3.7 Flash (`gemini-3.7-flash`)  
**Time Horizon:** 2014–2026 Baseline Audit + Continuous Monthly Incremental Ingestion (2027+)  
**Scheduler Infrastructure:** Google Cloud Scheduler & BigQuery Scheduled Queries (`0 0 1 * *` UTC)

---

## 1. User Stories

### US-1: Empirical Blockchain Researcher
> *As a* cryptocurrency researcher or data scientist,  
> *I want to* inspect a decade of Bitcoin UTXO age distributions and USDC organic transaction metrics (from 2014 to 2026 and ongoing into 2027+) via interactive Marimo notebooks with rich \(\LaTeX\) formulations and statistical charts,  
> *So that I can* empirically test whether crypto is functioning as an everyday medium of exchange or purely as a speculative store of value.

### US-2: ASI Agentverse Autonomous Consumer
> *As an* autonomous trading or governance agent on Fetch.ai's Agentverse,  
> *I want to* query up-to-date Bitcoin and USDC on-chain metrics across both historical decades and newly confirmed monthly blocks,  
> *So that I can* retrieve verified economic signals without managing cloud infrastructure or running SQL pipelines.

### US-3: System Owner & Cost Administrator
> *As the* GCP project owner,  
> *I want* Google Cloud to manage the monthly cron job serverlessly (Cloud Scheduler / BigQuery Scheduled Queries) to ingest only the previous month's delta (<25 GB),  
> *So that* ingestion runs reliably on Google's infrastructure with 99.99% uptime while keeping monthly GCP query costs completely within the Always-Free Tier ($0.00/month).

---

## 2. Functional Requirements (FR)

### FR-1: Curated Datamart Batch & Incremental ETL Pipelines
* **FR-1.1:** The system shall provide a BigQuery batch ETL script (`src/bigquery/etl_pipelines.py`) that queries `bigquery-public-data.crypto_bitcoin` to generate the 2014–2026 `crypto_analytics_mart.btc_daily_utxo_distribution` table.
* **FR-1.2:** The Bitcoin ETL shall categorize all unspent outputs into 7 standard HODL age bands (`<24h`, `1d-1w`, `1w-1m`, `1m-6m`, `6m-1y`, `1y-2y`, `>2y`) for each calendar day from 2014 to present.
* **FR-1.3:** The Bitcoin ETL shall bucket transaction output values into Micro (<$10), Retail ($10–$500), and Whale (>$50,000) counts, and compute the average fee-to-value drag ratio.
* **FR-1.4:** The system shall provide an Ethereum batch ETL script that queries `bigquery-public-data.crypto_ethereum.token_transfers` for USDC contract `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` to generate `crypto_analytics_mart.usdc_daily_organic_metrics`.
* **FR-1.5:** The USDC ETL shall apply the Visa/Artemis noise filter (excluding wallets with >1,000 tx/month or >$10M monthly volume) to compute organic vs. raw volume and EOA-to-EOA (retail) vs. EOA-to-Contract (DeFi) volume.
* **FR-1.6 (Google Cloud Managed Monthly Ingestion):** The system shall provide automated Google Cloud Scheduler / BigQuery Scheduled Query configurations that execute on the 1st of every month at `00:00 UTC` (`0 0 1 * *`), running the scoped `MERGE INTO` SQL queries to append the previous month's delta without human intervention.

### FR-2: Parameterized BigQuery Client & Guardrails
* **FR-2.1:** The BigQuery client (`src/bigquery/client.py`) shall enforce parameterized query execution for all analytical templates (`btc_hodl_waves`, `btc_microtransactions`, `usdc_organic_volume`, `usdc_eoa_topology`).
* **FR-2.2:** The client shall strictly validate SQL identifiers and forbid dynamic SQL string formatting to ensure total immunity to SQL injection.
* **FR-2.3:** The client shall configure `QueryJobConfig(maximum_bytes_billed=50_000_000, use_query_cache=True)` on every execution.
* **FR-2.4:** The client shall support true multi-granularity time series aggregation (daily, monthly, yearly) using mathematically weighted period ratios.

### FR-3: Gemini 3.7 Flash Natural Language Query Router
* **FR-3.1:** The system shall provide a natural language parser (`src/nl_parser/gemini_router.py`) powered explicitly by **Gemini 3.7 Flash (`gemini-3.7-flash`)** via `google-genai`.
* **FR-3.2:** The router shall map incoming user/agent prompts into a structured `AnalyticsQueryRequest` with strict type validation.

### FR-4: ASI Agentverse / uAgents Protocol
* **FR-4.1:** The agent (`src/agent/main.py`) shall instantiate a Fetch.ai `Agent` with persistent cryptographic identity and Mailbox connectivity.
* **FR-4.2:** The agent shall register the `blockchain_analytics_protocol_v1` protocol handling `AnalyticsQueryRequest` and returning `AnalyticsQueryResponse`.
* **FR-4.3:** The agent shall execute BigQuery calls asynchronously (`asyncio.to_thread`) to prevent blocking the event loop.

### FR-5: Marimo Interactive Research Notebooks & Visualizations
* **FR-5.1:** The system shall provide two reactive Marimo notebooks (`notebooks/btc_analysis.py` and `notebooks/usdc_analysis.py`).
* **FR-5.2:** Each code cell in the Marimo notebooks must be preceded by an explanatory markdown cell documenting the economic hypothesis, statistical methodology, and \(\LaTeX\) equations.
* **FR-5.3:** The notebooks shall render interactive publication-quality charts (Plotly) for HODL waves, fee-to-value drag curves, organic vs. bot waterfalls, and counterparty topology.

---

## 3. Behavior-Driven Development (BDD) Acceptance Criteria

### BDD-1: Querying Bitcoin UTXO HODL Waves
```gherkin
Feature: Bitcoin UTXO Age Distribution Analysis
  Scenario: External agent requests 2014-2026 Bitcoin HODL age bands
    Given an external agent sends an AnalyticsQueryRequest for "btc_hodl_waves" from "2014-01-01" to "2026-01-01"
    When the query passes rate limiting and input validation
    And the BigQuery client executes the parameterized query against crypto_analytics_mart.btc_daily_utxo_distribution
    Then the response status is "SUCCESS"
    And bytes_scanned_mb is less than 10.0 MB
    And the response contains percentage bands for "<24h", "1y-2y", and ">2y"
```

### BDD-2: Google Cloud Managed Monthly Incremental Ingestion
```gherkin
Feature: Serverless Monthly Incremental Ingestion
  Scenario: Google Cloud Scheduler triggers monthly BigQuery ingestion (0 0 1 * *)
    Given the GCP Cloud Scheduler executes at the start of a new month (e.g. 2027-01-01 00:00 UTC)
    When BigQuery runs the scheduled MERGE INTO query for the previous month partition
    Then the job scans only the single previous month delta (<25 GB)
    And new daily records are merged into btc_daily_utxo_distribution and usdc_daily_organic_metrics
    And subsequent queries for that month return fresh data with 100% serverless automation
```
