# AGENTS.md: SignalChain Oracle (CypherAudit) Agent Guidelines

This document governs the architecture, development principles, tool routing discipline, and security guardrails for any AI agent working on the **CypherAudit** repository (**SignalChain Oracle**).

---

## 1. Project Overview & Research Telos

* **Project Name:** CypherAudit
* **Agent Name:** SignalChain Oracle
* **Target Ecosystem:** Fetch.ai / ASI Agentverse Autonomous Analytics Oracle & Marimo Research Hub
* **LLM Engine:** Gemini 3.8 Flash (`gemini-3.8-flash`) via `google-genai`
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
 │ • `notebooks/btc_analysis.py` (Spec)      │ │ • `src/agent/main.py` (Spec)           │
 │ • `notebooks/usdc_analysis.py` (Spec)     │ │ • `src/agent/protocols/` (Pydantic v2) │
 │ • LaTeX formulas & Plotly visualizers     │ │ • `src/agent/security/` (Token Bucket)   │
 │ • Export: `marimo export html-wasm`       │ │ • `src/nl_parser/` (Gemini 3.8 Flash)    │
 │ • Deploy: GitHub Pages / molab ($0/mo)    │ │ • `src/bigquery/client.py` (LRU Cache)   │
 │                                           │ │ • `src/agent/housekeeping.py` (Monitor)  │
 └───────────────────────────────────────────┘ └──────────────────────────────────────────┘
