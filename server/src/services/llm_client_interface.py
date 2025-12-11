from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator
from ..config import NODE_EXECUTION_CONFIG


class LLMClientInterface(ABC):
    """통합된 LLM 클라이언트 인터페이스 - 스트리밍 전용"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """클라이언트 사용 가능 여부 확인"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[Dict[str, Any]]:
        """사용 가능한 모델 목록 반환"""
        pass
    
    @abstractmethod
    async def generate_stream(
        self, 
        prompt: str, 
        model: str, 
        temperature: float = 0.3, 
        max_tokens: int = NODE_EXECUTION_CONFIG["max_tokens_default"]
    ) -> AsyncGenerator[str, None]:
        """스트리밍으로 응답 생성 (통합된 단일 인터페이스)"""
        pass