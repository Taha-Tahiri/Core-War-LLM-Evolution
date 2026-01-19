"""
OpenAI LLM Provider

Supports GPT-4, GPT-4-turbo, GPT-3.5-turbo, and other OpenAI models.
"""

import os
from typing import Optional

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """
    OpenAI API provider for warrior generation.
    
    Supports models like gpt-4, gpt-4-turbo, gpt-3.5-turbo.
    """
    
    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the OpenAI provider.
        
        Args:
            model: The model to use (e.g., "gpt-4", "gpt-4-turbo")
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Lazy import to avoid requiring openai package if not used
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "openai package required. Install with: pip install openai"
            )
    
    @property
    def name(self) -> str:
        return f"OpenAI/{self.model}"
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate text using OpenAI API.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt,
            })
        
        messages.append({
            "role": "user",
            "content": prompt,
        })
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return response.choices[0].message.content or ""
