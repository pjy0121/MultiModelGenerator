"""Enum types for workflow models."""

from enum import Enum
from typing import Dict, List
from ..config import SEARCH_INTENSITY_CONFIG


class NodeType(str, Enum):
    INPUT = "input-node"
    GENERATION = "generation-node"
    ENSEMBLE = "ensemble-node"
    VALIDATION = "validation-node"
    CONTEXT = "context-node"
    OUTPUT = "output-node"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    INTERNAL = "internal"
    
    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """지원되는 LLM Provider 목록 반환"""
        return [cls.OPENAI, cls.GOOGLE, cls.INTERNAL]
    
    @classmethod
    def get_default_provider(cls) -> str:
        """기본 LLM Provider 반환"""
        return cls.GOOGLE


class SearchIntensity(str, Enum):
    EXACT = "exact"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    
    @classmethod
    def get_search_params(cls, intensity: str) -> Dict[str, any]:
        """검색 모드에 따른 파라미터 반환 (BGE-M3 실제 유사도 분포 기반)
        
        Top-K + Similarity Threshold 병행 필터링:
        1. init: 초기 검색 개수 (ChromaDB에서 가져오기)
        2. similarity_threshold: 최소 유사도 (cosine similarity 0.0~1.0)
        3. final: Reranker 적용 후 최종 개수
        
        임계값 설정 근거 (실측 데이터 기반):
        - BGE-M3 실제 유사도 범위: 관련 문서도 0.2~0.4 수준
        - 이론적 권장값(0.8/0.65/0.5)은 너무 높아 대부분 필터링됨
        - 실용적 값(0.3/0.25/0.2)으로 조정하여 적절한 검색 결과 확보
        
        - EXACT (고정밀 검색): init=10, final=5, threshold=0.3 (30%+ 유사도)
          사용 예: "정확한 명령어 ID", "특정 사양"
          특징: 명확히 관련된 문서만 선택
          
        - STANDARD (표준 검색): init=20, final=12, threshold=0.25 (25%+ 유사도) [기본값]
          사용 예: "일반적인 기능", "표준 절차"
          특징: 어느 정도 관련성 있는 문서 포함, 대부분의 경우 최적
          
        - COMPREHENSIVE (포괄 검색): init=40, final=25, threshold=0.2 (20%+ 유사도)
          사용 예: "전반적인 메커니즘", "탐색적 조사"
          특징: 약간이라도 관련 가능성 있는 모든 문서 포함
          
        * Similarity Threshold: 무관한 결과 필터링 (빈 결과 방지를 위해 최소 1개 반환)
        * Reranker 사용 시: threshold 후 init 결과를 final로 LLM 기반 재정렬
        * Reranker 미사용 시: threshold 필터링된 결과만 반환
        """
        intensity_map = {
            cls.EXACT: SEARCH_INTENSITY_CONFIG["exact"],
            cls.STANDARD: SEARCH_INTENSITY_CONFIG["standard"],
            cls.COMPREHENSIVE: SEARCH_INTENSITY_CONFIG["comprehensive"]
        }
        return intensity_map.get(intensity, intensity_map[cls.STANDARD])
    
    @classmethod
    def from_top_k(cls, top_k: int) -> str:
        """top_k 값을 기반으로 적절한 검색 모드 반환 (기준: final 개수)"""
        if top_k <= 12:
            return cls.EXACT
        elif top_k <= 30:
            return cls.STANDARD
        else:
            return cls.COMPREHENSIVE
    
    @classmethod
    def get_default(cls) -> str:
        """기본 검색 모드 반환 (균형잡힌 표준 검색)"""
        return cls.STANDARD
