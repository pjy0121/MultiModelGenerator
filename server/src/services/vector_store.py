import chromadb
import os
import threading
from typing import List, Dict, Optional
from ..core.config import VECTOR_DB_CONFIG, get_kb_path
from .rerank import ReRanker

# 전역 ChromaDB 클라이언트 관리자 (스레드 안전)
class ChromaDBManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._clients = {}
                    cls._instance._client_lock = threading.RLock()
        return cls._instance
    
    def get_client(self, kb_name: str) -> chromadb.PersistentClient:
        """KB별로 단일 클라이언트 인스턴스 반환 (스레드 안전)"""
        with self._client_lock:
            if kb_name not in self._clients:
                db_path = get_kb_path(kb_name)
                os.makedirs(db_path, exist_ok=True)
                print(f"🔗 새 ChromaDB 클라이언트 생성: {kb_name} -> {db_path}")
                self._clients[kb_name] = chromadb.PersistentClient(path=db_path)
            return self._clients[kb_name]
    
    def clear_client(self, kb_name: str):
        """특정 KB 클라이언트 제거 (필요시)"""
        with self._client_lock:
            if kb_name in self._clients:
                del self._clients[kb_name]
                print(f"🗑️ ChromaDB 클라이언트 제거: {kb_name}")

# 전역 매니저 인스턴스
chroma_manager = ChromaDBManager()

class VectorStore:
    def __init__(self, kb_name: str):
        self.embedding_function = chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=VECTOR_DB_CONFIG["embedding_model"])

        self.kb_name = kb_name
        self.db_path = get_kb_path(kb_name)
        
        # 전역 매니저에서 공유 클라이언트 가져오기
        self.client = chroma_manager.get_client(kb_name)
        self.collection = self.get_collection()
        
        print(f"📚 VectorStore 초기화 완료: {kb_name}")

    def get_collection(self):
        """컬렉션을 스레드 안전하게 반환"""
        # ChromaDB 클라이언트는 내부적으로 스레드 안전하지만 
        # get_or_create_collection 호출을 안전하게 처리
        try:
            return self.client.get_or_create_collection(
                name="spec_documents",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )
        except Exception as e:
            print(f"⚠️ 컬렉션 생성/접근 오류 (KB: {self.kb_name}): {e}")
            # 클라이언트 재생성 시도
            chroma_manager.clear_client(self.kb_name)
            self.client = chroma_manager.get_client(self.kb_name)
            return self.client.get_or_create_collection(
                name="spec_documents",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )

    def store_chunks(self, chunks: List[Dict]) -> None:
        """청크들을 벡터 DB에 저장"""
        print(f"💾 지식 베이스 '{self.kb_name}'에 {len(chunks)}개 청크 저장 중...")
        
        # 기존 데이터 삭제 (새로 저장하는 경우)
        try:
            self.collection.delete()
            self.collection = self.get_collection()
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
                if distance <= VECTOR_DB_CONFIG["similarity_threshold"]
            ]
            
            print(f"📚 1차 필터링 후 {len(filtered_chunks)}개 관련 청크 발견.")
            return filtered_chunks

        except Exception as e:
            print(f"⚠️ 초기 검색 중 오류 발생: {e}")
            return []

    async def search(
        self,
        query: str,
        search_intensity: str,
        rerank_info: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """
        통합 검색 메서드 - 공통 로직을 하나로 통합
        
        Args:
            query: 검색 쿼리
            search_intensity: 검색 강도
            rerank_info: rerank 정보 {"provider": "openai", "model": "gpt-3.5-turbo"}
        """
        # 공통: 검색 파라미터 설정
        search_intensity_map = VECTOR_DB_CONFIG["search_intensity_map"]
        search_params = search_intensity_map.get(search_intensity, search_intensity_map["medium"])

        top_k_init = search_params["init"]
        
        # rerank 사용 시에는 더 많은 초기 검색, 아니면 final과 동일
        if rerank_info:
            initial_chunks = await self._search_initial_chunks(query, top_k_init)
            
            if not initial_chunks:
                return []
            
            top_k_final = search_params["final"]
            try:
                reranker = ReRanker(provider=rerank_info["provider"], model=rerank_info["model"])
                reranked_chunks = await reranker.rerank_documents(query, initial_chunks, top_k_final)
                return reranked_chunks
            except Exception as e:
                print(f"⚠️ 재정렬 중 오류 발생: {e}. 초기 검색 결과의 일부를 반환합니다.")
                return initial_chunks[:top_k_final]
        else:
            initial_chunks = await self._search_initial_chunks(query, top_k_init)
            return initial_chunks
    
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
    
    async def get_knowledge_base_info(self) -> Dict:
        """지식 베이스 상세 정보 반환"""
        try:
            count = self.collection.count()
            return {
                'name': self.kb_name,
                'count': count,
                'path': self.db_path,
                'exists': True
            }
        except Exception as e:
            return {
                'name': self.kb_name,
                'count': 0,
                'path': self.db_path,
                'exists': False,
                'error': str(e)
            }

