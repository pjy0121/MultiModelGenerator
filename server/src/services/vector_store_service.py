"""
VectorStoreService - VectorStore 인스턴스들을 관리하는 단순한 wrapper 서비스
"""

from typing import List, Dict, Optional
from .vector_store import VectorStore
from ..core.config import NODE_EXECUTION_CONFIG, get_kb_list


class VectorStoreService:
    """
    VectorStore 인스턴스들을 관리하는 단순한 wrapper 서비스
    실제 구현은 VectorStore 클래스에 위임
    """
    
    def __init__(self):
        """VectorStoreService 초기화"""
        self._store_cache: Dict[str, VectorStore] = {}
    
    def get_vector_store(self, kb_name: str) -> VectorStore:
        """지식베이스별 VectorStore 인스턴스 반환 (캐싱됨)"""
        if kb_name not in self._store_cache:
            self._store_cache[kb_name] = VectorStore(kb_name)
        return self._store_cache[kb_name]
    
    def get_knowledge_bases(self) -> List[str]:
        """사용 가능한 지식 베이스 목록 반환"""
        return get_kb_list()
    
    async def search(
        self,
        kb_name: str, 
        query: str, 
        search_intensity: str = "medium",
        rerank_info: Optional[Dict] = None
    ) -> List[str]:
        """벡터 검색 (VectorStore에 직접 위임)"""
        store = self.get_vector_store(kb_name)
        return await store.search(query, search_intensity, rerank_info)
    
    async def get_knowledge_base_info(self, kb_name: str) -> Dict:
        """지식 베이스 정보 반환 (VectorStore에 위임)"""
        store = self.get_vector_store(kb_name)
        return await store.get_knowledge_base_info()


# 전역 서비스 인스턴스
vector_store_service = VectorStoreService()