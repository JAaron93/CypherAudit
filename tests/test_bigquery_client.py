"""Unit tests for Parameterized BigQuery Client & Guardrails in SignalChain Oracle."""

from unittest.mock import MagicMock, patch
import pytest
from src.bigquery.client import BigQueryAnalyticsClient, BigQueryExecutionError


class TestBigQueryAnalyticsClient:
    """Verifies parameterized execution, byte limits, and in-memory LRU caching."""

    def test_client_enforces_maximum_bytes_billed(self):
        with patch("google.cloud.bigquery.Client") as mock_bq:
            mock_instance = MagicMock()
            mock_bq.return_value = mock_instance

            client = BigQueryAnalyticsClient(
                project_id="test-project",
                dataset_id="crypto_analytics_mart",
                max_bytes_billed=50_000_000,
            )

            assert client.max_bytes_billed == 50_000_000

    def test_lru_cache_avoids_duplicate_query_execution(self):
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

    def test_byte_limit_exceeded_handled_gracefully(self):
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
