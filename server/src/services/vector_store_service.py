"""
VectorStoreService - VectorStore 인스턴스들을 관리하는 단순한 wrapper 서비스
"""

from typing import List, Dict, Optional
from .vector_store import VectorStore
from ..core.config import NODE_EXECUTION_CONFIG
from ..core.utils import get_kb_list


class VectorStoreService:
    """
    VectorStore 인스턴스들을 관리하는 단순한 wrapper 서비스
    실제 구현은 VectorStore 클래스에 위임
    동시 접근 문제 해결을 위해 인스턴스 캐싱과 연결 복구 기능 제공
    """
    
    def __init__(self):
        """VectorStoreService 초기화 (인스턴스별 독립 캐시)"""
        self._store_cache: Dict[str, VectorStore] = {}
    
    def get_vector_store(self, kb_name: str) -> VectorStore:
        """지식베이스별 VectorStore 인스턴스 반환 (인스턴스별 캐시)"""
        if kb_name not in self._store_cache:
            self._store_cache[kb_name] = VectorStore(kb_name)
        return self._store_cache[kb_name]
    
    async def get_knowledge_bases(self) -> List[str]:
        """사용 가능한 지식 베이스 목록 반환 (비동기)"""
        return await get_kb_list()
    
    async def search(
        self,
        kb_name: str, 
        query: str, 
        search_intensity: str = "standard",
        rerank_info: Optional[Dict] = None
    ) -> Dict:
        """벡터 검색 (VectorStore에 직접 위임, 에러 복구 포함)
        
        Returns:
            Dict with 'chunks', 'total_chunks', 'found_chunks'
        """
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
    
    def close_and_remove_kb(self, kb_name: str):
        """특정 KB의 VectorStore 연결을 닫고 캐시에서 제거 (삭제/이름 변경 전 호출)"""
        if kb_name in self._store_cache:
            try:
                store = self._store_cache[kb_name]
                store.close()  # ChromaDB 연결 닫기
                del self._store_cache[kb_name]
                print(f"✅ VectorStore '{kb_name}' 캐시에서 제거됨")
            except Exception as e:
                print(f"⚠️ VectorStore '{kb_name}' 제거 중 오류: {e}")
                # 오류가 발생해도 캐시에서는 제거
                if kb_name in self._store_cache:
                    del self._store_cache[kb_name]
    
    def close_all(self):
        """모든 VectorStore 연결 닫기 (서버 종료 시 호출)"""
        for kb_name, store in list(self._store_cache.items()):
            try:
                store.close()
                print(f"✅ VectorStore '{kb_name}' 연결 닫힘")
            except Exception as e:
                print(f"⚠️ VectorStore '{kb_name}' 닫기 중 오류: {e}")
        self._store_cache.clear()


# 전역 인스턴스 제거 - 각 요청별로 독립적인 인스턴스 사용
# vector_store_service = VectorStoreService()  # 제거됨