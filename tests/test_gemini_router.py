"""Unit tests for Gemini Natural Language Query Router in SignalChain Oracle."""

from unittest.mock import MagicMock, patch
import pytest
from src.agent.housekeeping import USAGE_DIGEST
from src.nl_parser.gemini_router import (
    DEFAULT_GEMINI_MODEL,
    GeminiQueryRouter,
    SemanticParsingError,
)


class TestGeminiQueryRouter:
    """Verifies that natural language prompts correctly map to validated AnalyticsQueryRequest."""

    def test_rule_based_fallback_mapping_btc_hodl(self) -> None:
        router = GeminiQueryRouter(api_key="mock-key")

        # Test rule-based mapper without network calls
        result = router.parse_prompt_fallback("What percentage of Bitcoin has been unspent for 2 years in 2025?")
        assert result["query_type"] == "btc_hodl_waves"
        assert result["start_date"] == "2025-01-01"
        assert result["end_date"] == "2025-12-31"

    def test_rule_based_fallback_mapping_usdc_organic(self) -> None:
        router = GeminiQueryRouter(api_key="mock-key")

        result = router.parse_prompt_fallback("Show me USDC organic payment volume vs bot volume for 2024")
        assert result["query_type"] == "usdc_organic_volume"
        assert result["start_date"] == "2024-01-01"
        assert result["end_date"] == "2024-12-31"

    def test_rule_based_fallback_mapping_microtransactions(self) -> None:
        router = GeminiQueryRouter(api_key="mock-key")

        result = router.parse_prompt_fallback("How many microtransactions and coffee purchases happened on Bitcoin in 2023?")
        assert result["query_type"] == "btc_microtransactions"

    def test_unsupported_prompt_raises_error(self) -> None:
        router = GeminiQueryRouter(api_key="mock-key")

        with pytest.raises(SemanticParsingError, match="Could not map prompt"):
            router.parse_prompt_fallback("What is the weather in Tokyo tomorrow?")

    def test_default_gemini_model_is_gemini_3_8_flash(self):
        assert DEFAULT_GEMINI_MODEL == "gemini-3.8-flash"

    def test_router_uses_gemini_3_8_flash_by_default(self):
        router = GeminiQueryRouter(api_key="mock-key")
        assert router.model == "gemini-3.8-flash"

    def test_router_accepts_custom_model_parameter(self):
        router = GeminiQueryRouter(api_key="mock-key", model="custom-gemini-model")
        assert router.model == "custom-gemini-model"

    def test_parse_prompt_calls_gemini_3_8_flash_api(self):
        router = GeminiQueryRouter(api_key="mock-key")
        mock_response = MagicMock()
        mock_response.text = '{"query_type": "btc_hodl_waves", "start_date": "2025-01-01", "end_date": "2025-12-31", "granularity": "daily"}'

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(router, "_get_client", return_value=mock_client):
            result = router.parse_prompt("Bitcoin dormancy in 2025")

        assert result["query_type"] == "btc_hodl_waves"
        mock_client.models.generate_content.assert_called_once()
        _, kwargs = mock_client.models.generate_content.call_args
        assert kwargs["model"] == "gemini-3.8-flash"

    def test_router_uses_env_model_override(self, monkeypatch):
        monkeypatch.setenv("GEMINI_MODEL", "gemini-custom-env")
        router = GeminiQueryRouter(api_key="mock-key")
        assert router.model == "gemini-custom-env"

    def test_router_handles_empty_env_model_with_default_fallback(self, monkeypatch):
        monkeypatch.setenv("GEMINI_MODEL", "   ")
        router = GeminiQueryRouter(api_key="mock-key")
        assert router.model == DEFAULT_GEMINI_MODEL

    def test_router_parameter_takes_precedence_over_env_model(self, monkeypatch):
        monkeypatch.setenv("GEMINI_MODEL", "gemini-custom-env")
        router = GeminiQueryRouter(api_key="mock-key", model="gemini-explicit-param")
        assert router.model == "gemini-explicit-param"


class TestGeminiClientLifecycle:
    """Verifies lazy google-genai client initialization, caching, and failure handling."""

    def test_client_initialized_once_and_cached(self) -> None:
        router = GeminiQueryRouter(api_key="mock-key")
        with patch("google.genai.Client") as mock_genai:
            first = router._get_client()
            second = router._get_client()
        assert first is mock_genai.return_value
        assert second is first
        mock_genai.assert_called_once_with(api_key="mock-key")

    def test_initialization_failure_returns_none(self) -> None:
        router = GeminiQueryRouter(api_key="mock-key")
        with patch("google.genai.Client", side_effect=RuntimeError("invalid credentials")):
            assert router._get_client() is None

    def test_missing_api_key_skips_client_creation(self, monkeypatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        router = GeminiQueryRouter()
        assert router._get_client() is None


class TestRouterDegradationPaths:
    """Verifies graceful degradation to the embedded prompt and rule-based parser."""

    def test_missing_instructions_file_falls_back_to_embedded_prompt(self, monkeypatch) -> None:
        router = GeminiQueryRouter(api_key="mock-key")
        monkeypatch.setattr("pathlib.Path.exists", lambda self: False)
        assert router.get_system_instructions() == router.SYSTEM_INSTRUCTION

    def test_instructions_read_failure_falls_back_to_embedded_prompt(self, monkeypatch) -> None:
        router = GeminiQueryRouter(api_key="mock-key")
        monkeypatch.setattr("pathlib.Path.exists", lambda self: True)

        def unreadable(self, encoding=None, errors=None):
            raise OSError("disk unreadable")

        monkeypatch.setattr("pathlib.Path.read_text", unreadable)
        assert router.get_system_instructions() == router.SYSTEM_INSTRUCTION

    def test_api_failure_degrades_to_rule_based_parser_and_counts(self, monkeypatch) -> None:
        router = GeminiQueryRouter(api_key="mock-key")
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("503 unavailable")
        monkeypatch.setattr(router, "_get_client", lambda: mock_client)
        before = USAGE_DIGEST.snapshot()["gemini_fallbacks"]

        result = router.parse_prompt("bitcoin hodl waves in 2025")

        assert result["query_type"] == "btc_hodl_waves"
        assert USAGE_DIGEST.snapshot()["gemini_fallbacks"] == before + 1

    def test_fallback_maps_eoa_topology_keywords(self) -> None:
        router = GeminiQueryRouter(api_key=None)
        result = router.parse_prompt_fallback("Show merchant p2p settlement topology")
        assert result["query_type"] == "usdc_eoa_topology"
        assert result["start_date"] == "2025-01-01"

