from typing import Dict, List, Optional
from .llm_client_interface import LLMClientInterface

from .openai_llm_client import OpenAIClient
from .google_llm_client import GoogleLLMClient
from .internal_llm_client import InternalLLMClient

class LLMFactory:
    """LLM 클라이언트 팩토리 (인스턴스 기반 완전 병렬 버전)"""
    
    def __init__(self):
        """인스턴스별 독립적 클라이언트 생성"""
        self.clients: Dict[str, LLMClientInterface] = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """인스턴스별 클라이언트 초기화 (블로킹 없는 병렬 처리)"""
            
        # 각 인스턴스마다 독립적 클라이언트 생성
        try:
            self.clients["openai"] = OpenAIClient()
        except Exception:
            pass  # 조용히 실패 처리
            
        try:
            self.clients["google"] = GoogleLLMClient()
        except Exception:
            pass  # 조용히 실패 처리
            
        try:
            self.clients["internal"] = InternalLLMClient()
        except Exception:
            pass  # 조용히 실패 처리
    
    def get_client(self, provider: str) -> LLMClientInterface:
        """
        지정된 Provider의 클라이언트 반환 (인스턴스 기반 완전 병렬)
        
        Args:
            provider: LLM Provider 이름 (필수)
            
        Returns:
            LLM 클라이언트 인스턴스
        """
        if provider not in self.clients:
            raise ValueError(f"지원하지 않는 LLM Provider: {provider}")
            
        client = self.clients[provider]
        if not client.is_available():
            raise RuntimeError(f"{provider} 클라이언트를 사용할 수 없습니다. API 키를 확인하세요.")
            
        return client
    
    def get_available_providers(self) -> List[str]:
        """사용 가능한 LLM Provider 목록 반환 (인스턴스 기반)"""
        available = []
        for provider, client in self.clients.items():
            if client.is_available():
                available.append(provider)
                
        return available