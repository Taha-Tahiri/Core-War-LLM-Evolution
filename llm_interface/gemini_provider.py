"""
Google Gemini LLM Provider

Supports Gemini models (gemini-pro, gemini-1.5-pro, gemini-1.5-flash, etc.)
"""

import os
from typing import Optional

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    """
    Google Gemini API provider for warrior generation.
    
    Supports models like gemini-pro, gemini-1.5-pro, gemini-1.5-flash.
    """
    
    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the Gemini provider.
        
        Args:
            model: The model to use (e.g., "gemini-1.5-pro", "gemini-1.5-flash")
            api_key: Google AI API key (defaults to GEMINI_API_KEY or GOOGLE_API_KEY env var)
        """
        self.model = model
        self.api_key = (
            api_key or 
            os.environ.get("GEMINI_API_KEY") or 
            os.environ.get("GOOGLE_API_KEY")
        )
        
        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GEMINI_API_KEY or GOOGLE_API_KEY "
                "environment variable or pass api_key parameter."
            )
        
        # Lazy import to avoid requiring google-generativeai package if not used
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.genai = genai
            self.client = genai.GenerativeModel(model)
        except ImportError:
            raise ImportError(
                "google-generativeai package required. Install with: "
                "pip install google-generativeai"
            )
    
    @property
    def name(self) -> str:
        return f"Gemini/{self.model}"
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate text using Google Gemini API.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        # Combine system prompt with user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"
        
        # Configure generation
        generation_config = self.genai.GenerationConfig(
            temperature=min(1.0, max(0.0, temperature)),
            max_output_tokens=max_tokens,
        )
        
        try:
            response = self.client.generate_content(
                full_prompt,
                generation_config=generation_config,
            )
            
            # Handle response
            if response.text:
                return response.text
            
            # Handle blocked or empty responses
            if response.prompt_feedback:
                if response.prompt_feedback.block_reason:
                    return ""
            
            return ""
            
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")
    
    def list_models(self) -> list:
        """List available Gemini models."""
        try:
            models = []
            for model in self.genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    models.append(model.name)
            return models
        except Exception:
            return [
                "gemini-1.5-flash",
                "gemini-1.5-pro", 
                "gemini-pro",
            ]
