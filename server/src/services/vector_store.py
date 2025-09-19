import chromadb
import os
from typing import List, Dict, Optional
from ..core.config import Config
from .rerank import ReRanker

class VectorStore:
    def __init__(self, kb_name: str):
        self.kb_name = kb_name
        self.db_path = Config.get_kb_path(kb_name)
        
        # 지식 베이스 디렉토리 생성
        os.makedirs(self.db_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(
            name="spec_documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    def store_chunks(self, chunks: List[Dict]) -> None:
        """청크들을 벡터 DB에 저장"""
        print(f"💾 지식 베이스 '{self.kb_name}'에 {len(chunks)}개 청크 저장 중...")
        
        # 기존 데이터 삭제 (새로 저장하는 경우)
        try:
            self.collection.delete()
            self.collection = self.client.get_or_create_collection(
                name="spec_documents",
                metadata={"hnsw:space": "cosine"}
            )
        except:
            pass
        
        ids = [f"chunk_{chunk['id']}" for chunk in chunks]
        documents = [chunk['content'] for chunk in chunks]
        embeddings = [chunk['embedding'] for chunk in chunks]
        metadatas = [{'length': chunk['length'], 'chunk_id': chunk['id']} for chunk in chunks]
        
        # 배치 크기로 나누어 저장 (ChromaDB 제한)
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            end_idx = min(i + batch_size, len(chunks))
            
            self.collection.add(
                ids=ids[i:end_idx],
                documents=documents[i:end_idx],
                embeddings=embeddings[i:end_idx],
                metadatas=metadatas[i:end_idx]
            )
        
        print(f"✅ 지식 베이스 '{self.kb_name}' 저장 완료!")

    async def _search_initial_chunks(self, query: str, top_k: int) -> List[str]:
        """초기 벡터 검색을 수행하는 내부 헬퍼 함수"""
        print(f"🔍 지식 베이스 '{self.kb_name}'에서 키워드 '{query}' 초기 검색 중... (top_k={top_k})")
        
        try:
            collection_count = self.collection.count()
            if collection_count == 0:
                print("❌ 지식 베이스가 비어있습니다.")
                return []
            
            actual_top_k = min(top_k, collection_count)
            
            results = self.collection.query(
                query_texts=[query],
                n_results=actual_top_k,
                include=['documents', 'distances']
            )
            
            if not results['documents'] or not results['documents'][0]:
                print("❌ 관련 문서를 찾지 못했습니다.")
                return []

            initial_chunks = results['documents'][0]
            distances = results['distances'][0] if results['distances'] else []
            
            filtered_chunks = [
                chunk for chunk, distance in zip(initial_chunks, distances)
                if distance <= Config.SEARCH_SIMILARITY_THRESHOLD
            ]
            
            print(f"📚 1차 필터링 후 {len(filtered_chunks)}개 관련 청크 발견.")
            return filtered_chunks

        except Exception as e:
            print(f"⚠️ 초기 검색 중 오류 발생: {e}")
            return []

    async def search_with_rerank(
        self, 
        query: str, 
        search_intensity: str,
        rerank_provider: str,
        rerank_model: str
    ) -> List[str]:
        """유사한 청크 검색 후 LLM으로 재정렬합니다."""
        search_params = Config.SEARCH_INTENSITY_MAP.get(search_intensity, Config.SEARCH_INTENSITY_MAP["medium"])
        top_k_init = search_params["init"]
        top_k_final = search_params["final"]

        initial_chunks = await self._search_initial_chunks(query, top_k_init)
        if not initial_chunks:
            return []

        try:
            reranker = ReRanker(provider=rerank_provider, model=rerank_model)
            reranked_chunks = await reranker.rerank_documents(query, initial_chunks, top_k_final)
            return reranked_chunks
        except Exception as e:
            print(f"⚠️ 재정렬 중 오류 발생: {e}. 초기 검색 결과의 일부를 반환합니다.")
            return initial_chunks[:top_k_final]

    async def search_without_rerank(self, query: str, search_intensity: str) -> List[str]:
        """유사한 청크를 검색만 하고 재정렬은 수행하지 않습니다."""
        search_params = Config.SEARCH_INTENSITY_MAP.get(search_intensity, Config.SEARCH_INTENSITY_MAP["medium"])
        top_k = search_params["final"]

        # 여기서는 초기 검색의 top_k를 최종 결과 개수와 동일하게 설정
        initial_chunks = await self._search_initial_chunks(query, top_k * 2) # 여유있게 2배수 검색
        return initial_chunks[:top_k]
    
    async def search(
        self,
        query: str,
        search_intensity: str,
        rerank_info: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """
        통합 검색 메서드
        rerank_info가 있으면 rerank 사용, 없으면 일반 검색
        
        Args:
            query: 검색 쿼리
            search_intensity: 검색 강도
            rerank_info: rerank 정보 {"provider": "openai", "model": "gpt-3.5-turbo"}
        """
        if rerank_info:
            return await self.search_with_rerank(
                query=query,
                search_intensity=search_intensity,
                rerank_provider=rerank_info["provider"],
                rerank_model=rerank_info["model"]
            )
        else:
            return await self.search_without_rerank(
                query=query,
                search_intensity=search_intensity
            )
    
    def get_status(self) -> dict:
        """지식 베이스 상태 정보 반환"""
        try:
            count = self.collection.count()
            return {
                'exists': True,
                'count': count,
                'path': self.db_path,
                'name': self.kb_name
            }
        except:
            return {
                'exists': False,
                'count': 0,
                'path': self.db_path,
                'name': self.kb_name
            }

