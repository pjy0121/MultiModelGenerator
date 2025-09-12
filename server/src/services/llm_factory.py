from typing import Dict, List, Optional
from .llm_client_interface import LLMClientInterface
from .perplexity_llm_client import PerplexityClient
from .openai_llm_client import OpenAIClient
from .google_llm_client import GoogleLLMClient

class LLMFactory:
    """LLM 클라이언트 팩토리"""
    
    _clients: Dict[str, LLMClientInterface] = {}
    _initialized = False
    
    @classmethod
    def _initialize_clients(cls):
        """모든 클라이언트 초기화"""
        if cls._initialized:
            return
            
        # 사용 가능한 클라이언트들 초기화
        try:
            cls._clients["perplexity"] = PerplexityClient()
        except Exception as e:
            print(f"⚠️ Perplexity 클라이언트 초기화 실패: {e}")
            
        try:
            cls._clients["openai"] = OpenAIClient()
        except Exception as e:
            print(f"⚠️ OpenAI 클라이언트 초기화 실패: {e}")
            
        try:
            cls._clients["google"] = GoogleLLMClient()
        except Exception as e:
            print(f"⚠️ Google AI 클라이언트 초기화 실패: {e}")
            
        cls._initialized = True
    
    @classmethod
    def get_client(cls, provider: str) -> LLMClientInterface:
        """
        지정된 제공자의 클라이언트 반환
        
        Args:
            provider: LLM 제공자 이름 (필수)
            
        Returns:
            LLM 클라이언트 인스턴스
        """
        cls._initialize_clients()
        
        if provider not in cls._clients:
            raise ValueError(f"지원하지 않는 LLM 제공자: {provider}")
            
        client = cls._clients[provider]
        if not client.is_available():
            raise RuntimeError(f"{provider} 클라이언트를 사용할 수 없습니다. API 키를 확인하세요.")
            
        return client
    
    @classmethod
    def get_client_for_model_id(cls, model_id: str) -> LLMClientInterface:
        """
        모델 ID에 기반해 적절한 클라이언트 반환
        
        Args:
            model_id: 실제 모델 ID (예: "gpt-4", "sonar-pro")
            
        Returns:
            LLM 클라이언트 인스턴스
        """
        cls._initialize_clients()
        
        # 모델 ID 기반으로 제공자 결정
        if model_id.startswith("gpt-"):
            provider = "openai"
        elif model_id.startswith("sonar-"):
            provider = "perplexity"
        elif model_id.startswith("gemini-") or model_id.startswith("gemma-") or model_id.startswith("learnlm-"):
            provider = "google"
        else:
            # 알 수 없는 모델인 경우 에러 발생
            raise ValueError(f"알 수 없는 모델 ID: {model_id}. 지원하는 모델을 사용하세요.")
        
        if provider not in cls._clients:
            raise ValueError(f"지원하지 않는 LLM 제공자: {provider}")
            
        client = cls._clients[provider]
        if not client.is_available():
            raise RuntimeError(f"{provider} 클라이언트를 사용할 수 없습니다.")
            
        return client

    @classmethod
    def get_client_for_model(cls, model_name: str, provider: str = None) -> LLMClientInterface:
        """
        모델 이름과 프로바이더에 맞는 클라이언트 반환
        
        Args:
            model_name: 사용할 모델 이름
            provider: LLM 프로바이더 (지정하면 해당 프로바이더 클라이언트만 사용)
            
        Returns:
            해당 모델을 지원하는 LLM 클라이언트
        """
        cls._initialize_clients()
        
        # 프로바이더가 지정된 경우 해당 클라이언트만 사용
        if provider:
            if provider not in cls._clients:
                raise ValueError(f"지원하지 않는 LLM 제공자: {provider}")
            
            client = cls._clients[provider]
            if not client.is_available():
                raise RuntimeError(f"{provider} 클라이언트를 사용할 수 없습니다. API 키를 확인하세요.")
            return client
        
        # 프로바이더가 지정되지 않은 경우 기존 로직 (모든 클라이언트에서 검색)
        for provider_name, client in cls._clients.items():
            if client.is_available():
                # 각 클라이언트의 available_models에서 model_type으로 찾기
                available_models = client.get_available_models()
                for model in available_models:
                    if model.model_type == model_name and not model.disabled:
                        return client
                
        # 지원하는 클라이언트가 없는 경우
        available_providers = [p for p, c in cls._clients.items() if c.is_available()]
        if not available_providers:
            raise ValueError(f"사용 가능한 LLM 클라이언트가 없습니다. API 키를 확인하세요.")
        else:
            raise ValueError(f"모델 '{model_name}'을 지원하는 사용 가능한 클라이언트가 없습니다. 사용 가능한 제공자: {available_providers}")
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """사용 가능한 LLM 제공자 목록 반환"""
        cls._initialize_clients()
        
        available = []
        for provider, client in cls._clients.items():
            if client.is_available():
                available.append(provider)
                
        return available
    
    @classmethod 
    def get_client_by_provider(cls, provider: str) -> Optional[LLMClientInterface]:
        """Provider 이름으로 클라이언트 반환"""
        cls._initialize_clients()
        return cls._clients.get(provider)