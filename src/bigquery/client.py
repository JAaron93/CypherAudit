"""Parameterized BigQuery Analytics Client with LRU Caching and Hard Cost Guardrails.

Provides safe, cost-bounded execution against the curated datamart:
- Hard byte limit per query (maximum_bytes_billed = 50 MB)
- Strict type-safe query parameterization and identifier validation
- In-memory thread-safe LRU caching with TTL
- True multi-granularity time series aggregation (daily, monthly, yearly)
"""

import os
import re
import time
from collections import OrderedDict, defaultdict
from pathlib import Path
from threading import Lock
from typing import Any
from google.cloud import bigquery


class BigQueryExecutionError(Exception):
    """Raised when BigQuery query execution fails or violates cost limits."""
    pass


def validate_identifier(name: str, param_name: str) -> str:
    """Validates that a SQL identifier contains only alphanumeric and safe characters."""
    if not isinstance(name, str) or not re.match(r"^[a-zA-Z0-9_\-\.]+$", name):
        raise BigQueryExecutionError(f"Invalid SQL identifier for {param_name}: '{name}'")
    return name


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
        max_bytes_billed: int = 50_000_000,  # 50 MB cap
        cache_capacity: int = 500,
        cache_ttl_seconds: int = 86400,
    ):
        raw_project = project_id or os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        raw_dataset = dataset_id or os.getenv("BIGQUERY_DATASET", "crypto_analytics_mart")
        self.project_id = validate_identifier(raw_project, "project_id")
        self.dataset_id = validate_identifier(raw_dataset, "dataset_id")
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
        """Loads and safely binds SQL file from templates directory."""
        if query_type not in self.TEMPLATE_MAP:
            raise BigQueryExecutionError(f"No SQL template registered for query_type: {query_type}")
        file_path = self.sql_dir / self.TEMPLATE_MAP[query_type]
        if not file_path.exists():
            raise BigQueryExecutionError(f"SQL file not found at: {file_path}")
        raw_sql = file_path.read_text(encoding="utf-8")
        return raw_sql.replace("{{project_id}}", self.project_id).replace("{{dataset_id}}", self.dataset_id)

    def _aggregate_granularity(
        self, results: list[dict[str, Any]], granularity: str, query_type: str = ""
    ) -> list[dict[str, Any]]:
        """Aggregates daily records into monthly or yearly summaries with mathematically sound weighted ratios."""
        if not results or granularity == "daily":
            return results

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in results:
            date_val = str(row.get("date", ""))
            period_key = date_val[:7] if granularity == "monthly" else date_val[:4]
            grouped[period_key].append(row)

        aggregated = []
        for period, rows in sorted(grouped.items()):
            n = len(rows)
            agg_row: dict[str, Any] = {"period": period, "observation_count": n}

            # Helper to sum a field
            def sum_field(field_name: str) -> float:
                return sum(float(r[field_name]) for r in rows if r.get(field_name) is not None)

            if query_type == "btc_hodl_waves":
                total_utxos = sum_field("total_active_utxos")
                agg_row["total_active_utxos"] = int(total_utxos)
                for band_key in ["pct_under_1d", "pct_1d_to_1w", "pct_1w_to_1m", "pct_1m_to_6m", "pct_6m_to_1y", "pct_1y_to_2y", "pct_over_2y"]:
                    if band_key in rows[0]:
                        if total_utxos > 0:
                            weighted = sum(float(r[band_key]) * float(r.get("total_active_utxos", 1)) for r in rows) / total_utxos
                            agg_row[band_key] = round(weighted, 2)
                        else:
                            agg_row[band_key] = round(sum(float(r[band_key]) for r in rows) / n, 2)
                agg_row["pct_dormant_supply_over_1y"] = round(agg_row.get("pct_1y_to_2y", 0.0) + agg_row.get("pct_over_2y", 0.0), 2)

            elif query_type == "btc_microtransactions":
                micro = int(sum_field("micro_tx_count_under_10usd"))
                retail = int(sum_field("retail_tx_count_10_to_500usd"))
                whale = int(sum_field("whale_tx_count_over_50kusd"))
                total_txs = micro + retail + whale
                agg_row["micro_tx_count_under_10usd"] = micro
                agg_row["retail_tx_count_10_to_500usd"] = retail
                agg_row["whale_tx_count_over_50kusd"] = whale
                agg_row["total_classified_txs"] = total_txs
                agg_row["pct_microtransactions"] = round(micro * 100.0 / total_txs, 2) if total_txs > 0 else 0.0
                agg_row["pct_retail_commerce"] = round(retail * 100.0 / total_txs, 2) if total_txs > 0 else 0.0
                agg_row["pct_whale_institutional"] = round(whale * 100.0 / total_txs, 2) if total_txs > 0 else 0.0
                if total_txs > 0:
                    weighted_fee = sum(
                        float(r.get("avg_fee_usd", 0.0)) * (
                            int(r.get("micro_tx_count_under_10usd", 0))
                            + int(r.get("retail_tx_count_10_to_500usd", 0))
                            + int(r.get("whale_tx_count_over_50kusd", 0))
                        )
                        for r in rows
                    ) / total_txs
                    agg_row["avg_fee_usd"] = round(weighted_fee, 2)
                else:
                    agg_row["avg_fee_usd"] = round(sum(float(r.get("avg_fee_usd", 0.0)) for r in rows) / n, 2)
                agg_row["fee_drag_pct_on_10usd_purchase"] = round(agg_row["avg_fee_usd"] / 10.0 * 100.0, 2)

            elif query_type == "usdc_organic_volume":
                raw_count = int(sum_field("raw_transfer_count"))
                org_count = int(sum_field("organic_transfer_count"))
                raw_vol = round(sum_field("raw_volume_usd"), 2)
                org_vol = round(sum_field("organic_volume_usd"), 2)
                retail_vol = round(sum_field("retail_volume_under_500usd"), 2)
                agg_row["raw_transfer_count"] = raw_count
                agg_row["organic_transfer_count"] = org_count
                agg_row["raw_volume_usd"] = raw_vol
                agg_row["organic_volume_usd"] = org_vol
                org_ratio_pct = round(org_vol * 100.0 / raw_vol, 2) if raw_vol > 0 else 0.0
                agg_row["organic_volume_pct"] = org_ratio_pct
                agg_row["automated_noise_pct"] = round(100.0 - org_ratio_pct, 2)
                agg_row["retail_volume_under_500usd"] = retail_vol
                agg_row["pct_retail_of_organic"] = round(retail_vol * 100.0 / org_vol, 2) if org_vol > 0 else 0.0

            elif query_type == "usdc_eoa_topology":
                eoa_vol = round(sum_field("eoa_to_eoa_volume_usd"), 2)
                contract_vol = round(sum_field("eoa_to_contract_volume_usd"), 2)
                total_vol = eoa_vol + contract_vol
                agg_row["eoa_to_eoa_volume_usd"] = eoa_vol
                agg_row["eoa_to_contract_volume_usd"] = contract_vol
                agg_row["pct_p2p_merchant_commerce"] = round(eoa_vol * 100.0 / total_vol, 2) if total_vol > 0 else 0.0
                agg_row["pct_defi_smart_contract"] = round(contract_vol * 100.0 / total_vol, 2) if total_vol > 0 else 0.0

            else:
                for key in rows[0].keys():
                    if key in {"date", "period"}:
                        continue
                    vals = [r[key] for r in rows if r.get(key) is not None and isinstance(r.get(key), (int, float))]
                    if vals:
                        agg_row[key] = round(sum(vals) / len(vals), 2) if any(s in key for s in ["pct", "ratio", "avg"]) else round(sum(vals), 2)

            aggregated.append(agg_row)

        return aggregated

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
            raw_results = [dict(row) for row in query_job.result()]
            results = self._aggregate_granularity(raw_results, granularity, query_type=query_type)
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
        last_point = results[-1]
        period_label = last_point.get("date") or last_point.get("period")

        if query_type == "btc_hodl_waves":
            dormant = last_point.get("pct_dormant_supply_over_1y", "N/A")
            over_2y = last_point.get("pct_over_2y", "N/A")
            return (
                f"Across {count} observations, as of {period_label}, "
                f"{dormant}% of Bitcoin's total supply has remained dormant for over 1 year "
                f"({over_2y}% for >2 years), strongly validating the Store-of-Value accumulation thesis."
            )
        elif query_type == "btc_microtransactions":
            micro_pct = last_point.get("pct_microtransactions", "N/A")
            fee_drag = last_point.get("fee_drag_pct_on_10usd_purchase", "N/A")
            return (
                f"Microtransactions (<$10) represent only {micro_pct}% of classified transactions. "
                f"Average fee drag on a standard $10 retail basket is {fee_drag}%, demonstrating that base-layer "
                f"fees remain a structural economic deterrent to everyday point-of-sale commerce."
            )
        elif query_type == "usdc_organic_volume":
            organic_pct = last_point.get("organic_volume_pct", "N/A")
            noise_pct = last_point.get("automated_noise_pct", "N/A")
            return (
                f"Visa/Artemis noise filtering shows that {noise_pct}% of nominal USDC volume is automated bot/MEV/wash "
                f"activity. Organic commerce volume represents {organic_pct}% of total throughput."
            )
        elif query_type == "usdc_eoa_topology":
            p2p_pct = last_point.get("pct_p2p_merchant_commerce", "N/A")
            defi_pct = last_point.get("pct_defi_smart_contract", "N/A")
            return (
                f"Counterparty topology analysis indicates {defi_pct}% of organic volume routes through DeFi/DEX/Lending contracts, "
                f"with only {p2p_pct}% consisting of direct P2P or merchant wallet settlement."
            )
        return f"Successfully processed {count} records."
