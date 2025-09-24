from typing import List, Dict, Any, AsyncGenerator, Union
import asyncio
import json
from openai import OpenAI
from .llm_client_interface import LLMClientInterface
from ..core.config import INTERNAL_LLM_CONFIG

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
            api_endpoint = INTERNAL_LLM_CONFIG.get("api_endpoint")
            api_key = INTERNAL_LLM_CONFIG.get("api_key")
            
            if not api_endpoint:
                raise ValueError("INTERNAL_API_ENDPOINT가 설정되지 않았습니다.")
            if not api_key:
                raise ValueError("INTERNAL_API_KEY가 설정되지 않았습니다.")
                
            self.client = OpenAI(
                api_key=api_key,
                base_url=api_endpoint
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
    
    async def generate_response(
        self, 
        prompt: str, 
        model: str, 
        temperature: float = 0.3, 
        max_tokens: int = 2000,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Internal LLM을 사용하여 응답 생성"""
        if not self.is_available():
            raise Exception("Internal LLM API가 사용 불가능합니다.")
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            if stream:
                return self._generate_stream_response(messages, model, temperature, max_tokens)
            else:
                response = self.client.chat.completions.create(
                    model=self.model_name,  # 내부 모델명 사용
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                if response.choices and response.choices[0].message:
                    return response.choices[0].message.content.strip()
                else:
                    raise Exception("Internal LLM에서 빈 응답을 받았습니다.")
                    
        except Exception as e:
            raise Exception(f"Internal LLM 응답 생성 실패: {str(e)}")
    
    async def _generate_stream_response(
        self, 
        messages: List[Dict[str, Any]], 
        model: str, 
        temperature: float, 
        max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """스트리밍 응답 생성"""
        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
                        await asyncio.sleep(0.01)  # 작은 지연으로 부드러운 스트리밍
                        
        except Exception as e:
            raise Exception(f"Internal LLM 스트리밍 응답 생성 실패: {str(e)}")
    
    async def generate(
        self, 
        prompt: str, 
        model: str, 
        temperature: float = 0.3, 
        max_tokens: int = 2000,
        stream: bool = False
    ) -> str:
        """rerank에서 사용하는 generate 메서드"""
        return await self.generate_response(prompt, model, temperature, max_tokens, stream)