```

---

## 3. Mandatory Tool Routing Protocol

Always route investigations through specialized tools before running raw terminal commands. When a task is initiated, pause, evaluate equipped skills, and route workflows through specialized tools first.

### 3.1 Mandatory Skill & Execution Invocation Order
1. **Step 1: Domain Documentation & Syntax Queries:** When you need to understand syntax, framework rules, or external library parameters, invoke the `gemini-documentation-router` skill first. Never guess syntax or sweep local directories for documentation files.
2. **Step 2: Codebase Exploration & Dependency Mapping (AST Graph):** When navigating the repository to locate functions, classes, or call chains, use `codebase-memory-mcp` structural graph tools (`search_graph`, `trace_path`, `get_code_snippet`, `query_graph`). Query the embedded SQLite Abstract Syntax Tree (AST) graph to trace relationships in milliseconds. Avoid unindexed raw file sweeps as a first resort.
3. **Step 3: CLI-First for Stateless Execution & External Services:** For all Git operations, GitHub workflows, cloud management, containers, and build processes, operate directly through native CLI tools (`gh`, `git`, `gcloud`, `aws`, `docker`) paired with companion skills rather than stateless MCP servers.
4. **Step 4: PR & Code Review Iteration:** Use `greptile-greploop` to trigger reviews, resolve comments, and iterate until 5/5 confidence is achieved.

### 3.2 MCP Scope & Stateful Boundaries
Antigravity operates on a **CLI-first, stateful-MCP-sparing architecture**:

> [!NOTE]
> **Developer Tooling Scope vs. Runtime Application Architecture**:
> This CLI-first doctrine governs **Software Engineering Agents (SEAs), coding assistants, and developer workflows** (version control, PR management, testing, builds, containers, and environment inspection). The **runtime application itself** runs purely through its native platform SDKs/in-process architecture (e.g., `google.cloud.bigquery`, `google-genai`, `uagents`, `pydantic`); agents and review bots must **never** conflate developer tool routing with runtime application architecture or demand that runtime services shell out to CLI binaries.

- **MCP Reserved Tier (Stateful & Daemon Integrations Only):**
  - **AST Knowledge Graph:** `codebase-memory-mcp` maintains the persistent SQLite Abstract Syntax Tree graph for codebase navigation and call-graph tracing.
  - **External Library Documentation:** `context7` resolves third-party package syntax and API definitions.
  - **Live Browser Sessions:** `chrome-devtools` and `axe-core` manage interactive Chrome DevTools Protocol (CDP) sessions and accessibility validation.
  - **Automated Review Agent Gateways:** `greptile` triggers and manages PR code reviews.
- **CLI Tier (Stateless Operations):**
  - All version control, pull requests, issues, cloud infrastructure, container management, and build tasks MUST execute through native CLI tools (`gh`, `git`, `gcloud`, `aws`, `docker`, `cargo`, `npm`, etc.) paired with lightweight companion skills.

### 3.3 Architectural Perpetuation & Downstream Agent Invariant
This CLI-first, MCP-sparing doctrine is a permanent, indefinite architectural standard. All future agents, subagents, and automated workflows governed by this constitution must:
1. **Perpetuate the Pattern**: When recommending, designing, or scaffolding new tools, integrations, or workflows, agents must prioritize CLI binaries paired with lightweight skills rather than introducing new MCP servers.
2. **Defend the Boundaries**: Strictly reject the addition of stateless MCP servers (e.g. for GitHub, Git, Jira, Slack, Linear, Stripe, or cloud providers) whenever a mature CLI tool or scriptable API exists. Reserve MCP exclusively for persistent stateful daemons, database connections, AST memory graphs, and the designated Reserved Tier.
3. **Propagate to Project Invariants**: When authoring repository-level `AGENTS.md`, `.cursor/rules/`, or subagent system prompts, agents must explicitly codify this CLI-first discipline with an explicit scope demarcation separating developer tooling from runtime application architecture to prevent review bot context blindness.

---

## 4. Cost Guardrails & Safety Boundaries ($0.00/Month Ceiling)

All code and queries MUST strictly comply with the **Always-Free Tier** ceilings:

* **Hard BigQuery Byte Limit:** All runtime queries in `src/bigquery/client.py` must enforce `maximum_bytes_billed = 50_000_000` (50 MB).
* **Batch/Monthly Ingestion Cap:** Monthly incremental ETL in `src/bigquery/etl_pipelines.py` must enforce `maximum_bytes_billed = 50_000_000_000` (50 GB).
* **Identifier Sanitization:** Never concatenate raw strings into SQL queries. Always validate `project_id` and `dataset_id` using `validate_identifier` (`^[a-zA-Z0-9_\-\.]+$`).
* **Rate Limiting:** Every incoming agent query must pass through the Token Bucket Rate Limiter (`5 req/min`, `30 req/day` per agent address).
* **Asynchronous Execution:** BigQuery execution within uAgents event handlers must use `await asyncio.to_thread(...)` to prevent blocking the async event loop.
* **Ratio Weighting Invariance:** Multi-day periodic aggregations must strictly weight daily percentages and averages by their true underlying base denominator (e.g., transaction counts for fees, total active coin supply for UTXO age bands).
* **Calibrated Ingestion Ceilings:** Multi-year baseline ETL jobs scanning cumulative history (e.g. Bitcoin outputs) must set bounded but realistic ceilings (`2.5 TB`) to prevent false-rejection during datamart backfills.

---

## 5. Development & Test-Driven Verification (TDD)

### 5.1 Virtual Environment & Strict TDD Workflow
* **Virtual Environment:** Always use the dedicated virtual environment:
  ```bash
  source .venv/bin/activate
  # or
  PYTHONPATH=. .venv/bin/pytest tests/ -v
  ```
* **Strict TDD Sequence:** All feature creation and bug fixes must be preceded by an AI-generated failing unit test or reproduction command. Write the test, verify that it fails, generate the minimum code required to pass, and re-verify.
* **Progressive Commit Verification:** Run the full local test suite after **every single commit**. Never batch multiple unverified commits.
* **The 3-Strike Hard Stop:** If the local test pass rate drops below the 90% threshold after three consecutive passes or refactoring loops, immediately cease code generation, revert uncommitted failing modifications, and alert the developer.

### 5.2 Universal Version Control & Terminal Deny List
To prevent repository corruption, supply-chain injection, and branch wiping during automated loops, the following terminal patterns are strictly barred:
* **No Remote Tampering:** Never execute `git remote add*`, `git remote set-url*`, or `git remote remove*`.
* **No Untrusted Submodules:** Never execute `git submodule add*` or `git submodule update --init*`.

### 5.3 GitHub CLI (`gh`) & Git Operational Guardrails
1. **Feature Branches Only:** All code modifications must occur within an isolated git worktree and be pushed to a dedicated feature branch. Direct commits or pushes to `main` and `master` are strictly prohibited.
2. **No Autonomous Merging:** You may create Pull Requests via `gh pr create` and inspect reviews via `gh pr view`, but you are strictly forbidden from merging Pull Requests via the terminal (`gh pr merge` is prohibited) or any API. A human must review and merge all code.
3. **Output Token Hygiene for `gh` Queries:** Never execute bare `gh` commands that dump unbounded JSON or table rows. Always constrain queries using `--json <fields>`, `--limit <N>`, or pipe through `jq` (e.g., `gh pr list --limit 10 --json number,title,author,headRefName,state`).
4. **No Destructive API / CLI Actions:** Repository deletion, branch protection tampering, and visibility modifications are blocked at the token level and strictly prohibited by rule.
5. **Pre-Commit Hygiene:** Before staging files via `git add`, verify that no `.env` files, API keys, credentials, or `.sqlite` WAL files are included in the commit payload.

### 5.4 File System Preferences & Blocked Shell Commands
* **Preferred File Patterns:**
  * Use `rsync` for copying/moving files (`rsync -avhP SOURCE/ DEST/`).
  * Use `tee` for file pipelines (`command | tee FILE` or `command | tee -a FILE`).
  * Use `git` for tracked source changes, status checks, diffs, and cleanups.
* **Disallowed Command Families:**
  * Do not use `mv`, `cp`, `>`, or `>>` as default file manipulation methods. Rewrite tasks using `rsync` or `tee`.

### 5.5 CLI Output Hygiene & Token Conservation Protocol
To maintain strict token economy across long-running sessions, adhere to output-limiting practices whenever running terminal CLI tools:
* **Scoped Query Projection Flags:** When running structured query, list, or inspection subcommands on tools with projection support (`gh`, `gcloud`, `aws`, `docker`), specify output projections:
  * `gh`: Use `--json <field1,field2>` and `--limit <N>` on list/query subcommands (e.g. `gh pr list`, `gh issue list`, `gh run list`).
  * `gcloud`: Use `--format="value(field)"` or `--format="table(field1,field2)"` on list/describe queries.
  * `docker`: Use `--format "{{.ID}}: {{.Names}} ({{.Status}})"` on `ps`, `images`, or `inspect`.
  For non-query subcommands (e.g., `docker build`, `gh pr create`), buffer outputs to a scratch file rather than piping through filters to prevent masking upstream non-zero exit codes. Never pipe interactive authentication commands (e.g., `gcloud auth login`).
* **Unix Pipeline Filtering for Diagnostic Output:** Direct Unix pipeline filters (`jq`, `head -n <N>`, `grep`, `awk`, `cut`) are reserved for read-only query and diagnostic streams (e.g., `gh run view <id> --log-failed | head -n 50`). When pipelines are executed in scripts or multi-command chains, ensure exit codes are preserved (e.g., using `set -o pipefail`).
* **Scratch File Buffering for Large Outputs:** If a diagnostic command or test run generates more than 100 lines of logs, redirect or tee it to the conversation scratch directory and inspect targeted segments with `grep` or `head` rather than dumping the full trace into context.
* **Atomic Pipelines Over Chatty Turns:** Prefer chaining commands in a single shell invocation using `&&` or pipelines (`|`) rather than executing separate single-command tool calls across multiple conversational turns.

### 5.6 Dynamic Rust Toolchain Discovery
When building Rust extensions or packages in local virtual environments, dynamically prepend the active Rust toolchain binary directory to `PATH` before compiling:
```bash
export PATH="$(rustup which rustc 2>/dev/null | xargs dirname || echo "$HOME/.cargo/bin"):$PATH"
```

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
│   └── foundation-spec/
│       ├── design.md                  # System architecture & mathematical formulations (v1.6.0)
│       ├── requirements.md            # Functional requirements & BDD acceptance tests (v1.6.0)
│       └── tasks.md                   # Modular execution tracks & task list (v1.6.0)
├── src/
│   ├── agent/
│   │   ├── main.py                    # uAgent main entrypoint & Agentverse registration
│   │   ├── prompts/
│   │   │   └── oracle_instructions.md # Decoupled Oracle research persona & synthesis prompt
│   │   ├── protocols/
│   │   │   └── analytics_protocol.py  # Pydantic v2 request/response protocol
│   │   ├── housekeeping.py            # Scheduled freshness probe & usage digest (on_schedule)
│   │   └── security/
│   │       ├── circuit_breaker.py     # Parameter validation & circuit breaker
│   │       └── rate_limiter.py        # Token bucket per-agent rate limiter
│   ├── bigquery/
│   │   ├── client.py                  # Parameterized client, weighted aggregator & LRU cache
│   │   ├── etl_pipelines.py           # Historical baseline & monthly incremental ETL
│   │   └── sql_queries/               # Parameterized SQL query templates
│   └── nl_parser/
│       └── gemini_router.py           # Gemini 3.8 Flash semantic intent router
├── notebooks/                         # Reactive notebooks (Roadmap Specification / Track 7)
│   ├── btc_analysis.py                # Bitcoin UTXO notebook (Roadmap Specification / Track 7.2)
│   └── usdc_analysis.py               # USDC volume notebook (Roadmap Specification / Track 7.3)
├── docs/                              # Compiled WASM static apps (Roadmap Specification / Track 7.5)
└── tests/                             # Pytest test suites (100% pass required)
```

