"""Unit & BDD tests for Scheduled Housekeeping: Datamart Freshness Monitoring (Track 8)."""

import threading
from collections.abc import Callable
from datetime import date
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.agent.housekeeping import (
    DATAMART_TABLES,
    DIGEST_CRON,
    FRESHNESS_CRON,
    USAGE_DIGEST,
    UsageDigest,
    evaluate_freshness,
    expected_data_ceiling,
    register_housekeeping,
    run_freshness_probe,
    run_usage_digest,
)
from src.nl_parser.gemini_router import GeminiQueryRouter


class TestExpectedDataCeiling:
    """Verifies the expected ingestion ceiling: last day of the previous calendar month."""

    def test_mid_month_returns_prior_month_end(self) -> None:
        assert expected_data_ceiling(date(2026, 3, 15)) == date(2026, 2, 28)

    def test_early_january_crosses_year_boundary(self) -> None:
        assert expected_data_ceiling(date(2026, 1, 5)) == date(2025, 12, 31)

    def test_first_day_of_continuous_ingestion_horizon(self) -> None:
        assert expected_data_ceiling(date(2027, 1, 1)) == date(2026, 12, 31)


class TestFreshnessStateMachine:
    """Verifies FRESH / PENDING / STALE evaluation with the 2-day grace window."""

    def test_fresh_when_max_date_matches_expected_ceiling(self) -> None:
        report = evaluate_freshness(
            "btc_daily_utxo_distribution", date(2026, 10, 31), date(2026, 11, 5)
        )
        assert report.status == "FRESH"
        assert report.days_behind == 0
        assert report.expected_ceiling == date(2026, 10, 31)

    def test_fresh_when_data_extends_beyond_ceiling(self) -> None:
        report = evaluate_freshness(
            "usdc_daily_organic_metrics", date(2026, 11, 1), date(2026, 11, 5)
        )
        assert report.status == "FRESH"

    def test_pending_during_grace_window_when_exactly_one_month_behind(self) -> None:
        report = evaluate_freshness(
            "btc_daily_utxo_distribution", date(2026, 9, 30), date(2026, 11, 2)
        )
        assert report.status == "PENDING"
        assert report.days_behind == 31

    def test_stale_after_grace_window_when_one_month_behind(self) -> None:
        report = evaluate_freshness(
            "btc_daily_utxo_distribution", date(2026, 9, 30), date(2026, 11, 5)
        )
        assert report.status == "STALE"
        assert report.days_behind == 31

    def test_stale_immediately_during_grace_when_multiple_months_behind(self) -> None:
        report = evaluate_freshness(
            "btc_daily_utxo_distribution", date(2026, 8, 31), date(2026, 11, 2)
        )
        assert report.status == "STALE"

    def test_stale_on_third_day_of_month_when_one_month_behind(self) -> None:
        report = evaluate_freshness(
            "usdc_daily_organic_metrics", date(2026, 9, 30), date(2026, 11, 3)
        )
        assert report.status == "STALE"

    def test_stale_when_table_has_no_rows(self) -> None:
        report = evaluate_freshness("btc_daily_utxo_distribution", None, date(2026, 11, 5))
        assert report.status == "STALE"
        assert report.max_date is None


class _StubLogger:
    def __init__(self) -> None:
        self.records: list[tuple[str, str]] = []

    def info(self, msg: str, *args: object, **kwargs: object) -> None:
        self.records.append(("INFO", str(msg)))

    def warning(self, msg: str, *args: object, **kwargs: object) -> None:
        self.records.append(("WARNING", str(msg)))

    def error(self, msg: str, *args: object, **kwargs: object) -> None:
        self.records.append(("ERROR", str(msg)))


def _stub_ctx() -> SimpleNamespace:
    return SimpleNamespace(logger=_StubLogger())


class _StubBigQueryClient:
    def __init__(self, results: dict[str, str | Exception]) -> None:
        self.results = results
        self.probed_tables: list[str] = []

    def fetch_table_max_date(self, table_name: str) -> str | None:
        self.probed_tables.append(table_name)
        result = self.results[table_name]
        if isinstance(result, Exception):
            raise result
        return result


