"""
Anthropic LLM Provider

Supports Claude models (claude-3-opus, claude-3-sonnet, etc.)
"""

import os
from typing import Optional

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    """
    Anthropic API provider for warrior generation.
    
    Supports Claude models like claude-3-opus, claude-3-sonnet, claude-3-haiku.
    """
    
    def __init__(
        self,
        model: str = "claude-3-sonnet-20240229",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the Anthropic provider.
        
        Args:
            model: The model to use (e.g., "claude-3-opus-20240229")
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Lazy import to avoid requiring anthropic package if not used
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: pip install anthropic"
            )
    
    @property
    def name(self) -> str:
        return f"Anthropic/{self.model}"
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate text using Anthropic API.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        # Anthropic temperature is 0-1, clamp if needed
        temperature = min(1.0, max(0.0, temperature))
        
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        response = self.client.messages.create(**kwargs)
        
        # Extract text from response
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return ""
