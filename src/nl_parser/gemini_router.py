"""Gemini 3.8 Flash Semantic Query Router & Natural Language Parser.

Translates human-readable analytical questions from Agentverse users into typed,
sanitized query parameters for the BigQuery Analytics Client.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("cypheraudit.nl_parser")

DEFAULT_GEMINI_MODEL: str = "gemini-3.8-flash"


class SemanticParsingError(Exception):
    """Raised when an incoming natural language prompt cannot be mapped to an authorized query type."""
    pass


class GeminiQueryRouter:
    """Routes natural language queries to structured analytical parameters."""

    SYSTEM_INSTRUCTION = """
You are the query router for SignalChain Oracle, an on-chain analytics agent.
Translate the user's prompt into one of the following exact query types:
- 'btc_hodl_waves': Inquiries about Bitcoin supply dormancy, UTXO age distribution, HODLing, long-term holding.
- 'btc_microtransactions': Inquiries about Bitcoin retail payments, everyday commerce, transactions <$10 or <$500, fee drag.
- 'usdc_organic_volume': Inquiries about USDC/stablecoin organic volume vs bot/MEV noise, real economic activity.
- 'usdc_eoa_topology': Inquiries about P2P/merchant transfers (EOA to EOA) vs DeFi/smart contract interactions.

Return ONLY a JSON object with this exact schema:
{
  "query_type": "btc_hodl_waves" | "btc_microtransactions" | "usdc_organic_volume" | "usdc_eoa_topology",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "granularity": "daily" | "monthly" | "yearly"
}
"""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        env_model = (os.getenv("GEMINI_MODEL") or "").strip()
        self.model = model or env_model or DEFAULT_GEMINI_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize google-genai Client: {e}")
            return self._client
        return self._client

    def get_system_instructions(self) -> str:
        """Dynamically loads the modular system prompt instructions from markdown artifact if available."""
        instructions_path = Path(__file__).parent.parent / "agent" / "prompts" / "oracle_instructions.md"
        if instructions_path.exists():
            try:
                return instructions_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Could not read modular instructions at {instructions_path}: {e}")
        return self.SYSTEM_INSTRUCTION

    def parse_prompt(self, prompt: str) -> dict[str, str]:
        """Parses a natural language prompt using Gemini Flash, falling back to rule-based parser if unconfigured."""
        client = self._get_client()
        if client is not None:
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "system_instruction": self.get_system_instructions(),
                        "response_mime_type": "application/json",
                    },
                )
                data = json.loads(response.text)
                return data
            except Exception as e:
                logger.warning(f"Gemini API call failed, using rule-based parser fallback: {e}")

        return self.parse_prompt_fallback(prompt)

    def parse_prompt_fallback(self, prompt: str) -> dict[str, str]:
        """Rule-based heuristic parser for offline testing and deterministic fallback."""
        lowered = prompt.lower()

        # Extract year if present
        year_match = re.search(r"\b(201[4-9]|202[0-9])\b", lowered)
        year = year_match.group(1) if year_match else "2025"
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        if any(w in lowered for w in ["hodl", "dormant", "age band", "unspent", "store of value"]):
            return {
                "query_type": "btc_hodl_waves",
                "start_date": start_date,
                "end_date": end_date,
                "granularity": "daily",
            }
        elif any(w in lowered for w in ["microtransaction", "coffee", "retail payment", "fee drag", "small purchase"]):
            return {
                "query_type": "btc_microtransactions",
                "start_date": start_date,
                "end_date": end_date,
                "granularity": "daily",
            }
        elif any(w in lowered for w in ["usdc", "stablecoin", "organic", "bot", "noise", "mev", "wash"]):
            return {
                "query_type": "usdc_organic_volume",
                "start_date": start_date,
                "end_date": end_date,
                "granularity": "daily",
            }
        elif any(w in lowered for w in ["eoa", "contract", "p2p", "merchant", "defi", "topology"]):
            return {
                "query_type": "usdc_eoa_topology",
                "start_date": start_date,
                "end_date": end_date,
                "granularity": "daily",
            }

        raise SemanticParsingError(
            f"Could not map prompt '{prompt}' to an authorized analytical query. "
            f"Please inquire about Bitcoin HODL waves, microtransactions, USDC organic volume, or EOA topology."
        )
