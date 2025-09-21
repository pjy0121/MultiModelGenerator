from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Union, Optional


class LLMClientInterface(ABC):
    """Base interface for all LLM client implementations."""
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider."""
        pass
    
    @abstractmethod
    async def generate_response(
        self, 
        prompt: str, 
        model: str, 
        temperature: float = 0.3, 
        max_tokens: int = 2000,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Generate response from the LLM."""
        pass
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        model: str, 
        temperature: float = 0.3, 
        max_tokens: int = 2000,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Alternative interface for generating responses (used by rerank)."""
        pass
    
    @abstractmethod
    def get_model_context_length(self, model: str) -> int:
        """Get the maximum context length for a specific model."""
        pass