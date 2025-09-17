from typing import List, Dict, Any
from openai import OpenAI
from .llm_client_interface import LLMClientInterface
from ..core.config import Config

class OpenAIClient(LLMClientInterface):
    """OpenAI API 클라이언트"""
    
    def __init__(self):
        """OpenAI 클라이언트 초기화"""
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """클라이언트 초기화"""
        try:
            if not Config.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
                
            self.client = OpenAI(
                api_key=Config.OPENAI_API_KEY
            )
        except Exception as e:
            self.client = None
    
    def chat_completion(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """OpenAI API 채팅 완성"""
        if not self.client:
            raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다.")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                error_msg = (
                    f"OpenAI API 인증 실패: {e}\n"
                    f"💡 해결 방법:\n"
                    f"1. .env 파일의 OPENAI_API_KEY 확인\n"
                    f"2. API 키가 유효한지 확인\n"
                    f"3. 서버 재시작 후 다시 시도"
                )
                raise RuntimeError(error_msg)
            else:
                raise RuntimeError(f"OpenAI API 요청 실패: {e}")
    
    def is_available(self) -> bool:
        """클라이언트 사용 가능 여부 확인"""
        return self.client is not None and bool(Config.OPENAI_API_KEY)
    
    async def chat_completion_stream(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.1,
        max_tokens: int = 2000
    ):
        """OpenAI API 스트리밍 채팅 완성"""
        if not self.client:
            raise RuntimeError("OpenAI 클라이언트가 초기화되지 않았습니다.")
        
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                error_msg = (
                    f"OpenAI API 인증 실패: {e}\n"
                    f"💡 해결 방법:\n"
                    f"1. .env 파일의 OPENAI_API_KEY 확인\n"
                    f"2. API 키가 유효한지 확인\n"
                    f"3. 서버 재시작 후 다시 시도"
                )
                raise RuntimeError(error_msg)
            else:
                raise RuntimeError(f"OpenAI API 스트리밍 요청 실패: {e}")
    
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