"""Unit tests for SignalChain Oracle Main Runner and Modular Prompt Loading."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.nl_parser.gemini_router import GeminiQueryRouter


class TestOracleInstructionsPrompt:
    """Verifies that the modular prompt instructions file exists and is dynamically ingested."""

    def test_oracle_instructions_file_exists(self):
        prompt_path = Path(__file__).parent.parent / "src" / "agent" / "prompts" / "oracle_instructions.md"
        assert prompt_path.exists(), f"Expected instructions file at {prompt_path}"
        content = prompt_path.read_text(encoding="utf-8")
        assert "SignalChain Oracle" in content
        assert "btc_hodl_waves" in content
        assert "usdc_organic_volume" in content
        assert "Financial Disclaimer" in content

    def test_gemini_router_loads_instructions_from_file(self):
        router = GeminiQueryRouter(api_key="mock-api-key")
        instructions = router.get_system_instructions()
        assert "SignalChain Oracle" in instructions
        assert "btc_hodl_waves" in instructions


class TestAgentMainRunner:
    """Verifies Agent initialization, protocol attachment, and startup configuration."""

    def test_agent_initialization(self):
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
