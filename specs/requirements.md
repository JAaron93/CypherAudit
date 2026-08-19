# Requirements Specification: On-Chain Analytics Oracle & Blockchain Data Agent

**Document Version:** 1.1.0  
**Status:** Approved for Implementation  
**Traceability Base:** `specs/design.md` (v1.1.0)  
**LLM Engine:** Gemini 3.7 Flash (`gemini-3.7-flash`)

---

## 1. User Stories

### US-1: Empirical Blockchain Researcher
> *As a* cryptocurrency researcher or data scientist,  
> *I want to* inspect a decade of Bitcoin UTXO age distributions and USDC organic transaction metrics via interactive Marimo notebooks with rich \(\LaTeX\) formulations and statistical charts,  
> *So that I can* empirically test whether crypto is functioning as an everyday medium of exchange or purely as a speculative store of value.

### US-2: ASI Agentverse Autonomous Consumer
> *As an* autonomous trading or governance agent on Fetch.ai's Agentverse,  
> *I want to* send natural language or structured queries parsed by Gemini 3.7 Flash to the Analytics Oracle,  
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
* **FR-2.1:** The BigQuery client (`src/bigquery/client.py`) shall enforce parameterized query execution for all analytical templates (`btc_hodl_waves`, `btc_microtransactions`, `usdc_organic_volume`, `usdc_eoa_topology`).
* **FR-2.2:** The client shall strictly forbid dynamic SQL string formatting to ensure total immunity to SQL injection.
* **FR-2.3:** The client shall configure `QueryJobConfig(maximum_bytes_billed=50_000_000, use_query_cache=True)` on every execution.

### FR-3: Gemini 3.7 Flash Natural Language Query Router
* **FR-3.1:** The system shall provide a natural language parser (`src/nl_parser/gemini_router.py`) powered explicitly by **Gemini 3.7 Flash (`gemini-3.7-flash`)** via `google-genai`.
* **FR-3.2:** The router shall map incoming user/agent prompts into a structured `AnalyticsQueryRequest` with strict type validation.
* **FR-3.3:** If an incoming prompt cannot be mapped to an authorized analytical template, the router shall return a helpful schema clarification without executing any cloud query.

### FR-4: ASI Agentverse / uAgents Protocol
* **FR-4.1:** The agent (`src/agent/main.py`) shall instantiate a Fetch.ai `Agent` with persistent cryptographic identity and Mailbox connectivity.
* **FR-4.2:** The agent shall register the `blockchain_analytics_protocol_v1` protocol handling `AnalyticsQueryRequest` and returning `AnalyticsQueryResponse`.
* **FR-4.3:** The agent shall include human-readable empirical interpretations, key statistical metrics, bytes scanned, and the reproducible SQL template in every successful response.

### FR-5: Marimo Interactive Research Notebooks & Visualizations
* **FR-5.1:** The system shall provide two reactive Marimo notebooks:
  1. `notebooks/btc_analysis.py`: Bitcoin UTXO HODL age bands, velocity decay, and fee drag analysis.
  2. `notebooks/usdc_analysis.py`: USDC organic vs. bot noise volume, retail sizing, and EOA counterparty topology.
* **FR-5.2:** Each code cell in the Marimo notebooks must be preceded by an explanatory markdown cell documenting the economic hypothesis, statistical methodology, and \(\LaTeX\) equations.
* **FR-5.3:** The notebooks shall render interactive publication-quality charts (Plotly) including:
  * 10-year Bitcoin HODL wave stacked area distribution.
  * Fee-to-value drag percentage curves on microtransactions (\$10, \$50, \$100).
  * USDC Organic vs. Bot volume waterfall and ratio time series.
  * Counterparty topology donut / breakdown charts (EOA $\rightarrow$ EOA vs EOA $\rightarrow$ Contract).
* **FR-5.4:** The notebooks shall execute BigQuery data retrieval in dedicated data-loading cells with caching before executing downstream analytical cells.

---

## 3. Security & Cost Requirements (SEC & COST)

* **SEC-1 (Token Bucket Rate Limiting):** Max 5 req/min and 30 req/day per caller address/IP.
* **SEC-2 (Least-Privilege IAM):** Read-only `roles/bigquery.dataViewer` on `crypto_analytics_mart`.
* **SEC-3 (Result Caching):** In-memory LRU cache (500 capacity, 24h TTL) serving duplicate queries in < 5ms with zero BQ scans.
* **COST-1 (Bytes Billed Ceiling):** BigQuery queries must never exceed 50 MB scanned per query job (`maximum_bytes_billed = 50_000_000`).
* **COST-2 (Monthly Free Tier Compliance):** Total monthly storage < 100 MB, query scan volume < 10 GB (well below the 1,000 GB GCP Always-Free quota).

---

## 4. Behavior-Driven Development (BDD) Acceptance Criteria

### BDD-1: Querying Bitcoin UTXO HODL Waves via BigQuery Client
```gherkin
Feature: Bitcoin UTXO Age Distribution Analysis
  Scenario: External agent requests 2024-2026 Bitcoin HODL age bands
    Given an external agent sends an AnalyticsQueryRequest for "btc_hodl_waves" from "2024-01-01" to "2026-01-01"
    When the query passes rate limiting and input validation
    And the BigQuery client executes the parameterized query against crypto_analytics_mart.btc_daily_utxo_distribution
    Then the response status is "SUCCESS"
    And bytes_scanned_mb is less than 10.0 MB
    And the response contains percentage bands for "<24h", "1y-2y", and ">2y"
```

### BDD-2: Marimo Interactive Visualizations and LaTeX Formulations
```gherkin
Feature: Interactive Marimo Research Notebooks
  Scenario: Data scientist launches Bitcoin Marimo notebook
    Given the user starts the Marimo reactive notebook "notebooks/btc_analysis.py"
    When the BigQuery client retrieves the 10-year HODL distribution dataset
    Then the notebook displays the LaTeX velocity formula: V = Y / M
    And an interactive Plotly stacked area chart of HODL age bands is rendered
    And an interactive fee drag curve showing retail purchase economic irrationality is displayed

  Scenario: Data scientist launches USDC Marimo notebook
    Given the user starts the Marimo reactive notebook "notebooks/usdc_analysis.py"
    When the BigQuery client retrieves the organic metrics dataset
    Then the notebook displays the LaTeX organic ratio formula: \Phi_{organic} = \sum V_{organic} / \sum V_{raw}
    And an interactive Plotly chart displays the 70%+ bot noise vs 30% organic volume ratio
    And an EOA-to-EOA commerce vs DeFi contract interaction chart is rendered
```

### BDD-3: Defense-in-Depth Malicious Flood & Byte Limit Protection
```gherkin
Feature: Security Hardening and Billing Protection
  Scenario: Malicious actor attempts to spam the agent with 20 requests in 5 seconds
    Given an unauthorized script sends 20 rapid requests from a single agent_address
    When the first 5 requests are processed
    Then the subsequent 15 requests are immediately rejected with status "RATE_LIMITED"
    And zero BigQuery jobs are initiated for the rejected requests
```
