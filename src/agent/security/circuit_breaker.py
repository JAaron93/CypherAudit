"""Security Circuit Breaker & Input Sanitization for SignalChain Oracle.

Guarantees zero dynamic SQL injection, validates structured query types,
and asserts schema boundaries before any BigQuery job is scheduled.
"""

import re
from datetime import datetime


class SecurityViolationError(Exception):
    """Raised when an incoming payload violates schema rules or security policies."""
    pass


class SecurityCircuitBreaker:
    """Validates query parameters against strict whitelists to prevent injection & abuse."""

    AUTHORIZED_QUERY_TYPES = {
        "btc_hodl_waves",
        "btc_microtransactions",
        "usdc_organic_volume",
        "usdc_eoa_topology",
    }

    AUTHORIZED_GRANULARITIES = {"daily", "monthly", "yearly"}

    DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def validate_query_type(self, query_type: str) -> bool:
        """Ensures query_type is strictly in the authorized catalog."""
        if not isinstance(query_type, str) or query_type not in self.AUTHORIZED_QUERY_TYPES:
            raise SecurityViolationError(
                f"Unauthorized query_type: '{query_type}'. Allowed: {sorted(list(self.AUTHORIZED_QUERY_TYPES))}"
            )
        return True

    def validate_granularity(self, granularity: str) -> bool:
        """Ensures granularity is daily, monthly, or yearly."""
        if not isinstance(granularity, str) or granularity.lower() not in self.AUTHORIZED_GRANULARITIES:
            raise SecurityViolationError(
                f"Unauthorized granularity: '{granularity}'. Allowed: {sorted(list(self.AUTHORIZED_GRANULARITIES))}"
            )
        return True

    def validate_date(self, date_str: str) -> str:
        """Validates that a date string is strictly YYYY-MM-DD and a valid calendar date."""
        if not isinstance(date_str, str) or not self.DATE_REGEX.match(date_str):
            raise SecurityViolationError(f"Invalid date format: '{date_str}'. Expected 'YYYY-MM-DD'.")

        try:
            parsed = datetime.strptime(date_str, "%Y-%m-%d")
            # Bound dates between 2009-01-01 (Bitcoin genesis) and 2030-01-01
            if parsed.year < 2009 or parsed.year > 2030:
                raise SecurityViolationError(f"Date out of historical range: '{date_str}'.")
            return date_str
        except ValueError as e:
            raise SecurityViolationError(f"Invalid calendar date '{date_str}': {e}") from e

    def sanitize_request_params(
        self, query_type: str, start_date: str, end_date: str, granularity: str = "daily"
    ) -> dict[str, str]:
        """Validates and returns sanitized query parameters."""
        self.validate_query_type(query_type)
        valid_start = self.validate_date(start_date)
        valid_end = self.validate_date(end_date)
        self.validate_granularity(granularity)

        if valid_start > valid_end:
            raise SecurityViolationError(f"start_date '{valid_start}' cannot be after end_date '{valid_end}'.")

        return {
            "query_type": query_type,
            "start_date": valid_start,
            "end_date": valid_end,
            "granularity": granularity.lower(),
        }