---

## 7. Automated Review Agent Protocol: Evals, Benchmarks & Cybersecurity Suites

Automated AI review bots (e.g., Greptile, CodeRabbit, GitHub Copilot) evaluate PR diffs using production web/API security mental models (OWASP, prompt injection prevention, strict fail-closed validation). When reviewing evaluation harnesses, model benchmark runners, LLM-as-a-judge pipelines, and security test suites, review agents frequently suffer from context blindness because test inputs and golden corpora are intentionally adversarial, malformed, or boundary-testing.

### The 4 Review Agent Pitfalls in Evals & Security
1. **Adversarial Input False Positives**: Reviewers flag jailbreak strings, scoring override tokens, or prompt delimiters in golden test fixtures as active application vulnerabilities.
2. **The Sanitization Catch-22 Loop**: Reviewers demand candidate outputs pass through strict input sanitizers, but when candidate text is pre-neutralized or escaped, they reverse polarity and flag that sanitization prevents the strict application sanitizer from rejecting the input with an exception.
3. **Resilience vs. Process Crashing**: Reviewers perceive catching `SanitizationError` or runtime exceptions to record an explicit fallback rubric (`is_fallback = True`, `winner = "tie"`) as "swallowing security errors", coercing agents into crashing benchmark runners on adversarial samples.
4. **Semantic Domain Keyword Collisions**: Reviewers mistake standard evaluation variables (`score`, `verdict`, `force`, `winner`, `rate`, `maximum`) for prompt injection attacks.

