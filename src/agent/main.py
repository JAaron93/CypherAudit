"""Main Entrypoint & ASI Agentverse Registration for SignalChain Oracle (CypherAudit).

Initializes the uAgent daemon, configures cryptographic identity, attaches security
guardrails and BigQuery clients, and exposes the blockchain analytics protocol.
"""

import os
import logging
from dotenv import load_dotenv
from uagents import Agent

from src.agent.protocols.analytics_protocol import create_analytics_protocol
from src.agent.security.circuit_breaker import SecurityCircuitBreaker
from src.agent.security.rate_limiter import TokenBucketRateLimiter
from src.bigquery.client import BigQueryAnalyticsClient

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("signalchain_oracle")


def create_agent() -> Agent:
    """Factory creating and configuring the SignalChain Oracle uAgent instance."""
    agent_name = os.getenv("AGENT_NAME", "signalchain-oracle")
    agent_seed = os.getenv("AGENT_SEED", "signalchain-oracle-default-production-seed-2026")
    agent_port = int(os.getenv("AGENT_PORT", "8000"))
    mailbox_key = os.getenv("AGENTVERSE_MAILBOX_KEY")
    endpoint = os.getenv("AGENT_ENDPOINT")

    agent_kwargs = {
        "name": agent_name,
        "seed": agent_seed,
        "port": agent_port,
    }

    if mailbox_key:
        agent_kwargs["mailbox"] = f"{mailbox_key}@https://agentverse.ai"
    elif endpoint:
        agent_kwargs["endpoint"] = [endpoint]

    agent = Agent(**agent_kwargs)

    # 1. Initialize Deterministic & Guardrail Layers
    project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
    dataset_id = os.getenv("BIGQUERY_DATASET", "crypto_analytics_mart")
    rate_per_min = int(os.getenv("RATE_LIMIT_PER_MINUTE", "5"))
    rate_per_day = int(os.getenv("RATE_LIMIT_PER_DAY", "30"))

    rate_limiter = TokenBucketRateLimiter(
        rate_per_minute=rate_per_min,
        rate_per_day=rate_per_day,
    )
    circuit_breaker = SecurityCircuitBreaker()
    bq_client = BigQueryAnalyticsClient(
        project_id=project_id,
        dataset_id=dataset_id,
    )

    # 2. Attach Analytics Protocol
    protocol = create_analytics_protocol(
        bigquery_client=bq_client,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
    )
    if protocol is not None:
        agent.include(protocol)

    # 3. Register Startup Event Banner
    @agent.on_event("startup")
    async def startup_handler(ctx):
        ctx.logger.info("=" * 70)
        ctx.logger.info("  🚀 SignalChain Oracle (CypherAudit) Agent Initialized")
        ctx.logger.info(f"  • Agent Name:     {agent.name}")
        ctx.logger.info(f"  • Agent Address:  {agent.address}")
        ctx.logger.info(f"  • BigQuery Mart:  {project_id}.{dataset_id}")
        ctx.logger.info(f"  • Rate Limits:    {rate_per_min} req/min, {rate_per_day} req/day")
        ctx.logger.info(f"  • Protocols:      blockchain_analytics_protocol_v1")
        ctx.logger.info("=" * 70)

    return agent


def main():
    """Starts the uAgent runtime loop."""
    logger.info("Starting SignalChain Oracle daemon...")
    agent = create_agent()
    agent.run()


if __name__ == "__main__":
    main()
