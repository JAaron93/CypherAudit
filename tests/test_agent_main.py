"""Unit tests for SignalChain Oracle Main Runner and Modular Prompt Loading."""

import os
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest

from src.agent.housekeeping import DIGEST_CRON, FRESHNESS_CRON
from src.nl_parser.gemini_router import GeminiQueryRouter


class TestOracleInstructionsPrompt:
    """Verifies that the modular prompt instructions file exists and is dynamically ingested."""

    def test_oracle_instructions_file_exists(self) -> None:
        prompt_path = Path(__file__).parent.parent / "src" / "agent" / "prompts" / "oracle_instructions.md"
        assert prompt_path.exists(), f"Expected instructions file at {prompt_path}"
        content = prompt_path.read_text(encoding="utf-8")
        assert "SignalChain Oracle" in content
        assert "btc_hodl_waves" in content
        assert "usdc_organic_volume" in content
        assert "Financial Disclaimer" in content

    def test_gemini_router_loads_instructions_from_file(self) -> None:
        router = GeminiQueryRouter(api_key="mock-api-key")
        instructions = router.get_system_instructions()
        assert "SignalChain Oracle" in instructions
        assert "btc_hodl_waves" in instructions


class TestAgentMainRunner:
    """Verifies Agent initialization, protocol attachment, and startup configuration."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self) -> None:
        from src.agent.main import create_agent

        with patch.dict(
            os.environ,
            {
                "AGENT_SEED": "test-secret-recovery-seed-phrase-for-testing",
                "AGENT_NAME": "test-signalchain-oracle",
                "GCP_PROJECT_ID": "test-gcp-project",
            },
        ):
            agent = create_agent()
            assert agent is not None
            assert agent.name == "test-signalchain-oracle"
            assert hasattr(agent, "address")
            assert len(agent.protocols) >= 1

    def test_agent_initialization_requires_seed(self) -> None:
        from src.agent.main import create_agent

        with patch.dict(
            os.environ,
            {
                "AGENT_SEED": "",
                "AGENT_NAME": "test-signalchain-oracle",
                "GCP_PROJECT_ID": "test-gcp-project",
            },
            clear=True,
        ):
            with pytest.raises(ValueError, match="AGENT_SEED environment variable is required"):
                create_agent()


class _MockAgent:
    """Stands in for uagents.Agent, capturing wiring decisions without starting a runtime."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.name = kwargs.get("name", "mock-agent")
        self.address = "agent1qmockaddress"
        self.included = []
        self.event_handlers = {}
        self.schedule_handlers = {}
        self.ran = False

    def include(self, protocol):
        self.included.append(protocol)

    def on_event(self, event_type):
        def decorator(fn):
            self.event_handlers[event_type] = fn
            return fn
        return decorator

    def on_schedule(self, cron):
        def decorator(fn):
            self.schedule_handlers[cron] = fn
            return fn
        return decorator

    def run(self):
        self.ran = True


@pytest.fixture
def mock_agent_env(monkeypatch):
    monkeypatch.setenv("AGENT_SEED", "test-seed-for-mock-agent-wiring")
    monkeypatch.delenv("AGENTVERSE_MAILBOX_KEY", raising=False)
    monkeypatch.delenv("AGENT_ENDPOINT", raising=False)
    instances = []

    def factory(**kwargs):
        agent = _MockAgent(**kwargs)
        instances.append(agent)
        return agent

    monkeypatch.setattr("src.agent.main.Agent", factory)
    return SimpleNamespace(instances=instances, factory=factory)


class TestAgentWiringVariants:
    """Verifies Agentverse mailbox/endpoint wiring, protocol attachment, and daemon startup."""

    def test_mailbox_key_configures_agentverse_mailbox(self, mock_agent_env, monkeypatch) -> None:
        monkeypatch.setenv("AGENTVERSE_MAILBOX_KEY", "test-mailbox-key")
        from src.agent.main import create_agent

        agent = create_agent()
        assert agent.kwargs["mailbox"] == "test-mailbox-key@https://agentverse.ai"
        assert "endpoint" not in agent.kwargs

    def test_endpoint_used_when_mailbox_absent(self, mock_agent_env, monkeypatch) -> None:
        monkeypatch.setenv("AGENT_ENDPOINT", "http://localhost:8000/submit")
        from src.agent.main import create_agent

        agent = create_agent()
        assert agent.kwargs["endpoint"] == ["http://localhost:8000/submit"]
        assert "mailbox" not in agent.kwargs

    def test_none_protocol_skips_include_but_keeps_housekeeping(self, mock_agent_env, monkeypatch) -> None:
        monkeypatch.setattr("src.agent.main.create_analytics_protocol", lambda **kwargs: None)
        from src.agent.main import create_agent

        agent = create_agent()
        assert agent.included == []
        assert set(agent.schedule_handlers) == {FRESHNESS_CRON, DIGEST_CRON}

    @pytest.mark.asyncio
    async def test_startup_handler_logs_configuration_banner(self, mock_agent_env) -> None:
        from src.agent.main import create_agent

        agent = create_agent()
        ctx = MagicMock()
        await agent.event_handlers["startup"](ctx)
        banner = " ".join(str(call.args[0]) for call in ctx.logger.info.call_args_list)
        assert "SignalChain Oracle" in banner
        assert "crypto_analytics_mart" in banner

    def test_main_runs_the_created_agent(self, mock_agent_env) -> None:
        from src.agent.main import main

        main()
        assert mock_agent_env.instances[0].ran is True

    def test_module_entrypoint_starts_daemon(self, mock_agent_env, monkeypatch) -> None:
        monkeypatch.setattr("uagents.Agent", mock_agent_env.factory)
        monkeypatch.delitem(sys.modules, "src.agent.main")
        runpy.run_module("src.agent.main", run_name="__main__")
        assert mock_agent_env.instances[0].ran is True