### Mandatory Operational Guardrails & Circuit Breaker Hard Gate
* **Review Circuit Breaker Hard Gate (10 Reviews / Early Oscillation)**:
  - If an automated review loop reaches **10 reviews**, OR exhibits Catch-22 oscillation / pedantic spirals across 2-3 iterations, immediately **trip the circuit breaker**:
    1. Cease code generation and refactoring churn.
    2. Run diagnostic thread checks via `review-agent-circuit-breaker`.
    3. Update repository reviewer configuration (`.greptile/rules.md`, `.greptile/config.json`) to enforce boundary rules in prose.
    4. If the reviewer's score remains depressed despite 0 open comments and 100% test pass rates, halt and alert the human developer rather than generating speculative code churn.

---

## 8. Version-Free Rules Doctrine

* **Single Source of Truth:** Constraint-bearing dependency versions (floors, ceilings, exact pins) MUST be stated exactly once, in the manifests (`pyproject.toml` for this repository). The advisory source of truth is the vendor's own declared dependency metadata (`importlib.metadata` on installed distributions, the PyPI registry JSON).
* **Series-Only Prose:** Rulebooks (`AGENTS.md`, `.greptile/rules.md`, `specs/foundation-spec/**`, `README.md` claims) and review directives MUST reference version *series* only (e.g. "Pydantic v2", "Python 3.x"). Quoting package floors/ceilings in prose is prohibited — they age into falsehood. Precedent (dated drift evidence, 2026-11-10 audit): two disguised floors in living spec prose (`Python 3.11+` in the design.md Target Platform; `uAgents 0.26+` in its §6.2 heading) duplicated `pyproject.toml` constraints, and the uAgents prose floor had already drifted looser than the manifest floor (`0.26+` vs `>=0.26.1`). Model identifiers (e.g. `gemini-3.8-flash`) are product identity, not dependency constraints.
* **Exceptions:** Immutable archives (e.g. a future `docs/archive/**`) and dated release notes may quote era-specific versions. Within living rulebooks, historical numbers may appear ONLY when explicitly labeled as dated drift evidence.
* **PR Discipline:** A diff that changes a manifest constraint MUST NOT also edit rule-prose version numbers (and vice versa); dependency PRs MUST verify resolvability (`pip install --dry-run` of the affected packages against the manifest) before commit.
* **Verify Gate:** Governance PRs touching rule prose MUST pass the version-free-rules verifier before push: `bash .agents/skills/version-free-rules-auditor/scripts/vf_verify.sh <repo-root> --base <default-branch-tip> --allow .greptile/vf-allow.txt`. The verifier is vendored in-repo (requires `git` and `rg`); the allowlist exempts exactly one labeled dated-drift-evidence key (`./AGENTS.md:212` — the precedent clause above); re-key it in the same PR if any edit shifts that line. The verifier's own test suite (`tests/test_vf_scripts.py`) is governance tooling and is the sole `tests/` path exempt from the docs-only diff policy.
