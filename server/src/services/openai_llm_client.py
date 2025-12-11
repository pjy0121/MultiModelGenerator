import asyncio
from typing import List, Dict, Any
from openai import OpenAI
from .llm_client_interface import LLMClientInterface
from ..config import API_KEYS, NODE_EXECUTION_CONFIG

class OpenAIClient(LLMClientInterface):
    """OpenAI API 클라이언트"""
    
    def __init__(self):
        """OpenAI 클라이언트 초기화"""
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """클라이언트 초기화"""
        try:
            if not API_KEYS["openai"]:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
                
            self.client = OpenAI(
                api_key=API_KEYS["openai"]
            )
        except Exception as e:
            self.client = None
    
    def is_available(self) -> bool:
        """OpenAI API 사용 가능 여부 확인"""
        return self.client is not None and bool(API_KEYS["openai"])

    def get_available_models(self) -> List[Dict[str, Any]]:
        """OpenAI API에서 실제 사용 가능한 모델 목록 가져오기"""
        if not self.is_available():
            return []
        
        try:
            models = self.client.models.list()
            available_models = []
            
            # GPT 모델들만 필터링 (채팅 완성용 모델들)
            chat_model_prefixes = ["gpt-3.5", "gpt-4"]
            
            for model in models.data:
                model_id = model.id
                # 채팅 완성에 사용할 수 있는 모델들만 포함
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
        """스트리밍으로 응답 생성 (통합된 단일 인터페이스)"""
        if not self.client:
            raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다.")
        
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
            # OpenAI 라이브러리의 정확한 에러 타입 처리
            from openai import AuthenticationError, APIError, RateLimitError
            
            if isinstance(e, AuthenticationError):
                error_msg = (
                    f"OpenAI API 인증 실패: {e}\n"
                    f"💡 해결 방법:\n"
                    f"1. .env 파일의 OPENAI_API_KEY 확인\n"
                    f"2. API 키가 유효한지 확인\n"
                    f"3. 서버 재시작 후 다시 시도"
                )
                raise RuntimeError(error_msg)
            elif isinstance(e, RateLimitError):
                raise RuntimeError(f"OpenAI API 사용량 초과: {e}")
            elif isinstance(e, APIError):
                raise RuntimeError(f"OpenAI API 오류: {e}")
            else:
                raise RuntimeError(f"OpenAI API 스트리밍 요청 실패: {e}")
