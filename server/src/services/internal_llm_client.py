import os
import asyncio
from typing import List, Dict, Any
from openai import OpenAI
from .llm_client_interface import LLMClientInterface
from ..core.config import INTERNAL_LLM_CONFIG, NODE_EXECUTION_CONFIG

class InternalLLMClient(LLMClientInterface):
    """내부 LLM API 클라이언트 (OpenAI 패키지 사용)"""
    
    def __init__(self):
        """Internal LLM 클라이언트 초기화"""
        self.client = None
        self.model_name = INTERNAL_LLM_CONFIG.get("model_name", "internal-llm")
        self._initialize_client()
    
    def _initialize_client(self):
        """클라이언트 초기화"""
        try:
            api_key = INTERNAL_LLM_CONFIG.get("api_key")
            if not api_key:
                raise ValueError("INTERNAL_API_KEY가 설정되지 않았습니다.")
            
            api_endpoint = INTERNAL_LLM_CONFIG.get("api_endpoint")            
            if not api_endpoint:
                raise ValueError("INTERNAL_API_ENDPOINT가 설정되지 않았습니다.")            
            os.environ["NO_PROXY"] = api_endpoint.replace("https://", "").replace("http://", "")

            self.client = OpenAI(
                api_key=api_key,
                base_url=api_endpoint,
                timeout=INTERNAL_LLM_CONFIG.get("timeout", 30)
            )
        except Exception as e:
            print(f"Internal LLM 클라이언트 초기화 실패: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Internal LLM API 사용 가능 여부 확인"""
        return self.client is not None
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 모델 목록 반환 (단일 내부 모델)"""
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
        """스트리밍으로 응답 생성 (통합된 단일 인터페이스)"""
        if not self.client:
            raise RuntimeError("Internal LLM 클라이언트가 초기화되지 않았습니다.")
        
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
            raise RuntimeError(f"Internal LLM API 스트리밍 요청 실패: {e}")