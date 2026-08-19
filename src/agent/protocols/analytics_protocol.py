"""uAgents Protocol Definition and Message Models for SignalChain Oracle."""

from typing import Any
from pydantic import BaseModel, Field


class AnalyticsQueryRequest(BaseModel):
    """Structured request payload for the SignalChain Analytics Oracle."""
    query_type: str = Field(
        ...,
        description="Type of analysis: 'btc_hodl_waves', 'btc_microtransactions', 'usdc_organic_volume', 'usdc_eoa_topology'",
    )
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    granularity: str = Field(default="daily", description="Time aggregation: 'daily', 'monthly', 'yearly'")


class AnalyticsQueryResponse(BaseModel):
    """Structured response payload containing empirical metrics, summaries, and reproducible SQL."""
    status: str = Field(..., description="'SUCCESS', 'RATE_LIMITED', or 'ERROR'")
    query_type: str = Field(..., description="Executed query type")
    timeframe: str = Field(..., description="Applied date range")
    bytes_scanned_mb: float = Field(..., description="Total megabytes scanned by BigQuery engine")
    data_points: list[dict[str, Any]] = Field(default_factory=list, description="Array of time-series data records")
    empirical_summary: str = Field(..., description="Human-readable factual interpretation of findings")
    reproducible_sql: str = Field(..., description="Exact ANSI SQL template used to derive results")
    error_message: str | None = Field(default=None, description="Detailed error explanation if status != SUCCESS")


def create_analytics_protocol(bigquery_client, rate_limiter, circuit_breaker):
    """Factory creating the uAgents Protocol instance wired with security guardrails and BigQuery client."""
    try:
        from uagents import Protocol, Context
    except ImportError:
        # Fallback for environments without full uagents C-extensions
        return None

    proto = Protocol(name="blockchain_analytics_protocol_v1", version="1.0.0")

    @proto.on_message(model=AnalyticsQueryRequest, replies={AnalyticsQueryResponse})
    async def handle_analytics_query(ctx: Context, sender: str, msg: AnalyticsQueryRequest):
        ctx.logger.info(f"Received {msg.query_type} query from {sender}")

        # 1. Rate Limiting Check
        allowed, reason = rate_limiter.check_rate_limit(sender)
        if not allowed:
            ctx.logger.warning(f"Rate limit exceeded for sender {sender}: {reason}")
            await ctx.send(
                sender,
                AnalyticsQueryResponse(
                    status="RATE_LIMITED",
                    query_type=msg.query_type,
                    timeframe=f"{msg.start_date} to {msg.end_date}",
                    bytes_scanned_mb=0.0,
                    data_points=[],
                    empirical_summary="",
                    reproducible_sql="",
                    error_message=reason,
                ),
            )
            return

        # 2. Input Sanitization & Circuit Breaker
        try:
            params = circuit_breaker.sanitize_request_params(
                query_type=msg.query_type,
                start_date=msg.start_date,
                end_date=msg.end_date,
                granularity=msg.granularity,
            )
        except Exception as e:
            await ctx.send(
                sender,
                AnalyticsQueryResponse(
                    status="ERROR",
                    query_type=msg.query_type,
                    timeframe="",
                    bytes_scanned_mb=0.0,
                    data_points=[],
                    empirical_summary="",
                    reproducible_sql="",
                    error_message=f"Validation Violation: {e}",
                ),
            )
            return

        # 3. BigQuery Execution
        try:
            result = bigquery_client.execute_analytics_query(
                query_type=params["query_type"],
                start_date=params["start_date"],
                end_date=params["end_date"],
                granularity=params["granularity"],
            )
            await ctx.send(
                sender,
                AnalyticsQueryResponse(
                    status=result["status"],
                    query_type=result["query_type"],
                    timeframe=result["timeframe"],
                    bytes_scanned_mb=result["bytes_scanned_mb"],
                    data_points=result["data_points"],
                    empirical_summary=result["empirical_summary"],
                    reproducible_sql=result["reproducible_sql"],
                ),
            )
        except Exception as e:
            await ctx.send(
                sender,
                AnalyticsQueryResponse(
                    status="ERROR",
                    query_type=msg.query_type,
                    timeframe=f"{msg.start_date} to {msg.end_date}",
                    bytes_scanned_mb=0.0,
                    data_points=[],
                    empirical_summary="",
                    reproducible_sql="",
                    error_message=f"Query Execution Error: {e}",
                ),
            )

    return proto
