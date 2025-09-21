"""
VectorStoreService - 여러 VectorStore 인스턴스를 관리하는 서비스 레이어
ChromaDB 클라이언트 공유로 병렬 접근 최적화
"""

import os
import asyncio
import chromadb
from typing import List, Dict, Optional
from ..core.config import get_kb_path, VECTOR_DB_CONFIG
from .rerank import ReRanker


class VectorStoreService:
    """
    ChromaDB 클라이언트 공유를 통한 병렬 검색 최적화 서비스
    각 지식베이스별로 하나의 클라이언트를 공유하여 병렬 read 접근 지원
    """
    
    def __init__(self):
        """VectorStoreService 초기화"""
        self.clients: Dict[str, chromadb.PersistentClient] = {}
        self._lock = asyncio.Lock()  # 클라이언트 생성 시 동기화

    async def get_client(self, kb_name: str) -> chromadb.PersistentClient:
        """지식베이스별 ChromaDB 클라이언트 반환 (캐싱됨)"""
        if kb_name not in self.clients:
            async with self._lock:
                # Double-check locking pattern
                if kb_name not in self.clients:
                    db_path = get_kb_path(kb_name)
                    os.makedirs(db_path, exist_ok=True)
                    self.clients[kb_name] = chromadb.PersistentClient(path=db_path)
        
        return self.clients[kb_name]

    async def get_collection(self, kb_name: str):
        """지식베이스의 컬렉션 반환 - 매번 새로 가져와서 병렬 접근 지원"""
        try:
            client = await self.get_client(kb_name)
            # 매번 새로 컬렉션을 가져와서 병렬 접근 허용
            collection = client.get_or_create_collection(
                name="spec_documents",
                metadata={"hnsw:space": "cosine"}
            )
            return collection
        except Exception as e:
            print(f"컬렉션 조회 실패 ({kb_name}): {e}")
            return None

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
    

    
    async def get_knowledge_base_info(self, kb_name: str) -> Dict:
        """지정된 지식 베이스의 상세 정보 반환"""
        try:
            collection = await self.get_collection(kb_name)
            if collection:
                count = collection.count()
                return {
                    'name': kb_name,
                    'exists': True,
                    'chunk_count': count,
                    'path': get_kb_path(kb_name),
                    'created_at': 'Unknown'
                }
            else:
                return {
                    'name': kb_name,
                    'exists': False,
                    'chunk_count': 0,
                    'path': get_kb_path(kb_name),
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
        """
        병렬 검색 최적화된 통합 검색 메서드
        각 호출마다 새로운 컬렉션 객체를 사용하여 진정한 병렬 접근 지원
        """
        try:
            # 매번 새로운 컬렉션 객체 - 병렬 접근 가능
            collection = await self.get_collection(kb_name)
            if not collection:
                return []

            # 검색 강도 설정
            search_params = VECTOR_DB_CONFIG["search_intensity_map"].get(
                search_intensity, 
                VECTOR_DB_CONFIG["search_intensity_map"]["medium"]
            )
            
            # 초기 벡터 검색
            initial_results = await self._search_initial_chunks(
                collection, query, search_params["init"]
            )
            
            if not initial_results:
                return []
            
            # 리랭킹 처리
            if rerank_info:
                return await self._search_with_rerank(
                    query, initial_results, search_params["final"], rerank_info
                )
            else:
                return initial_results[:search_params["final"]]
                
        except Exception as e:
            raise Exception(f"Knowledge base search failed for {kb_name}: {str(e)}")

    async def _search_initial_chunks(self, collection, query: str, top_k: int) -> List[str]:
        """초기 벡터 검색 수행"""
        try:
            collection_count = collection.count()
            if collection_count == 0:
                return []

            actual_top_k = min(top_k, collection_count)
            
            results = collection.query(
                query_texts=[query],
                n_results=actual_top_k,
                include=['documents', 'distances']
            )
            
            if not results['documents'] or not results['documents'][0]:
                return []

            chunks = results['documents'][0]
            distances = results['distances'][0] if results['distances'] else []
            
            # 유사도 임계값 필터링
            filtered_chunks = [
                chunk for chunk, distance in zip(chunks, distances)
                if distance <= VECTOR_DB_CONFIG["similarity_threshold"]
            ]
            
            return filtered_chunks

        except Exception as e:
            print(f"⚠️ 초기 검색 중 오류 발생: {e}")
            return []

    async def _search_with_rerank(
        self, 
        query: str, 
        initial_chunks: List[str], 
        top_k_final: int,
        rerank_info: Dict[str, str]
    ) -> List[str]:
        """리랭킹을 사용한 검색"""
        try:
            reranker = ReRanker(
                provider=rerank_info["provider"], 
                model=rerank_info["model"]
            )
            return await reranker.rerank_documents(query, initial_chunks, top_k_final)
        except Exception as e:
            print(f"⚠️ 재정렬 중 오류 발생: {e}. 초기 검색 결과의 일부를 반환합니다.")
            return initial_chunks[:top_k_final]