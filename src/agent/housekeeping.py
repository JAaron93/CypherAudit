"""Scheduled housekeeping for SignalChain Oracle: read-only datamart freshness
monitoring and runtime usage/health reporting (uAgents 0.26+ ``on_schedule``).

Ingestion ownership stays 100% serverless in GCP (Cloud Scheduler ->
BigQuery scheduled MERGE). This module never writes to the datamart and never
runs ETL; it detects when that pipeline silently stops producing rows and
reports agent runtime health. Every handler is fail-soft: detection failures
are logged, never raised, so analytics message handling is never disrupted.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uagents import Context

    from src.bigquery.client import BigQueryAnalyticsClient

FRESHNESS_CRON: str = "0 6 * * *"
DIGEST_CRON: str = "30 6 * * *"
DATAMART_TABLES: tuple[str, ...] = (
    "btc_daily_utxo_distribution",
    "usdc_daily_organic_metrics",
)
GRACE_DAYS: int = 2


@dataclass(frozen=True)
class FreshnessReport:
    """Outcome of comparing a table's observed MAX(date) against the expected ceiling."""

    table_name: str
    max_date: date | None
    expected_ceiling: date
    status: str
    days_behind: int


def expected_data_ceiling(today: date) -> date:
    """Returns the last day of the previous calendar month (the monthly MERGE target)."""
    first_of_current = today.replace(day=1)
    return first_of_current - timedelta(days=1)


def previous_data_ceiling(today: date) -> date:
    """Returns the last day of the month before the previous one."""
    prev_month_end = expected_data_ceiling(today)
    return prev_month_end.replace(day=1) - timedelta(days=1)


def evaluate_freshness(
    table_name: str,
    max_date: date | None,
    today: date,
    grace_days: int = GRACE_DAYS,
) -> FreshnessReport:
    """Evaluates ingestion staleness for one datamart table.

    States:
      FRESH  - observed MAX(date) covers the expected monthly ceiling.
      PENDING - within the grace window at month start and at most one monthly
                cycle behind (the in-flight cycle may not have landed yet).
      STALE  - the GCP scheduled ingestion appears to have stopped.
    """
    ceiling = expected_data_ceiling(today)
    if max_date is None:
        return FreshnessReport(table_name, None, ceiling, "STALE", 0)
    if max_date >= ceiling:
        return FreshnessReport(table_name, max_date, ceiling, "FRESH", 0)

    days_behind = (ceiling - max_date).days
    if today.day <= grace_days and max_date >= previous_data_ceiling(today):
        return FreshnessReport(table_name, max_date, ceiling, "PENDING", days_behind)
    return FreshnessReport(table_name, max_date, ceiling, "STALE", days_behind)


def _log_freshness_report(ctx: Context, report: FreshnessReport) -> None:
    if report.status == "STALE":
        ctx.logger.warning(
            f"🚨 DATAMART STALE: {report.table_name} current through {report.max_date}, "
            f"expected {report.expected_ceiling} ({report.days_behind} days behind) — "
            f"GCP scheduled ingestion may have stopped."
        )
    elif report.status == "PENDING":
        ctx.logger.info(
            f"⏳ Datamart PENDING: {report.table_name} current through {report.max_date}; "
            f"ingestion cycle for {report.expected_ceiling.strftime('%Y-%m')} still within grace window."
        )
    else:
        ctx.logger.info(
            f"✅ Datamart FRESH: {report.table_name} current through {report.max_date} "
            f"(expected {report.expected_ceiling})."
        )


async def run_freshness_probe(
    ctx: Context,
    bq_client: BigQueryAnalyticsClient,
    *,
    today: date | None = None,
) -> None:
    """Probes MAX(date) for every curated datamart table. Fail-soft by contract."""
    effective_today = today or datetime.now(timezone.utc).date()
    for table_name in DATAMART_TABLES:
        try:
            raw_max_date = await asyncio.to_thread(bq_client.fetch_table_max_date, table_name)
            max_date = date.fromisoformat(raw_max_date) if raw_max_date else None
            _log_freshness_report(ctx, evaluate_freshness(table_name, max_date, effective_today))
        except Exception as e:
            ctx.logger.error(f"Freshness probe failed for {table_name} (fail-soft): {e}")
