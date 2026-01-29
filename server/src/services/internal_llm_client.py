import os
import asyncio
from typing import List, Dict, Any
from openai import OpenAI
from .llm_client_interface import LLMClientInterface
from ..config import INTERNAL_LLM_CONFIG, NODE_EXECUTION_CONFIG

class InternalLLMClient(LLMClientInterface):
    """Internal LLM API client (using OpenAI package)"""

    def __init__(self):
        """Initialize Internal LLM client"""
        self.client = None
        self.model_name = INTERNAL_LLM_CONFIG.get("model_name", "internal-llm")
        self._initialize_client()

    def _initialize_client(self):
        """Initialize client"""
        try:
            api_key = INTERNAL_LLM_CONFIG.get("api_key")
            if not api_key:
                raise ValueError("INTERNAL_API_KEY is not configured.")

            api_endpoint = INTERNAL_LLM_CONFIG.get("api_endpoint")
            if not api_endpoint:
                raise ValueError("INTERNAL_API_ENDPOINT is not configured.")            
            os.environ["NO_PROXY"] = api_endpoint.replace("https://", "").replace("http://", "")

            self.client = OpenAI(
                api_key=api_key,
                base_url=api_endpoint,
                timeout=INTERNAL_LLM_CONFIG.get("timeout", 30)
            )
        except Exception as e:
            print(f"Internal LLM client initialization failed: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Check if Internal LLM API is available"""
        return self.client is not None

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Return list of available models (single internal model)"""
        if not self.is_available():
            return []
            
        return [{
            "value": self.model_name,
            "label": self.model_name,
            "provider": "internal",
            "model_type": self.model_name,
            "disabled": False
        }]
    
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = NODE_EXECUTION_CONFIG["max_tokens_default"]
    ):
        """Generate response via streaming (unified single interface)"""
        if not self.client:
            raise RuntimeError("Internal LLM client is not initialized.")
        
        try:
            messages = [{"role": "user", "content": prompt}]
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content is not None:
                    yield content
                    await asyncio.sleep(0.01)
                    
        except Exception as e:
            raise RuntimeError(f"Internal LLM API streaming request failed: {e}")