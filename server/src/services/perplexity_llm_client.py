from typing import List, Dict, Any
from openai import OpenAI
from .llm_client_interface import LLMClientInterface
from ..core.models import AvailableModel
from ..core.config import Config

class PerplexityClient(LLMClientInterface):
    """Perplexity AI 클라이언트"""
    
    def __init__(self):
        """Perplexity 클라이언트 초기화"""
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """클라이언트 초기화"""
        try:
            if not Config.PERPLEXITY_API_KEY:
                raise ValueError("PERPLEXITY_API_KEY가 설정되지 않았습니다.")
                
            self.client = OpenAI(
                api_key=Config.PERPLEXITY_API_KEY,
                base_url=Config.PERPLEXITY_BASE_URL
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
        """Perplexity API 채팅 완성"""
        if not self.client:
            raise RuntimeError("Perplexity 클라이언트가 초기화되지 않았습니다.")
        
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
                    f"Perplexity API 인증 실패: {e}\n"
                    f"💡 해결 방법:\n"
                    f"1. .env 파일의 PERPLEXITY_API_KEY 확인\n"
                    f"2. API 키가 유효한지 확인\n"
                    f"3. 서버 재시작 후 다시 시도"
                )
                raise RuntimeError(error_msg)
            else:
                raise RuntimeError(f"Perplexity API 요청 실패: {e}")
    
    def is_available(self) -> bool:
        """클라이언트 사용 가능 여부 확인"""
        return self.client is not None and bool(Config.PERPLEXITY_API_KEY)
    
    def get_available_models(self) -> List[AvailableModel]:
        """Perplexity에서 지원하는 모델 목록"""
        # Perplexity는 API에서 모델 목록을 제공하지 않으므로 정적으로 반환
        is_available = self.is_available()
        models = [
            {
                "index": 0,
                "value": "sonar-pro",
                "label": "Sonar Pro",
                "provider": "perplexity",
                "model_type": "sonar-pro",
                "disabled": not is_available
            },
            {
                "index": 1,
                "value": "sonar-medium",
                "label": "Sonar Medium",
                "provider": "perplexity",
                "model_type": "sonar-medium", 
                "disabled": not is_available
            }
        ]
        
        return [AvailableModel(**model) for model in models]