"""Unit tests for the Security Layer & Rate Limiter in SignalChain Oracle."""

import time
import pytest
from src.agent.security.rate_limiter import TokenBucketRateLimiter
from src.agent.security.circuit_breaker import SecurityCircuitBreaker, SecurityViolationError


class TestTokenBucketRateLimiter:
    """Verifies that rate limiting throttles excessive requests per agent_address / IP."""

    def test_allow_requests_within_limit(self) -> None:
        limiter = TokenBucketRateLimiter(rate_per_minute=5, rate_per_day=30)
        agent_id = "agent1qtestaddress123"

        # First 5 requests should pass
        for _ in range(5):
            allowed, reason = limiter.check_rate_limit(agent_id)
            assert allowed is True
            assert reason == "OK"

    def test_block_burst_requests_exceeding_per_minute(self) -> None:
        limiter = TokenBucketRateLimiter(rate_per_minute=5, rate_per_day=30)
        agent_id = "agent1qspambot456"

        # Exhaust the 5 requests
        for _ in range(5):
            limiter.check_rate_limit(agent_id)

        # 6th request must be rejected
        allowed, reason = limiter.check_rate_limit(agent_id)
        assert allowed is False
        assert "per-minute limit exceeded" in reason.lower()

    def test_independent_rate_limits_across_different_agents(self) -> None:
        limiter = TokenBucketRateLimiter(rate_per_minute=2, rate_per_day=10)
        agent_a = "agent1q_alice"
        agent_b = "agent1q_bob"

        # Exhaust Alice
        limiter.check_rate_limit(agent_a)
        limiter.check_rate_limit(agent_a)
        assert limiter.check_rate_limit(agent_a)[0] is False

        # Bob should still be allowed
        assert limiter.check_rate_limit(agent_b)[0] is True

    def test_daily_ceiling_blocks_after_quota_exhausted(self) -> None:
        limiter = TokenBucketRateLimiter(rate_per_minute=100, rate_per_day=2)
        agent_id = "agent1qdailyquota"

        assert limiter.check_rate_limit(agent_id)[0] is True
        assert limiter.check_rate_limit(agent_id)[0] is True

        allowed, reason = limiter.check_rate_limit(agent_id)
        assert allowed is False
        assert "Daily limit exceeded" in reason

    def test_daily_counter_resets_after_24_hours(self) -> None:
        limiter = TokenBucketRateLimiter(rate_per_minute=100, rate_per_day=1)
        agent_id = "agent1qdailyreset"

        assert limiter.check_rate_limit(agent_id)[0] is True
        assert limiter.check_rate_limit(agent_id)[0] is False

        limiter.quotas[agent_id].day_start_timestamp -= 86401
        allowed, reason = limiter.check_rate_limit(agent_id)
        assert allowed is True
        assert reason == "OK"


class TestSecurityCircuitBreaker:
    """Verifies input sanitization and protection against SQL injection / abnormal payloads."""

    def test_valid_query_types_pass(self) -> None:
        breaker = SecurityCircuitBreaker()
        assert breaker.validate_query_type("btc_hodl_waves") is True
        assert breaker.validate_query_type("btc_microtransactions") is True
        assert breaker.validate_query_type("usdc_organic_volume") is True
        assert breaker.validate_query_type("usdc_eoa_topology") is True

    def test_invalid_query_type_raises_violation(self) -> None:
        breaker = SecurityCircuitBreaker()
        with pytest.raises(SecurityViolationError, match="Unauthorized query_type"):
            breaker.validate_query_type("arbitrary_raw_sql_execution")

    def test_date_format_validation(self) -> None:
        breaker = SecurityCircuitBreaker()
        assert breaker.validate_date("2024-01-01") == "2024-01-01"
        assert breaker.validate_date("2026-08-18") == "2026-08-18"

        with pytest.raises(SecurityViolationError, match="Invalid date format"):
            breaker.validate_date("DROP TABLE;--")

        with pytest.raises(SecurityViolationError, match="Invalid calendar date"):
            breaker.validate_date("2024-99-99")

    def test_prevent_sql_injection_payloads(self) -> None:
        breaker = SecurityCircuitBreaker()
        malicious_inputs = [
            "2024-01-01' OR '1'='1",
            "2024-01-01; SELECT * FROM credentials;",
            "UNION ALL SELECT password FROM users--",
        ]
        for bad_input in malicious_inputs:
            with pytest.raises(SecurityViolationError):
                breaker.validate_date(bad_input)

    @pytest.mark.parametrize("granularity", ["daily", "monthly", "yearly", "MONTHLY", "Daily"])
    def test_valid_granularities_pass(self, granularity) -> None:
        assert SecurityCircuitBreaker().validate_granularity(granularity) is True

    @pytest.mark.parametrize("granularity", ["hourly", "weekly", "", None, 42, "daily; DROP"])
    def test_invalid_granularities_raise(self, granularity) -> None:
        with pytest.raises(SecurityViolationError, match="Unauthorized granularity"):
            SecurityCircuitBreaker().validate_granularity(granularity)

    def test_sanitize_request_params_normalizes_granularity(self) -> None:
        params = SecurityCircuitBreaker().sanitize_request_params(
            "btc_hodl_waves", "2025-01-01", "2025-12-31", granularity="MONTHLY"
        )
        assert params == {
            "query_type": "btc_hodl_waves",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "granularity": "monthly",
        }

    def test_sanitize_rejects_inverted_date_range(self) -> None:
        with pytest.raises(SecurityViolationError, match="cannot be after"):
            SecurityCircuitBreaker().sanitize_request_params(
                "btc_hodl_waves", "2025-12-31", "2025-01-01"
            )

    def test_sanitize_propagates_date_injection_violation(self) -> None:
        with pytest.raises(SecurityViolationError):
            SecurityCircuitBreaker().sanitize_request_params(
                "btc_hodl_waves", "2025-01-01' OR '1'='1", "2025-12-31"
            )

    def test_sanitize_rejects_unauthorized_query_type(self) -> None:
        with pytest.raises(SecurityViolationError, match="Unauthorized query_type"):
            SecurityCircuitBreaker().sanitize_request_params(
                "arbitrary_raw_sql", "2025-01-01", "2025-12-31"
            )
