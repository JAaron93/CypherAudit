"""Unit tests for Gemini Natural Language Query Router in SignalChain Oracle."""

from unittest.mock import MagicMock, patch
import pytest
from src.nl_parser.gemini_router import GeminiQueryRouter, SemanticParsingError


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
