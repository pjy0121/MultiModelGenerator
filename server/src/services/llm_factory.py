from typing import Dict, List, Optional
from .llm_client_interface import LLMClientInterface

from .openai_llm_client import OpenAIClient
from .google_llm_client import GoogleLLMClient
from .internal_llm_client import InternalLLMClient

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
            print("🔄 OpenAI 클라이언트 생성 중...")
            cls._clients["openai"] = OpenAIClient()
            print("✅ OpenAI 클라이언트 생성 완료")
        except Exception as e:
            print(f"❌ OpenAI 클라이언트 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            
        try:
            print("🔄 Google 클라이언트 생성 중...")
            cls._clients["google"] = GoogleLLMClient()
            print("✅ Google 클라이언트 생성 완료")
        except Exception as e:
            print(f"❌ Google 클라이언트 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            
        try:
            print("🔄 Internal LLM 클라이언트 생성 중...")
            cls._clients["internal"] = InternalLLMClient()
            print("✅ Internal LLM 클라이언트 생성 완료")
        except Exception as e:
            print(f"❌ Internal LLM 클라이언트 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            
        cls._initialized = True
    
    @classmethod
    def get_client(cls, provider: str) -> LLMClientInterface:
        """
        지정된 Provider의 클라이언트 반환
        
        Args:
            provider: LLM Provider 이름 (필수)
            
        Returns:
            LLM 클라이언트 인스턴스
        """
        cls._initialize_clients()
        
        if provider not in cls._clients:
            raise ValueError(f"지원하지 않는 LLM Provider: {provider}")
            
        client = cls._clients[provider]
        if not client.is_available():
            raise RuntimeError(f"{provider} 클라이언트를 사용할 수 없습니다. API 키를 확인하세요.")
            
        return client
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """사용 가능한 LLM Provider 목록 반환"""
        cls._initialize_clients()
        
        available = []
        for provider, client in cls._clients.items():
            if client.is_available():
                available.append(provider)
                
        return available