"""Unit & BDD tests for uAgents Protocol and Message Models in SignalChain Oracle."""

import pytest
from pydantic import ValidationError
from src.agent.protocols.analytics_protocol import AnalyticsQueryRequest, AnalyticsQueryResponse


class TestAnalyticsProtocolModels:
    """Verifies Pydantic schema validation for Agentverse message exchange."""

    def test_valid_request_serialization(self):
        req = AnalyticsQueryRequest(
            query_type="btc_hodl_waves",
            start_date="2025-01-01",
            end_date="2025-12-31",
            granularity="daily",
        )
        assert req.query_type == "btc_hodl_waves"
        assert req.start_date == "2025-01-01"
        assert req.granularity == "daily"

    def test_request_requires_fields(self):
        with pytest.raises(ValidationError):
            AnalyticsQueryRequest(query_type="btc_hodl_waves")  # missing dates

    def test_response_serialization(self):
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
