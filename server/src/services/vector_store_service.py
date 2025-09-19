"""
VectorStoreService - 여러 VectorStore 인스턴스를 관리하는 서비스 레이어
"""

import os
from typing import List, Dict, Optional
from .vector_store import VectorStore


class VectorStoreService:
    """노드 기반 워크플로우를 위한 벡터 스토어 서비스"""
    
    def __init__(self):
        """VectorStoreService 초기화"""
        self.vector_stores: Dict[str, VectorStore] = {}

    def get_vector_store(self, kb_name: str) -> VectorStore:
        """지정된 지식 베이스에 대한 VectorStore 인스턴스를 반환합니다 (캐싱 사용)"""
        if kb_name not in self.vector_stores:
            self.vector_stores[kb_name] = VectorStore(kb_name)
        return self.vector_stores[kb_name]
    
    def get_knowledge_bases(self) -> List[str]:
        """사용 가능한 지식 베이스 목록 반환"""
        try:
            kb_base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge_bases')
            if not os.path.exists(kb_base_path):
                return []
            
            knowledge_bases = []
            for item in os.listdir(kb_base_path):
                item_path = os.path.join(kb_base_path, item)
                if os.path.isdir(item_path):
                    knowledge_bases.append(item)
            
            return knowledge_bases
            
        except Exception as e:
            print(f"지식 베이스 목록 조회 실패: {e}")
            return []
    
    def list_knowledge_bases(self) -> List[str]:
        """사용 가능한 지식 베이스 목록 반환 (alias for get_knowledge_bases)"""
        return self.get_knowledge_bases()
    
    def get_collection(self, kb_name: str):
        """지정된 지식 베이스의 컬렉션 반환"""
        try:
            vector_store = self.get_vector_store(kb_name)
            return vector_store.collection
        except Exception as e:
            print(f"컬렉션 조회 실패 ({kb_name}): {e}")
            return None
    
    def get_knowledge_base_info(self, kb_name: str) -> Dict:
        """지정된 지식 베이스의 상세 정보 반환"""
        try:
            vector_store = self.get_vector_store(kb_name)
            status = vector_store.get_status()
            return {
                'name': kb_name,
                'exists': status.get('exists', False),
                'chunk_count': status.get('count', 0),
                'path': status.get('path', ''),
                'created_at': 'Unknown'
            }
        except Exception as e:
            print(f"지식 베이스 정보 조회 실패 ({kb_name}): {e}")
            return {
                'name': kb_name,
                'exists': False,
                'chunk_count': 0,
                'path': '',
                'created_at': 'Unknown'
            }
    
    async def search(
        self,
        kb_name: str,
        query: str,
        search_intensity: str = "medium",
        rerank_info: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """통합 검색 메서드 - VectorStoreService 레벨에서 검색 처리"""
        try:
            vector_store = self.get_vector_store(kb_name)
            return await vector_store.search(
                query=query,
                search_intensity=search_intensity,
                rerank_info=rerank_info
            )
        except Exception as e:
            raise Exception(f"Knowledge base search failed for {kb_name}: {str(e)}")