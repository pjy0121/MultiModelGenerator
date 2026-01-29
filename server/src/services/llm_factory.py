from typing import Dict, List, Optional
from .llm_client_interface import LLMClientInterface

from .openai_llm_client import OpenAIClient
from .google_llm_client import GoogleLLMClient
from .internal_llm_client import InternalLLMClient

class LLMFactory:
    """LLM client factory (instance-based fully parallel version)"""

    def __init__(self):
        """Create independent client per instance"""
        self.clients: Dict[str, LLMClientInterface] = {}
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize clients per instance (non-blocking parallel processing)"""

        # Create independent client for each instance
        try:
            self.clients["openai"] = OpenAIClient()
        except Exception:
            pass  # Silently handle failure

        try:
            self.clients["google"] = GoogleLLMClient()
        except Exception:
            pass  # Silently handle failure

        try:
            self.clients["internal"] = InternalLLMClient()
        except Exception:
            pass  # Silently handle failure

    def get_client(self, provider: str) -> LLMClientInterface:
        """
        Return client for specified provider (instance-based fully parallel)

        Args:
            provider: LLM Provider name (required)

        Returns:
            LLM client instance
        """
        if provider not in self.clients:
            raise ValueError(f"Unsupported LLM Provider: {provider}")

        client = self.clients[provider]
        if not client.is_available():
            raise RuntimeError(f"{provider} client is not available. Please check your API key.")

        return client

    def get_available_providers(self) -> List[str]:
        """Return list of available LLM providers (instance-based)"""
        available = []
        for provider, client in self.clients.items():
            if client.is_available():
                available.append(provider)
                
        return available