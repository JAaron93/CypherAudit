"""Unit tests for Gemini Natural Language Query Router in SignalChain Oracle."""

from unittest.mock import MagicMock, patch
import pytest
from src.nl_parser.gemini_router import (
    DEFAULT_GEMINI_MODEL,
    GeminiQueryRouter,
    SemanticParsingError,
)


class TestGeminiQueryRouter:
    """Verifies that natural language prompts correctly map to validated AnalyticsQueryRequest."""

    def test_rule_based_fallback_mapping_btc_hodl(self):
        router = GeminiQueryRouter(api_key="mock-key")

        # Test rule-based mapper without network calls
        result = router.parse_prompt_fallback("What percentage of Bitcoin has been unspent for 2 years in 2025?")
        assert result["query_type"] == "btc_hodl_waves"
        assert result["start_date"] == "2025-01-01"
        assert result["end_date"] == "2025-12-31"

    def test_rule_based_fallback_mapping_usdc_organic(self):
        router = GeminiQueryRouter(api_key="mock-key")

        result = router.parse_prompt_fallback("Show me USDC organic payment volume vs bot volume for 2024")
        assert result["query_type"] == "usdc_organic_volume"
        assert result["start_date"] == "2024-01-01"
        assert result["end_date"] == "2024-12-31"

    def test_rule_based_fallback_mapping_microtransactions(self):
        router = GeminiQueryRouter(api_key="mock-key")

        result = router.parse_prompt_fallback("How many microtransactions and coffee purchases happened on Bitcoin in 2023?")
        assert result["query_type"] == "btc_microtransactions"

    def test_unsupported_prompt_raises_error(self):
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

