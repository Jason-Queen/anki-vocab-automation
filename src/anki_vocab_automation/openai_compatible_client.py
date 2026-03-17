"""
Backward-compatible import shim for the provider-aware LLM client.
"""

from .llm_client import LLMClient, OpenAICompatibleClient

__all__ = ["LLMClient", "OpenAICompatibleClient"]
