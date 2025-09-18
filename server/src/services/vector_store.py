import chromadb
import os
from typing import List, Dict
from ..core.config import Config
from .rerank import ReRanker
from .llm_factory import LLMFactory

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
