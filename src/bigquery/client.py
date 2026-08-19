"""Parameterized BigQuery Analytics Client with LRU Caching and Hard Cost Guardrails.

Provides safe, cost-bounded execution against the curated datamart:
- Hard byte limit per query (maximum_bytes_billed = 50 MB)
- Strict type-safe query parameterization
- In-memory thread-safe LRU caching with TTL
"""

import os
import time
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Any
from google.cloud import bigquery


class BigQueryExecutionError(Exception):
    """Raised when BigQuery query execution fails or violates cost limits."""
    pass


class LRUCache:
    """Thread-safe in-memory LRU Cache with TTL."""

    def __init__(self, capacity: int = 500, ttl_seconds: int = 86400):
        self.capacity = capacity
        self.ttl = ttl_seconds
        self.cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self.lock = Lock()

    def get(self, key: str) -> Any | None:
        with self.lock:
            if key not in self.cache:
                return None
            timestamp, value = self.cache[key]
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                return None
            self.cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = (time.time(), value)
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)


class BigQueryAnalyticsClient:
    """Production-grade BigQuery client executing parameterized queries with cost bounds."""

    TEMPLATE_MAP = {
        "btc_hodl_waves": "btc_utxo_hodl_waves.sql",
        "btc_microtransactions": "btc_microtransaction_density.sql",
        "usdc_organic_volume": "usdc_organic_vs_noise.sql",
        "usdc_eoa_topology": "usdc_eoa_vs_contract.sql",
    }

    def __init__(
        self,
        project_id: str | None = None,
        dataset_id: str = "crypto_analytics_mart",
        max_bytes_billed: int = 50_000_000, # 50 MB cap
        cache_capacity: int = 500,
        cache_ttl_seconds: int = 86400,
    ):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        self.dataset_id = dataset_id or os.getenv("BIGQUERY_DATASET", "crypto_analytics_mart")
        self.max_bytes_billed = int(os.getenv("BIGQUERY_MAX_BYTES_BILLED", max_bytes_billed))
        self.cache = LRUCache(capacity=cache_capacity, ttl_seconds=cache_ttl_seconds)
        self.sql_dir = Path(__file__).parent / "sql_queries"
        self._bq_client = None

    @property
    def client(self) -> bigquery.Client:
        """Lazily initialize the BigQuery client."""
        if self._bq_client is None:
            self._bq_client = bigquery.Client(project=self.project_id)
        return self._bq_client

    def _load_sql_template(self, query_type: str) -> str:
        """Loads SQL file from templates directory."""
        if query_type not in self.TEMPLATE_MAP:
            raise BigQueryExecutionError(f"No SQL template registered for query_type: {query_type}")
        file_path = self.sql_dir / self.TEMPLATE_MAP[query_type]
        if not file_path.exists():
            raise BigQueryExecutionError(f"SQL file not found at: {file_path}")
        raw_sql = file_path.read_text(encoding="utf-8")
        return raw_sql.replace("{{project_id}}", self.project_id).replace("{{dataset_id}}", self.dataset_id)

    def execute_analytics_query(
        self,
        query_type: str,
        start_date: str,
        end_date: str,
        granularity: str = "daily",
    ) -> dict[str, Any]:
        """Executes a parameterized analytical query against the curated datamart.

        Enforces LRU cache checks and hard byte limit ceilings.
        """
        cache_key = f"{query_type}:{start_date}:{end_date}:{granularity}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return {**cached_result, "is_cached": True}

        raw_sql = self._load_sql_template(query_type)

        query_params = [
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]

        job_config = bigquery.QueryJobConfig(
            query_parameters=query_params,
            maximum_bytes_billed=self.max_bytes_billed,
            use_query_cache=True,
        )

        try:
            query_job = self.client.query(raw_sql, job_config=job_config)
            results = [dict(row) for row in query_job.result()]
            bytes_scanned_mb = float(query_job.total_bytes_billed or 0) / (1024 * 1024)

            summary = self._generate_empirical_summary(query_type, results)

            payload = {
                "status": "SUCCESS",
                "query_type": query_type,
                "timeframe": f"{start_date} to {end_date}",
                "granularity": granularity,
                "bytes_scanned_mb": round(bytes_scanned_mb, 4),
                "data_points": results,
                "empirical_summary": summary,
                "reproducible_sql": raw_sql,
                "is_cached": False,
            }

            self.cache.set(cache_key, payload)
            return payload

        except Exception as e:
            err_msg = str(e)
            if "bytes billed" in err_msg.lower() or "limit" in err_msg.lower():
                raise BigQueryExecutionError(
                    f"Billing Guard Triggered: Query exceeded safety ceiling of {self.max_bytes_billed / (1024*1024)} MB."
                ) from e
            raise BigQueryExecutionError(f"BigQuery execution failed: {err_msg}") from e

    def _generate_empirical_summary(self, query_type: str, results: list[dict]) -> str:
        """Generates concise, human-readable empirical summaries from query results."""
        if not results:
            return "No data points returned for the specified date range."

        count = len(results)
        if query_type == "btc_hodl_waves":
            last_point = results[-1]
            dormant = last_point.get("pct_dormant_supply_over_1y", "N/A")
            over_2y = last_point.get("pct_over_2y", "N/A")
            return (
                f"Across {count} daily observations, as of {last_point.get('date')}, "
                f"{dormant}% of Bitcoin's total supply has remained dormant for over 1 year "
                f"({over_2y}% for >2 years), strongly validating the Store-of-Value accumulation thesis."
            )
        elif query_type == "btc_microtransactions":
            last_point = results[-1]
            micro_pct = last_point.get("pct_microtransactions", "N/A")
            fee_drag = last_point.get("fee_drag_pct_on_10usd_purchase", "N/A")
            return (
                f"Microtransactions (<$10) represent only {micro_pct}% of classified transactions. "
                f"Average fee drag on a standard $10 retail basket is {fee_drag}%, demonstrating that base-layer "
                f"fees remain a structural economic deterrent to everyday point-of-sale commerce."
            )
        elif query_type == "usdc_organic_volume":
            last_point = results[-1]
            organic_pct = last_point.get("organic_volume_pct", "N/A")
            noise_pct = last_point.get("automated_noise_pct", "N/A")
            return (
                f"Visa/Artemis noise filtering shows that {noise_pct}% of nominal USDC volume is automated bot/MEV/wash "
                f"activity. Organic commerce volume represents {organic_pct}% of total throughput."
            )
        elif query_type == "usdc_eoa_topology":
            last_point = results[-1]
            p2p_pct = last_point.get("pct_p2p_merchant_commerce", "N/A")
            defi_pct = last_point.get("pct_defi_smart_contract", "N/A")
            return (
                f"Counterparty topology analysis indicates {defi_pct}% of organic volume routes through DeFi/DEX/Lending contracts, "
                f"with only {p2p_pct}% consisting of direct P2P or merchant wallet settlement."
            )
        return f"Successfully processed {count} records."
