"""Unit tests for BigQuery ETL pipelines: cost ceilings, chunk windows, and sanitization."""

import calendar
import runpy
import sys
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from src.bigquery.etl_pipelines import (
    run_etl_pipeline,
    run_monthly_incremental_etl,
    validate_date,
    validate_identifier,
)


@pytest.fixture
def mock_bq_client() -> Iterator[MagicMock]:
    with patch("src.bigquery.etl_pipelines.bigquery.Client") as mock_cls:
        mock_client = mock_cls.return_value
        mock_job = MagicMock()
        mock_job.job_id = "test-job-123"
        mock_job.total_bytes_processed = 10 * 1024**3
        mock_client.query.return_value = mock_job
        yield mock_client


class TestEtlInputValidation:
    @pytest.mark.parametrize("identifier", ["my-project", "crypto_analytics_mart", "proj.dataset_1"])
    def test_valid_identifiers_pass(self, identifier: str) -> None:
        assert validate_identifier(identifier, "project_id") == identifier

    @pytest.mark.parametrize("payload", ["proj; DROP TABLE x", "a b", "", "proj`", None, 42])
    def test_invalid_identifiers_raise(self, payload: object) -> None:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            validate_identifier(payload, "project_id")

    def test_valid_date_passes(self) -> None:
        assert validate_date("2024-02-29") == "2024-02-29"

    @pytest.mark.parametrize("payload", ["2024-2-29", "DROP TABLE;--", "", None])
    def test_invalid_dates_raise(self, payload: object) -> None:
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date(payload)


class TestBaselineEtlPipeline:
    def test_unsafe_project_rejected_before_client_creation(self) -> None:
        with patch("src.bigquery.etl_pipelines.bigquery.Client") as mock_cls:
            with pytest.raises(ValueError, match="Invalid SQL identifier"):
                run_etl_pipeline("bad;project", dry_run=True)
            mock_cls.assert_not_called()

    def test_missing_dataset_created_in_us(self, mock_bq_client: MagicMock) -> None:
        mock_bq_client.get_dataset.side_effect = RuntimeError("404 not found")
        run_etl_pipeline("test-project", start_date="2024-01-01", end_date="2024-12-31", dry_run=True)
        mock_bq_client.create_dataset.assert_called_once()
        dataset = mock_bq_client.create_dataset.call_args.args[0]
        assert dataset.location == "US"
        assert mock_bq_client.create_dataset.call_args.kwargs["exists_ok"] is True

    def test_existing_dataset_not_recreated(self, mock_bq_client: MagicMock) -> None:
        run_etl_pipeline("test-project", start_date="2024-01-01", end_date="2024-12-31", dry_run=True)
        mock_bq_client.get_dataset.assert_called_once()
        mock_bq_client.create_dataset.assert_not_called()

    def test_single_year_dry_run_skips_ddl_and_byte_ceiling(self, mock_bq_client: MagicMock) -> None:
        run_etl_pipeline("test-project", start_date="2024-01-01", end_date="2024-12-31", dry_run=True)
        calls = mock_bq_client.query.call_args_list
        assert len(calls) == 2
        for call in calls:
            config = call.kwargs["job_config"]
            assert config.dry_run is True
            assert config.maximum_bytes_billed is None

    def test_multi_year_chunking_enforces_ceilings(self, mock_bq_client: MagicMock) -> None:
        run_etl_pipeline("test-project", start_date="2024-06-01", end_date="2025-03-31")
        calls = mock_bq_client.query.call_args_list
        # 2 schema DDL statements + 2 years x 2 MERGE jobs
        assert len(calls) == 6
        merge_sqls = [call.args[0] for call in calls[2:]]
        assert "2024-06-01" in merge_sqls[0] and "2024-12-31" in merge_sqls[0]
        assert "2025-01-01" in merge_sqls[2] and "2025-03-31" in merge_sqls[2]
        btc_config = calls[2].kwargs["job_config"]
        usdc_config = calls[3].kwargs["job_config"]
        assert btc_config.dry_run is False
        assert btc_config.maximum_bytes_billed == 2_500_000_000_000
        assert usdc_config.maximum_bytes_billed == 500_000_000_000

    def test_unchunked_baseline_uses_full_window(self, mock_bq_client: MagicMock) -> None:
        run_etl_pipeline(
            "test-project", start_date="2024-01-01", end_date="2025-12-31", chunk_by_year=False
        )
        calls = mock_bq_client.query.call_args_list
        assert len(calls) == 4
        assert "2024-01-01" in calls[2].args[0]
        assert "2025-12-31" in calls[2].args[0]

    def test_inverted_annual_window_is_skipped(self, mock_bq_client: MagicMock) -> None:
        # validate_date checks shape only; a month-13 start inverts the first annual window
        run_etl_pipeline("test-project", start_date="2024-13-01", end_date="2025-01-31", dry_run=True)
        calls = mock_bq_client.query.call_args_list
        assert len(calls) == 2
        assert "2025-01-01" in calls[0].args[0]
        assert "2025-01-31" in calls[0].args[0]

    def test_main_entrypoint_dry_runs_full_backfill(self, monkeypatch: pytest.MonkeyPatch, mock_bq_client: MagicMock) -> None:
        monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
        monkeypatch.delitem(sys.modules, "src.bigquery.etl_pipelines")
        runpy.run_module("src.bigquery.etl_pipelines", run_name="__main__")
        calls = mock_bq_client.query.call_args_list
        # 2014-2026 inclusive = 13 annual chunks x 2 MERGE jobs, no DDL in dry-run
        assert len(calls) == 26
        for call in calls:
            assert call.kwargs["job_config"].dry_run is True


class TestMonthlyIncrementalEtl:
    @pytest.mark.parametrize(
        "year,month,last_day",
        [(2024, 2, 29), (2025, 2, 28), (2026, 12, 31)],
    )
    def test_month_window_and_ceilings(self, mock_bq_client: MagicMock, year: int, month: int, last_day: int) -> None:
        run_monthly_incremental_etl("test-project", target_year=year, target_month=month)
        calls = mock_bq_client.query.call_args_list
        assert len(calls) == 2
        for call in calls:
            sql = call.args[0]
            assert f"{year:04d}-{month:02d}-01" in sql
            assert f"{year:04d}-{month:02d}-{last_day:02d}" in sql
        assert calls[0].kwargs["job_config"].maximum_bytes_billed == 2_500_000_000_000
        assert calls[1].kwargs["job_config"].maximum_bytes_billed == 50_000_000_000

    def test_dry_run_disables_byte_ceiling(self, mock_bq_client: MagicMock) -> None:
        run_monthly_incremental_etl("test-project", target_year=2026, target_month=1, dry_run=True)
        for call in mock_bq_client.query.call_args_list:
            config = call.kwargs["job_config"]
            assert config.dry_run is True
            assert config.maximum_bytes_billed is None

    def test_invalid_month_raises_before_submission(self, mock_bq_client: MagicMock) -> None:
        with pytest.raises(calendar.IllegalMonthError):
            run_monthly_incremental_etl("test-project", target_year=2026, target_month=13)
        mock_bq_client.query.assert_not_called()

    def test_unsafe_dataset_rejected_before_submission(self, mock_bq_client: MagicMock) -> None:
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            run_monthly_incremental_etl("test-project", dataset_id="mart; DROP TABLE x")
        mock_bq_client.query.assert_not_called()