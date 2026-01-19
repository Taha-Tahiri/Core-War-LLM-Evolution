"""
LLM Interface Module - Support for multiple LLM providers.

Provides a unified interface for generating and mutating
Core War warriors using various LLM providers.
"""

from .base import LLMProvider, WarriorGenerator
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .ollama_provider import OllamaProvider

__all__ = [
    "LLMProvider",
    "WarriorGenerator",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
]
