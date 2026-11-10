"""Unit tests for Parameterized BigQuery Client & Guardrails in SignalChain Oracle."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from src.bigquery.client import BigQueryAnalyticsClient, BigQueryExecutionError, LRUCache, validate_identifier


class TestBigQueryAnalyticsClient:
    """Verifies parameterized execution, byte limits, identifier checks, and in-memory LRU caching."""

    def test_client_enforces_maximum_bytes_billed(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance

            client = BigQueryAnalyticsClient(
                project_id="test-project",
                dataset_id="crypto_analytics_mart",
                max_bytes_billed=50_000_000,
            )

            assert client.max_bytes_billed == 50_000_000

    def test_invalid_sql_identifiers_rejected(self) -> None:
        with pytest.raises(BigQueryExecutionError, match="Invalid SQL identifier"):
            validate_identifier("bad-project; DROP TABLE users;--", "project_id")

        with pytest.raises(BigQueryExecutionError, match="Invalid SQL identifier"):
            BigQueryAnalyticsClient(project_id="test`project")

    def test_lru_cache_avoids_duplicate_query_execution(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance

            # Mock query job result
            mock_query_job = MagicMock()
            mock_row = {"date": "2025-01-01", "pct_dormant_supply_over_1y": 68.5}
            mock_query_job.result.return_value = [mock_row]
            mock_query_job.total_bytes_billed = 1048576  # 1 MB
            mock_instance.query.return_value = mock_query_job

            client = BigQueryAnalyticsClient(project_id="test-project")

            # First query - Cache Miss (calls BigQuery)
            res1 = client.execute_analytics_query(
                query_type="btc_hodl_waves", start_date="2025-01-01", end_date="2025-12-31"
            )
            assert res1["status"] == "SUCCESS"
            assert res1["is_cached"] is False
            assert mock_instance.query.call_count == 1

            # Second identical query - Cache Hit (zero BigQuery API calls)
            res2 = client.execute_analytics_query(
                query_type="btc_hodl_waves", start_date="2025-01-01", end_date="2025-12-31"
            )
            assert res2["status"] == "SUCCESS"
            assert res2["is_cached"] is True
            assert mock_instance.query.call_count == 1  # Still 1!

    def test_granularity_aggregation_monthly(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance

            mock_rows = [
                {"date": "2025-01-01", "raw_volume_usd": 1000.0, "organic_volume_usd": 300.0, "raw_transfer_count": 10, "organic_transfer_count": 8},
                {"date": "2025-01-15", "raw_volume_usd": 2000.0, "organic_volume_usd": 800.0, "raw_transfer_count": 20, "organic_transfer_count": 15},
                {"date": "2025-02-01", "raw_volume_usd": 5000.0, "organic_volume_usd": 1250.0, "raw_transfer_count": 50, "organic_transfer_count": 30},
            ]
            mock_query_job = MagicMock()
            mock_query_job.result.return_value = mock_rows
            mock_query_job.total_bytes_billed = 2097152
            mock_instance.query.return_value = mock_query_job

            client = BigQueryAnalyticsClient(project_id="test-project")
            res = client.execute_analytics_query(
                query_type="usdc_organic_volume",
                start_date="2025-01-01",
                end_date="2025-02-28",
                granularity="monthly",
            )

            assert res["status"] == "SUCCESS"
            assert len(res["data_points"]) == 2
            assert res["data_points"][0]["period"] == "2025-01"
            assert res["data_points"][0]["raw_volume_usd"] == 3000.0
            assert res["data_points"][0]["organic_volume_usd"] == 1100.0
            assert res["data_points"][0]["organic_volume_pct"] == 36.67  # (1100/3000)*100
            assert res["data_points"][0]["automated_noise_pct"] == 63.33
            assert res["data_points"][1]["period"] == "2025-02"
            assert res["data_points"][1]["organic_volume_pct"] == 25.0

    def test_granularity_aggregation_btc_hodl_waves_supply_weighted(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance

            # Day 1: 10,000 UTXOs with 100 BTC supply, 10% under 1d (10 BTC)
            # Day 2: 1,000 UTXOs with 900 BTC supply, 50% under 1d (450 BTC)
            # Total Supply = 1000 BTC. Weighted % under 1d = (100*10 + 900*50) / 1000 = 46.0%
            mock_rows = [
                {
                    "date": "2025-01-01",
                    "total_active_utxos": 10000,
                    "total_active_btc_supply": 100.0,
                    "pct_under_1d": 10.0,
                    "pct_1d_to_1w": 20.0,
                    "pct_1w_to_1m": 20.0,
                    "pct_1m_to_6m": 20.0,
                    "pct_6m_to_1y": 10.0,
                    "pct_1y_to_2y": 10.0,
                    "pct_over_2y": 10.0,
                },
                {
                    "date": "2025-01-15",
                    "total_active_utxos": 1000,
                    "total_active_btc_supply": 900.0,
                    "pct_under_1d": 50.0,
                    "pct_1d_to_1w": 10.0,
                    "pct_1w_to_1m": 10.0,
                    "pct_1m_to_6m": 10.0,
                    "pct_6m_to_1y": 10.0,
                    "pct_1y_to_2y": 5.0,
                    "pct_over_2y": 5.0,
                },
            ]
            mock_query_job = MagicMock()
            mock_query_job.result.return_value = mock_rows
            mock_query_job.total_bytes_billed = 1048576
            mock_instance.query.return_value = mock_query_job

            client = BigQueryAnalyticsClient(project_id="test-project")
            res = client.execute_analytics_query(
                query_type="btc_hodl_waves",
                start_date="2025-01-01",
                end_date="2025-01-31",
                granularity="monthly",
            )

            assert res["status"] == "SUCCESS"
            assert len(res["data_points"]) == 1
            assert res["data_points"][0]["period"] == "2025-01"
            assert res["data_points"][0]["total_active_utxos"] == 11000
            assert res["data_points"][0]["pct_under_1d"] == 46.0  # (100*10 + 900*50)/1000
            assert res["data_points"][0]["pct_dormant_supply_over_1y"] == 11.0  # (100*20 + 900*10)/1000

    def test_granularity_aggregation_btc_microtransactions_weighted_fee(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance

            # Day 1: 100 txs with $1.00 fee; Day 2: 900 txs with $5.00 fee
            # Weighted average fee = (100*1.0 + 900*5.0) / 1000 = 4.60
            mock_rows = [
                {
                    "date": "2025-01-01",
                    "micro_tx_count_under_10usd": 50,
                    "retail_tx_count_10_to_500usd": 30,
                    "whale_tx_count_over_50kusd": 20,
                    "avg_fee_usd": 1.0,
                },
                {
                    "date": "2025-01-02",
                    "micro_tx_count_under_10usd": 450,
                    "retail_tx_count_10_to_500usd": 270,
                    "whale_tx_count_over_50kusd": 180,
                    "avg_fee_usd": 5.0,
                },
            ]
            mock_query_job = MagicMock()
            mock_query_job.result.return_value = mock_rows
            mock_query_job.total_bytes_billed = 1048576
            mock_instance.query.return_value = mock_query_job

            client = BigQueryAnalyticsClient(project_id="test-project")
            res = client.execute_analytics_query(
                query_type="btc_microtransactions",
                start_date="2025-01-01",
                end_date="2025-01-31",
                granularity="monthly",
            )

            assert res["status"] == "SUCCESS"
            assert len(res["data_points"]) == 1
            assert res["data_points"][0]["period"] == "2025-01"
            assert res["data_points"][0]["total_classified_txs"] == 1000
            assert res["data_points"][0]["avg_fee_usd"] == 4.60
            assert res["data_points"][0]["fee_drag_pct_on_10usd_purchase"] == 46.0

    def test_granularity_aggregation_usdc_eoa_topology(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance

            # EOA->EOA: 400, EOA->Contract: 500, Contract->EOA: 100 => Total = 1000
            # pct_p2p = 40.0%, pct_defi = 50.0%
            mock_rows = [
                {
                    "date": "2025-01-01",
                    "eoa_to_eoa_volume_usd": 200.0,
                    "eoa_to_contract_volume_usd": 250.0,
                    "contract_to_eoa_volume_usd": 50.0,
                },
                {
                    "date": "2025-01-15",
                    "eoa_to_eoa_volume_usd": 200.0,
                    "eoa_to_contract_volume_usd": 250.0,
                    "contract_to_eoa_volume_usd": 50.0,
                },
            ]
            mock_query_job = MagicMock()
            mock_query_job.result.return_value = mock_rows
            mock_query_job.total_bytes_billed = 1048576
            mock_instance.query.return_value = mock_query_job

            client = BigQueryAnalyticsClient(project_id="test-project")
            res = client.execute_analytics_query(
                query_type="usdc_eoa_topology",
                start_date="2025-01-01",
                end_date="2025-01-31",
                granularity="monthly",
            )

            assert res["status"] == "SUCCESS"
            assert len(res["data_points"]) == 1
            assert res["data_points"][0]["period"] == "2025-01"
            assert res["data_points"][0]["eoa_to_eoa_volume_usd"] == 400.0
            assert res["data_points"][0]["eoa_to_contract_volume_usd"] == 500.0
            assert res["data_points"][0]["contract_to_eoa_volume_usd"] == 100.0
            assert res["data_points"][0]["pct_p2p_merchant_commerce"] == 40.0
            assert res["data_points"][0]["pct_defi_smart_contract"] == 50.0
            assert res["data_points"][0]["pct_contract_payout"] == 10.0

    def test_byte_limit_exceeded_handled_gracefully(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance

            # Simulate BigQuery Query Exceeded Byte Limit Error
            mock_instance.query.side_effect = Exception(
                "Query exceeded limit for bytes billed: 100000000. Limit was 50000000."
            )

            client = BigQueryAnalyticsClient(project_id="test-project")

            with pytest.raises(BigQueryExecutionError, match="Billing Guard Triggered"):
                client.execute_analytics_query(
                    query_type="usdc_organic_volume", start_date="2024-01-01", end_date="2024-12-31"
                )


class TestFreshnessProbe:
    """Verifies the read-only MAX(date) freshness probe inherits the hard byte ceiling."""

    def test_fetch_table_max_date_returns_iso_string_with_ceiling_enforced(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance

            mock_query_job = MagicMock()
            mock_query_job.result.return_value = [{"max_date": date(2026, 10, 31)}]
            mock_instance.query.return_value = mock_query_job

            client = BigQueryAnalyticsClient(
                project_id="test-project", dataset_id="crypto_analytics_mart", max_bytes_billed=50_000_000
            )
            result = client.fetch_table_max_date("btc_daily_utxo_distribution")

            assert result == "2026-10-31"
            assert mock_instance.query.call_count == 1
            sql, kwargs = mock_instance.query.call_args[0][0], mock_instance.query.call_args[1]
            assert "MAX(date) AS max_date" in sql
            assert "`test-project.crypto_analytics_mart.btc_daily_utxo_distribution`" in sql
            assert kwargs["job_config"].maximum_bytes_billed == 50_000_000

    def test_fetch_table_max_date_empty_table_returns_none(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance

            mock_query_job = MagicMock()
            mock_query_job.result.return_value = []
            mock_instance.query.return_value = mock_query_job

            client = BigQueryAnalyticsClient(project_id="test-project")

            assert client.fetch_table_max_date("usdc_daily_organic_metrics") is None

    def test_fetch_table_max_date_null_max_returns_none(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance

            mock_query_job = MagicMock()
            mock_query_job.result.return_value = [{"max_date": None}]
            mock_instance.query.return_value = mock_query_job

            client = BigQueryAnalyticsClient(project_id="test-project")

            assert client.fetch_table_max_date("usdc_daily_organic_metrics") is None

    def test_fetch_table_max_date_wraps_execution_errors(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance
            mock_instance.query.side_effect = RuntimeError("connection reset")

            client = BigQueryAnalyticsClient(project_id="test-project")

            with pytest.raises(BigQueryExecutionError, match="Freshness probe failed"):
                client.fetch_table_max_date("btc_daily_utxo_distribution")

    def test_fetch_table_max_date_rejects_invalid_table_identifier(self) -> None:
        client = BigQueryAnalyticsClient(project_id="test-project")

        with pytest.raises(BigQueryExecutionError, match="Invalid SQL identifier"):
            client.fetch_table_max_date("btc_daily_utxo_distribution; DROP TABLE users;--")


class TestLRUCacheLifecycle:
    """Verifies TTL expiry, capacity eviction, and recency refresh in the thread-safe cache."""

    def test_expired_entry_evicted_on_read(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.bigquery import client as client_module

        clock = [1000.0]
        monkeypatch.setattr(client_module.time, "time", lambda: clock[0])
        cache = LRUCache(capacity=5, ttl_seconds=60)
        cache.set("key", "value")

        clock[0] = 1061.0
        assert cache.get("key") is None
        assert "key" not in cache.cache

    def test_capacity_evicts_least_recently_used(self) -> None:
        cache = LRUCache(capacity=2, ttl_seconds=3600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_overwrite_refreshes_recency(self) -> None:
        cache = LRUCache(capacity=2, ttl_seconds=3600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("a", 9)
        cache.set("c", 3)

        assert cache.get("b") is None
        assert cache.get("a") == 9


def _execute_with_rows(query_type: str, rows: list[dict], granularity: str = "monthly") -> dict:
    with patch("google.cloud.bigquery.Client") as mock_bq:
        mock_job = MagicMock()
        mock_job.result.return_value = rows
        mock_job.total_bytes_billed = 0
        mock_bq.return_value.query.return_value = mock_job
        client = BigQueryAnalyticsClient(project_id="test-project")
        return client.execute_analytics_query(
            query_type=query_type,
            start_date="2025-01-01",
            end_date="2025-01-31",
            granularity=granularity,
        )


class TestTemplateAndExecutionErrors:
    """Verifies template resolution failures and generic error mapping."""

    def test_unregistered_query_type_rejected(self) -> None:
        client = BigQueryAnalyticsClient(project_id="test-project")
        with pytest.raises(BigQueryExecutionError, match="No SQL template registered"):
            client.execute_analytics_query("not_a_query", "2025-01-01", "2025-12-31")

    def test_missing_sql_file_rejected(self, tmp_path: Path) -> None:
        client = BigQueryAnalyticsClient(project_id="test-project")
        client.sql_dir = tmp_path
        with pytest.raises(BigQueryExecutionError, match="SQL file not found"):
            client.execute_analytics_query("btc_hodl_waves", "2025-01-01", "2025-12-31")

    def test_generic_execution_failure_wrapped(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_bq.return_value.query.side_effect = RuntimeError("connection reset")
            client = BigQueryAnalyticsClient(project_id="test-project")
            with pytest.raises(BigQueryExecutionError, match="BigQuery execution failed: connection reset"):
                client.execute_analytics_query("btc_hodl_waves", "2025-01-01", "2025-12-31")

    def test_lazy_client_initialized_once(self) -> None:
        with patch("google.cloud.bigquery.Client") as mock_bq:
            client = BigQueryAnalyticsClient(project_id="test-project")
            assert client.client is client.client
            mock_bq.assert_called_once_with(project="test-project")


class TestAggregationDegenerateInputs:
    """Verifies weighting fallbacks when base denominators are zero or absent."""

    def test_hodl_zero_supply_weights_by_utxo_count(self) -> None:
        rows = [
            {"date": "2025-01-01", "total_active_utxos": 100, "total_active_btc_supply": 0.0, "pct_under_1d": 10.0},
            {"date": "2025-01-02", "total_active_utxos": 300, "total_active_btc_supply": 0.0, "pct_under_1d": 50.0},
        ]
        point = _execute_with_rows("btc_hodl_waves", rows)["data_points"][0]
        assert point["total_active_utxos"] == 400
        assert "total_active_btc_supply" not in point
        assert point["pct_under_1d"] == 40.0  # (100*10 + 300*50) / 400

    def test_hodl_zero_supply_and_utxos_uses_simple_average(self) -> None:
        rows = [
            {"date": "2025-01-01", "total_active_utxos": 0, "total_active_btc_supply": 0.0, "pct_under_1d": 10.0},
            {"date": "2025-01-02", "total_active_utxos": 0, "total_active_btc_supply": 0.0, "pct_under_1d": 50.0},
        ]
        point = _execute_with_rows("btc_hodl_waves", rows)["data_points"][0]
        assert point["pct_under_1d"] == 30.0

    def test_micro_total_tx_count_weighting_with_zero_classified(self) -> None:
        rows = [
            {"date": "2025-01-01", "total_tx_count": 100, "avg_fee_usd": 2.0},
            {"date": "2025-01-02", "total_tx_count": 300, "avg_fee_usd": 4.0},
        ]
        point = _execute_with_rows("btc_microtransactions", rows)["data_points"][0]
        assert point["total_tx_count"] == 400
        assert point["total_classified_txs"] == 0
        assert point["pct_microtransactions"] == 0.0
        assert point["avg_fee_usd"] == 3.5  # (100*2 + 300*4) / 400

    def test_micro_zero_activity_averages_daily_fees(self) -> None:
        rows = [
            {"date": "2025-01-01", "avg_fee_usd": 2.0},
            {"date": "2025-01-02", "avg_fee_usd": 4.0},
        ]
        point = _execute_with_rows("btc_microtransactions", rows)["data_points"][0]
        assert point["avg_fee_usd"] == 3.0
        assert point["fee_drag_pct_on_10usd_purchase"] == 30.0

    def test_empty_result_set_reports_no_data(self) -> None:
        res = _execute_with_rows("btc_hodl_waves", [])
        assert res["data_points"] == []
        assert res["empirical_summary"] == "No data points returned for the specified date range."

    def test_generic_aggregation_sums_counts_and_averages_ratios(self) -> None:
        client = BigQueryAnalyticsClient(project_id="test-project")
        rows = [
            {"date": "2025-01-01", "volume_usd": 100.0, "pct_share": 10.0, "label": "a"},
            {"date": "2025-01-02", "volume_usd": 300.0, "pct_share": 30.0, "label": None},
        ]
        point = client._aggregate_granularity(rows, "monthly", query_type="future_metric")[0]
        assert point["volume_usd"] == 400.0
        assert point["pct_share"] == 20.0
        assert "label" not in point
        assert "date" not in point

    def test_unknown_query_summary_is_generic(self) -> None:
        client = BigQueryAnalyticsClient(project_id="test-project")
        summary = client._generate_empirical_summary("future_metric", [{"date": "2025-01-01"}])
        assert summary == "Successfully processed 1 records."
