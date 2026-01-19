"""
Ollama LLM Provider

Supports local models via Ollama (Llama, Mistral, CodeLlama, etc.)
"""

import os
from typing import Optional

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    """
    Ollama provider for local model inference.
    
    Supports any model available through Ollama:
    - llama2, llama3
    - codellama
    - mistral, mixtral
    - phi, phi3
    - etc.
    
    Requires Ollama to be running locally.
    """
    
    def __init__(
        self,
        model: str = "llama3",
        host: str = "http://localhost:11434",
    ):
        """
        Initialize the Ollama provider.
        
        Args:
            model: The model to use (e.g., "llama3", "codellama", "mistral")
            host: Ollama API host URL
        """
        self.model = model
        self.host = host
        
        # Lazy import
        try:
            import httpx
            self.httpx = httpx
        except ImportError:
            raise ImportError(
                "httpx package required. Install with: pip install httpx"
            )
    
    @property
    def name(self) -> str:
        return f"Ollama/{self.model}"
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate text using Ollama API.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Use the generate endpoint for simplicity
        url = f"{self.host}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        try:
            response = self.httpx.post(
                url,
                json=payload,
                timeout=120.0,  # Longer timeout for local models
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("response", "")
            
        except self.httpx.HTTPError as e:
            raise RuntimeError(
                f"Ollama API error: {e}. "
                "Make sure Ollama is running with: ollama serve"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Ollama: {e}")
    
    def list_models(self) -> list:
        """List available models in Ollama."""
        url = f"{self.host}/api/tags"
        
        try:
            response = self.httpx.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []
    
    def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama library."""
        url = f"{self.host}/api/pull"
        
        try:
            response = self.httpx.post(
                url,
                json={"name": model},
                timeout=600.0,  # Long timeout for model downloads
            )
            return response.status_code == 200
        except Exception:
            return False