class TestFreshnessProbeHandler:
    """Verifies the fail-soft scheduled handler over both curated datamart tables."""

    @pytest.mark.asyncio
    async def test_probe_logs_fresh_for_both_tables(self) -> None:
        bq = _StubBigQueryClient(
            {
                "btc_daily_utxo_distribution": "2026-10-31",
                "usdc_daily_organic_metrics": "2026-10-31",
            }
        )
        ctx = _stub_ctx()

        await run_freshness_probe(ctx, bq, today=date(2026, 11, 5))

        assert bq.probed_tables == list(DATAMART_TABLES)
        assert not [level for level, _ in ctx.logger.records if level != "INFO"]
        assert sum("FRESH" in msg for _, msg in ctx.logger.records) == 2

    @pytest.mark.asyncio
    async def test_probe_warns_stale_with_days_behind(self) -> None:
        bq = _StubBigQueryClient(
            {
                "btc_daily_utxo_distribution": "2026-09-30",
                "usdc_daily_organic_metrics": "2026-10-31",
            }
        )
        ctx = _stub_ctx()

        await run_freshness_probe(ctx, bq, today=date(2026, 11, 5))

        warnings = [msg for level, msg in ctx.logger.records if level == "WARNING"]
        assert len(warnings) == 1
        assert "STALE" in warnings[0]
        assert "31 days behind" in warnings[0]
        assert "btc_daily_utxo_distribution" in warnings[0]

    @pytest.mark.asyncio
    async def test_probe_logs_pending_within_grace_window(self) -> None:
        bq = _StubBigQueryClient(
            {
                "btc_daily_utxo_distribution": "2026-09-30",
                "usdc_daily_organic_metrics": "2026-09-30",
            }
        )
        ctx = _stub_ctx()

        await run_freshness_probe(ctx, bq, today=date(2026, 11, 2))

        assert all(level == "INFO" for level, _ in ctx.logger.records)
        assert sum("PENDING" in msg for _, msg in ctx.logger.records) == 2

    @pytest.mark.asyncio
    async def test_probe_is_fail_soft_and_still_probes_remaining_table(self) -> None:
        bq = _StubBigQueryClient(
            {
                "btc_daily_utxo_distribution": RuntimeError("BigQuery unavailable"),
                "usdc_daily_organic_metrics": "2026-10-31",
            }
        )
        ctx = _stub_ctx()

        await run_freshness_probe(ctx, bq, today=date(2026, 11, 5))

        errors = [msg for level, msg in ctx.logger.records if level == "ERROR"]
        assert len(errors) == 1
        assert "btc_daily_utxo_distribution" in errors[0]
        assert "usdc_daily_organic_metrics" in bq.probed_tables
        assert any("FRESH" in msg for _, msg in ctx.logger.records)


class TestUsageDigest:
    """Verifies thread-safe counter accumulation, rendering, and reset."""

    def test_record_increments_named_counters(self) -> None:
        digest = UsageDigest()
        digest.record("queries_served")
        digest.record("queries_served")
        digest.record("query_errors")

        snapshot = digest.snapshot()
        assert snapshot["queries_served"] == 2
        assert snapshot["query_errors"] == 1
        assert snapshot["rate_limited"] == 0

    def test_render_and_reset_emits_single_line_then_zeroes(self) -> None:
        digest = UsageDigest()
        digest.record("queries_served")
        digest.record("gemini_fallbacks")

        line = digest.render_and_reset()

        assert "\n" not in line
        assert "queries_served=1" in line
        assert "gemini_fallbacks=1" in line
        assert all(value == 0 for value in digest.snapshot().values())

    def test_concurrent_records_are_not_lost(self) -> None:
        digest = UsageDigest()
        threads = [
            threading.Thread(target=lambda: [digest.record("queries_served") for _ in range(50)])
            for _ in range(4)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert digest.snapshot()["queries_served"] == 200

    @pytest.mark.asyncio
    async def test_digest_handler_logs_and_resets(self) -> None:
        digest = UsageDigest()
        digest.record("rate_limited")
        ctx = _stub_ctx()

        await run_usage_digest(ctx, digest)

        logged = ctx.logger.records[0][1]
        assert "rate_limited=1" in logged
        assert all(value == 0 for value in digest.snapshot().values())


class TestGeminiFallbackCounting:
    """Verifies rule-based fallback degradation is counted on the usage digest."""

    @pytest.fixture(autouse=True)
    def _reset_singleton_digest(self) -> None:
        USAGE_DIGEST.render_and_reset()

    def test_unconfigured_router_counts_fallback_degradation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        router = GeminiQueryRouter(api_key=None)

        parsed = router.parse_prompt("tell me about bitcoin hodl waves in 2018")

        assert parsed["query_type"] == "btc_hodl_waves"
        assert USAGE_DIGEST.snapshot()["gemini_fallbacks"] == 1

    def test_direct_fallback_calls_are_not_degradations(self) -> None:
        router = GeminiQueryRouter(api_key=None)

        parsed = router.parse_prompt_fallback("usdc organic volume 2020")

        assert parsed["query_type"] == "usdc_organic_volume"
        assert USAGE_DIGEST.snapshot()["gemini_fallbacks"] == 0


class TestScheduleWiring:
    """Smoke-verifies the on_schedule registration contract against uAgents 0.26+."""

    @pytest.mark.asyncio
    async def test_register_housekeeping_attaches_cron_handlers(self) -> None:
        from uagents import Agent

        agent = Agent(name="housekeeping-smoke", seed="housekeeping smoke test seed 1234")

        register_housekeeping(agent, MagicMock())

        assert FRESHNESS_CRON == "0 6 * * *"
        assert DIGEST_CRON == "30 6 * * *"

    @pytest.mark.asyncio
    async def test_registered_cron_handlers_execute_probe_and_digest(self) -> None:
        class StubAgent:
            def __init__(self) -> None:
                self.schedules = {}

            def on_schedule(self, cron: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
                def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                    self.schedules[cron] = fn
                    return fn
                return decorator

        agent = StubAgent()
        bq = _StubBigQueryClient(
            {
                "btc_daily_utxo_distribution": "2026-10-31",
                "usdc_daily_organic_metrics": "2026-10-31",
            }
        )
        register_housekeeping(agent, bq)
        assert set(agent.schedules) == {FRESHNESS_CRON, DIGEST_CRON}

        ctx = _stub_ctx()
        await agent.schedules[FRESHNESS_CRON](ctx)
        assert bq.probed_tables == list(DATAMART_TABLES)

        await agent.schedules[DIGEST_CRON](ctx)
        assert any("Daily Usage Digest" in msg for _, msg in ctx.logger.records)
