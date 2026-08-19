"""Token Bucket / Leaky Bucket Rate Limiter for SignalChain Oracle.

Provides defense-in-depth protection against API quota exhaustion, opportunistic adversaries,
and spam bots targeting the ASI Agentverse endpoint.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class AgentQuota:
    """Tracks token bucket state and daily request counts for a single agent/IP."""
    tokens: float
    last_updated: float
    daily_count: int = 0
    day_start_timestamp: float = field(default_factory=time.time)


class TokenBucketRateLimiter:
    """Thread-safe Token Bucket Rate Limiter with per-minute and per-day ceilings."""

    def __init__(self, rate_per_minute: int = 5, rate_per_day: int = 30):
        self.rate_per_minute = rate_per_minute
        self.rate_per_day = rate_per_day
        self.burst_capacity = float(rate_per_minute)
        self.fill_rate = float(rate_per_minute) / 60.0  # tokens added per second
        self.quotas: dict[str, AgentQuota] = defaultdict(
            lambda: AgentQuota(
                tokens=self.burst_capacity,
                last_updated=time.time(),
                daily_count=0,
                day_start_timestamp=time.time(),
            )
        )
        self._lock = Lock()

    def check_rate_limit(self, agent_id: str) -> tuple[bool, str]:
        """Checks if a request from agent_id is permitted under current quotas.

        Returns:
            (allowed: bool, message: str)
        """
        with self._lock:
            now = time.time()
            quota = self.quotas[agent_id]

            # Reset daily counter if 24 hours have elapsed
            if now - quota.day_start_timestamp >= 86400:
                quota.daily_count = 0
                quota.day_start_timestamp = now

            # Check daily ceiling
            if quota.daily_count >= self.rate_per_day:
                return False, f"Daily limit exceeded ({self.rate_per_day} req/day). Try again tomorrow."

            # Replenish minute-bucket tokens based on elapsed time
            elapsed = now - quota.last_updated
            quota.tokens = min(self.burst_capacity, quota.tokens + (elapsed * self.fill_rate))
            quota.last_updated = now

            # Check if at least 1 token is available
            if quota.tokens >= 1.0:
                quota.tokens -= 1.0
                quota.daily_count += 1
                return True, "OK"
            else:
                retry_after_sec = int((1.0 - quota.tokens) / self.fill_rate) + 1
                return False, f"Per-minute limit exceeded ({self.rate_per_minute} req/min). Retry in {retry_after_sec}s."
