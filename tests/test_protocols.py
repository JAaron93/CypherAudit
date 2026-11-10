"""Unit & BDD tests for uAgents Protocol and Message Models in SignalChain Oracle."""

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

import src.agent.protocols.analytics_protocol as protocol_module
from src.agent.housekeeping import UsageDigest
from src.agent.protocols.analytics_protocol import (
    AnalyticsQueryRequest,
    AnalyticsQueryResponse,
    create_analytics_protocol,
)
from src.agent.security.circuit_breaker import SecurityCircuitBreaker


class TestAnalyticsProtocolModels:
    """Verifies Pydantic schema validation for Agentverse message exchange."""

    def test_valid_request_serialization(self) -> None:
        req = AnalyticsQueryRequest(
            query_type="btc_hodl_waves",
            start_date="2025-01-01",
            end_date="2025-12-31",
            granularity="daily",
        )
        assert req.query_type == "btc_hodl_waves"
        assert req.start_date == "2025-01-01"
        assert req.granularity == "daily"

    def test_request_requires_fields(self) -> None:
        with pytest.raises(ValidationError):
            AnalyticsQueryRequest(query_type="btc_hodl_waves")  # missing dates

    def test_response_serialization(self) -> None:
        resp = AnalyticsQueryResponse(
            status="SUCCESS",
            query_type="usdc_organic_volume",
            timeframe="2024-01-01 to 2024-12-31",
            bytes_scanned_mb=2.15,
            data_points=[{"date": "2024-06-01", "organic_volume_pct": 28.5}],
            empirical_summary="71.5% of volume was noise.",
            reproducible_sql="SELECT * FROM mart;",
        )
        assert resp.status == "SUCCESS"
        assert resp.bytes_scanned_mb == 2.15
        assert len(resp.data_points) == 1


def make_request(**overrides) -> AnalyticsQueryRequest:
    payload = {
        "query_type": "btc_hodl_waves",
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "granularity": "daily",
    }
    payload.update(overrides)
    return AnalyticsQueryRequest(**payload)


@pytest.fixture
def protocol_env(monkeypatch):
    """Captures the handler registered by the factory via a stub uagents.Protocol."""
    captured = {}

    class StubProtocol:
        def __init__(self, name=None, version=None):
            pass

        def on_message(self, **kwargs):
            captured["registration"] = kwargs

            def decorator(fn):
                captured["handler"] = fn
                return fn

            return decorator

    monkeypatch.setattr("uagents.Protocol", StubProtocol)
    monkeypatch.setattr(protocol_module, "USAGE_DIGEST", UsageDigest())

    def build(bigquery_client=None, rate_limiter=None, circuit_breaker=None):
        if rate_limiter is None:
            rate_limiter = MagicMock()
            rate_limiter.check_rate_limit.return_value = (True, "OK")
        create_analytics_protocol(
            bigquery_client if bigquery_client is not None else MagicMock(),
            rate_limiter,
            circuit_breaker if circuit_breaker is not None else SecurityCircuitBreaker(),
        )
        return captured["handler"]

    return SimpleNamespace(build=build, captured=captured)


@pytest.fixture
def ctx():
    context = MagicMock()
    context.send = AsyncMock()
    return context


class TestAnalyticsProtocolFactory:
    def test_returns_none_when_uagents_unavailable(self, monkeypatch) -> None:
        monkeypatch.setitem(sys.modules, "uagents", None)
        assert create_analytics_protocol(MagicMock(), MagicMock(), MagicMock()) is None

    def test_handler_registered_for_request_response_models(self, protocol_env) -> None:
        handler = protocol_env.build()
        assert callable(handler)
        registration = protocol_env.captured["registration"]
        assert registration["model"] is AnalyticsQueryRequest
        assert registration["replies"] == {AnalyticsQueryResponse}


class TestAnalyticsProtocolHandler:
    async def test_rate_limited_sender_gets_rate_limited_response(self, protocol_env, ctx) -> None:
        limiter = MagicMock()
        limiter.check_rate_limit.return_value = (False, "Daily limit exceeded (30 req/day).")
        bq = MagicMock()
        handler = protocol_env.build(bigquery_client=bq, rate_limiter=limiter)

        await handler(ctx, "agent1qsender", make_request())

        resp = ctx.send.call_args.args[1]
        assert resp.status == "RATE_LIMITED"
        assert resp.error_message == "Daily limit exceeded (30 req/day)."
        assert resp.bytes_scanned_mb == 0.0
        assert resp.data_points == []
        bq.execute_analytics_query.assert_not_called()
        assert protocol_module.USAGE_DIGEST.snapshot()["rate_limited"] == 1

    async def test_security_violation_returns_error_response(self, protocol_env, ctx) -> None:
        bq = MagicMock()
        handler = protocol_env.build(bigquery_client=bq)

        await handler(ctx, "agent1qsender", make_request(query_type="arbitrary_raw_sql"))

        resp = ctx.send.call_args.args[1]
        assert resp.status == "ERROR"
        assert "Validation Violation" in resp.error_message
        assert resp.bytes_scanned_mb == 0.0
        bq.execute_analytics_query.assert_not_called()
        assert protocol_module.USAGE_DIGEST.snapshot()["security_violations"] == 1

    async def test_success_path_forwards_bigquery_payload(self, protocol_env, ctx) -> None:
        bq = MagicMock()
        bq.execute_analytics_query.return_value = {
            "status": "SUCCESS",
            "query_type": "btc_hodl_waves",
            "timeframe": "2025-01-01 to 2025-12-31",
            "bytes_scanned_mb": 1.25,
            "data_points": [{"date": "2025-06-01", "pct_over_2y": 60.0}],
            "empirical_summary": "Empirical summary.",
            "reproducible_sql": "SELECT 1",
        }
        handler = protocol_env.build(bigquery_client=bq)

        await handler(ctx, "agent1qsender", make_request())

        resp = ctx.send.call_args.args[1]
        assert resp.status == "SUCCESS"
        assert resp.bytes_scanned_mb == 1.25
        assert resp.data_points == [{"date": "2025-06-01", "pct_over_2y": 60.0}]
        assert resp.empirical_summary == "Empirical summary."
        bq.execute_analytics_query.assert_called_once_with(
            query_type="btc_hodl_waves",
            start_date="2025-01-01",
            end_date="2025-12-31",
            granularity="daily",
        )
        assert protocol_module.USAGE_DIGEST.snapshot()["queries_served"] == 1

    async def test_bigquery_failure_returns_error_response(self, protocol_env, ctx) -> None:
        bq = MagicMock()
        bq.execute_analytics_query.side_effect = RuntimeError("quota exceeded")
        handler = protocol_env.build(bigquery_client=bq)

        await handler(ctx, "agent1qsender", make_request())

        resp = ctx.send.call_args.args[1]
        assert resp.status == "ERROR"
        assert "Query Execution Error: quota exceeded" in resp.error_message
        assert resp.timeframe == "2025-01-01 to 2025-12-31"
        assert protocol_module.USAGE_DIGEST.snapshot()["query_errors"] == 1
