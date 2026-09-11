# Greptile Code Review Guidelines for CypherAudit / SignalChain Oracle

## 1. Architectural & Safety Principles
- **Cost Guardrails & BigQuery Safety:** Every BigQuery query job configuration MUST enforce `maximum_bytes_billed` (default 50 MB ceiling). Full unpartitioned table scans against raw public blockchain datasets without byte ceilings must be flagged as critical severity.
- **Zero Dynamic SQL / Injection Defense:** SQL queries must strictly use parameterized queries (`google.cloud.bigquery.ScalarQueryParameter`). Never permit dynamic f-string formatting or string concatenation in SQL execution paths.
- **Defense-in-Depth Security:** All incoming user inputs (dates, query types, granularities) must pass through `SecurityCircuitBreaker` and `TokenBucketRateLimiter` before initiating cloud I/O.
- **Cryptographic Identity Isolation:** Never provide public fallback strings for cryptographic seed variables (`AGENT_SEED`). Missing seeds must raise an explicit exception to prevent identity collision and address impersonation.

## 2. Code Quality & Typing Standards
- **Strict Typing:** All Python functions, methods, event handlers (`ctx: Context`), and test cases (`-> None`) must include explicit parameter and return type hints.
- **Pydantic v2 Models:** Protocol message models must inherit from `pydantic.BaseModel` with explicit field definitions and descriptions.
- **Async Non-Blocking Execution:** Agent protocols and message handlers must use `async`/`await` non-blocking patterns.

## 3. Test-Driven Development (TDD)
- Any new feature or bug fix must be covered by unit tests in `tests/`.
- Ensure mock fixtures are used for cloud APIs (BigQuery, Gemini) in unit test suites to maintain deterministic execution.

## 4. Antigravity 2.0 CLI-First Architecture & Tool Routing Guardrails

> [!NOTE]
> **Developer Tooling Scope vs. Runtime Application Architecture**:
> This CLI-first doctrine governs **Software Engineering Agents (SEAs), coding assistants, and developer workflows** (version control, PR management, testing, builds, containers, and environment inspection). The **runtime application itself** runs purely through its native platform SDKs/in-process architecture (e.g., `google.cloud.bigquery`, `google-genai`, `uagents`, `pydantic`); agents and review bots must **never** conflate developer tool routing with runtime application architecture or demand that runtime services shell out to CLI binaries.

- **Scope Demarcation:** Review agents must never flag runtime Python SDK calls (`google.cloud.bigquery`, `google.genai`, `uagents`) as violating CLI-first principles. Developer and orchestration workflows use CLI binaries; runtime services run in-process.
- **MCP Scope & Stateful Boundaries:** Reserve MCP exclusively for persistent stateful daemons, database connections, AST memory graphs, and the designated Reserved Tier (`codebase-memory-mcp`, `context7`, `chrome-devtools`, `greptile`). Reject stateless MCP servers (e.g. GitHub, Git, Slack, Jira) in favor of native CLI tools (`gh`, `git`, `gcloud`, `aws`, `docker`).
- **Architectural Perpetuation Invariant:** Review agents must verify that new tool integrations, agent definitions, or scaffolded workflows adhere to CLI binaries paired with lightweight skills rather than introducing stateless MCP daemons.

## 5. Universal Version Control, Token Hygiene & PR Boundaries
- **Feature Branches Only:** All modifications must occur on isolated feature branches. Flag any attempt to commit or push directly to `main` or `master`.
- **Zero Autonomous Merging:** Flag any automated or scripted invocation of `gh pr merge` or API-based pull request merging. Human review and approval are mandatory.
- **Pre-Commit Hygiene:** Flag commits staging `.env` files, API keys, credentials, or `.sqlite` WAL files.
- **CLI Output Hygiene & Token Conservation:** Ensure terminal commands and diagnostic scripts enforce bounded output:
  - `gh`: Use `--json <field1,field2>` and `--limit <N>` on list/query subcommands.
  - `gcloud`: Use `--format="value(field)"` or `--format="table(field1,field2)"` on list/describe queries.
  - `docker`: Use `--format "{{.ID}}: {{.Names}} ({{.Status}})"` on `ps`, `images`, or `inspect`.
  - Non-query subcommands must pipe through Unix stream filters (`jq`, `head -n <N>`, `grep`).

## 6. Automated Review Agent Protocol & Domain Invariants
- **Domain Invariants for Evals & Security Fixtures:** When reviewing test fixtures, evaluation datasets, or security probes:
  - Do not flag adversarial strings, jailbreaks, or prompt delimiters in golden test cases as active application vulnerabilities.
  - Do not demand that candidate inputs pass through application sanitizers when the test harness deliberately probes invalid or boundary-breaking inputs.
  - Recognize graceful exception mapping (`is_fallback = True`, `winner = "tie"`) as legitimate resilience, not "swallowing security errors".
- **Review Circuit Breaker Hard Gate (10 Reviews / Early Oscillation):** If a review loop reaches 10 iterations or exhibits Catch-22 oscillation, the circuit breaker must be tripped immediately to halt speculative code churn and update review configuration.

