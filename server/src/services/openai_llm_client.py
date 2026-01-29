import asyncio
from typing import List, Dict, Any
from openai import OpenAI
from .llm_client_interface import LLMClientInterface
from ..config import API_KEYS, NODE_EXECUTION_CONFIG

class OpenAIClient(LLMClientInterface):
    """OpenAI API client"""

    def __init__(self):
        """Initialize OpenAI client"""
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize client"""
        try:
            if not API_KEYS["openai"]:
                raise ValueError("OPENAI_API_KEY is not configured.")
                
            self.client = OpenAI(
                api_key=API_KEYS["openai"]
            )
        except Exception as e:
            self.client = None
    
    def is_available(self) -> bool:
        """Check if OpenAI API is available"""
        return self.client is not None and bool(API_KEYS["openai"])

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of actually available models from OpenAI API"""
        if not self.is_available():
            return []
        
        try:
            models = self.client.models.list()
            available_models = []
            
            # Filter only GPT models (chat completion models)
            chat_model_prefixes = ["gpt-3.5", "gpt-4"]

            for model in models.data:
                model_id = model.id
                # Include only models that can be used for chat completion
                if any(model_id.startswith(prefix) for prefix in chat_model_prefixes):
                    model_info = {
                        "value": model_id,
                        "label": model_id,
                        "provider": "openai",
                        "model_type": model_id,
                        "disabled": False
                    }
                    available_models.append(model_info)
                
            return available_models
            
        except Exception as e:
            return []
    
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = NODE_EXECUTION_CONFIG["max_tokens_default"]
    ):
        """Generate response via streaming (unified single interface)"""
        if not self.client:
            raise RuntimeError("OpenAI client is not initialized.")
        
        try:
            messages = [{"role": "user", "content": prompt}]
            stream = self.client.chat.completions.create(
                model=model,
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
            # Handle exact error types from OpenAI library
            from openai import AuthenticationError, APIError, RateLimitError

            if isinstance(e, AuthenticationError):
                error_msg = (
                    f"OpenAI API authentication failed: {e}\n"
                    f"💡 Solutions:\n"
                    f"1. Check OPENAI_API_KEY in .env file\n"
                    f"2. Verify API key is valid\n"
                    f"3. Restart server and try again"
                )
                raise RuntimeError(error_msg)
            elif isinstance(e, RateLimitError):
                raise RuntimeError(f"OpenAI API rate limit exceeded: {e}")
            elif isinstance(e, APIError):
                raise RuntimeError(f"OpenAI API error: {e}")
            else:
                raise RuntimeError(f"OpenAI API streaming request failed: {e}")
