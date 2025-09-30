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
    동시 접근 문제 해결을 위해 인스턴스 캐싱과 연결 복구 기능 제공
    """
    
    def __init__(self):
        """VectorStoreService 초기화"""
        self._store_cache: Dict[str, VectorStore] = {}
    
    def get_vector_store(self, kb_name: str) -> VectorStore:
        """지식베이스별 VectorStore 인스턴스 반환 (캐싱됨)"""
        if kb_name not in self._store_cache:
            self._store_cache[kb_name] = VectorStore(kb_name)
        return self._store_cache[kb_name]
    
    async def get_knowledge_bases(self) -> List[str]:
        """사용 가능한 지식 베이스 목록 반환 (비동기)"""
        from ..core.config import get_kb_list
        return await get_kb_list()
    
    async def search(
        self,
        kb_name: str, 
        query: str, 
        search_intensity: str = "medium",
        rerank_info: Optional[Dict] = None
    ) -> List[str]:
        """벡터 검색 (VectorStore에 직접 위임, 에러 복구 포함)"""
        try:
            store = self.get_vector_store(kb_name)
            return await store.search(query, search_intensity, rerank_info)
        except Exception as e:
            print(f"⚠️ 검색 중 오류 발생 (KB: {kb_name}): {e}")
            # 캐시된 인스턴스 제거 후 재시도
            if kb_name in self._store_cache:
                print(f"🔄 VectorStore 인스턴스 재생성 시도: {kb_name}")
                del self._store_cache[kb_name]
                store = self.get_vector_store(kb_name)
                return await store.search(query, search_intensity, rerank_info)
            else:
                raise e
    
    async def get_knowledge_base_info(self, kb_name: str) -> Dict:
        """지식 베이스 정보 반환 (VectorStore에 위임, 에러 복구 포함)"""
        try:
            store = self.get_vector_store(kb_name)
            return await store.get_knowledge_base_info()
        except Exception as e:
            print(f"⚠️ KB 정보 조회 중 오류 발생 (KB: {kb_name}): {e}")
            # 캐시된 인스턴스 제거 후 재시도
            if kb_name in self._store_cache:
                print(f"🔄 VectorStore 인스턴스 재생성 시도: {kb_name}")
                del self._store_cache[kb_name]
                store = self.get_vector_store(kb_name)
                return await store.get_knowledge_base_info()
            else:
                raise e


# 전역 서비스 인스턴스
vector_store_service = VectorStoreService()