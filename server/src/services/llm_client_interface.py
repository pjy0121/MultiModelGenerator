from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..core.models import AvailableModel

class LLMClientInterface(ABC):
    """LLM 클라이언트 추상 인터페이스"""
    
    @abstractmethod
    def chat_completion(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """
        채팅 완성 요청
        
        Args:
            model: 모델 이름
            messages: 메시지 리스트 [{"role": "user", "content": "..."}]
            temperature: 창의성 수준 (0.0 ~ 1.0)
            max_tokens: 최대 토큰 수
            
        Returns:
            생성된 텍스트
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        클라이언트 사용 가능 여부 확인
        
        Returns:
            사용 가능하면 True, 아니면 False
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[AvailableModel]:
        """
        사용 가능한 모델 목록 반환 (UI 표시용 메타데이터 포함)
        
        Returns:
            AvailableModel 객체 리스트
        """
        pass