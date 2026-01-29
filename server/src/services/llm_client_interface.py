from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator
from ..config import NODE_EXECUTION_CONFIG


class LLMClientInterface(ABC):
    """Unified LLM client interface - streaming only"""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if client is available"""
        pass

    @abstractmethod
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Return list of available models"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = NODE_EXECUTION_CONFIG["max_tokens_default"]
    ) -> AsyncGenerator[str, None]:
        """Generate response via streaming (unified single interface)"""
        pass