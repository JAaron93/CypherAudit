# Greptile Code Review Guidelines for CypherAudit / SignalChain Oracle

## 1. Architectural & Safety Principles
- **Cost Guardrails & BigQuery Safety:** Every BigQuery query job configuration MUST enforce `maximum_bytes_billed` (default 50 MB ceiling). Full unpartitioned table scans against raw public blockchain datasets without byte ceilings must be flagged as critical severity.
- **Zero Dynamic SQL / Injection Defense:** SQL queries must strictly use parameterized queries (`google.cloud.bigquery.ScalarQueryParameter`). Never permit dynamic f-string formatting or string concatenation in SQL execution paths.
- **Defense-in-Depth Security:** All incoming user inputs (dates, query types, granularities) must pass through `SecurityCircuitBreaker` and `TokenBucketRateLimiter` before initiating cloud I/O.

## 2. Code Quality & Typing Standards
- **Strict Typing:** All Python functions, methods, and classes must include explicit type hints.
- **Pydantic v2 Models:** Protocol message models must inherit from `pydantic.BaseModel` with explicit field definitions and descriptions.
- **Async Non-Blocking Execution:** Agent protocols and message handlers must use `async`/`await` non-blocking patterns.

## 3. Test-Driven Development (TDD)
- Any new feature or bug fix must be covered by unit tests in `tests/`.
- Ensure mock fixtures are used for cloud APIs (BigQuery, Gemini) in unit test suites to maintain deterministic execution.
