import chromadb
import os
import threading
from typing import List, Dict, Optional
from ..core.config import VECTOR_DB_CONFIG
from ..core.utils import get_kb_path
from ..core.models import SearchIntensity
from .rerank import ReRanker

# ChromaDBManager 클래스 제거됨 - 각 VectorStore 인스턴스가 독립적인 클라이언트 사용

class VectorStore:
    def __init__(self, kb_name: str):
        self.embedding_function = chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=VECTOR_DB_CONFIG["embedding_model"])

        self.kb_name = kb_name
        self.db_path = get_kb_path(kb_name)
        
        # 지연 초기화 - 실제 사용할 때만 ChromaDB 파일 접근
        self.client = None
        self.collection = None
        
    def get_collection(self):
        """컬렉션을 지연 초기화로 반환 (동시성 문제 해결된 버전)"""
        if self.collection is None:
            # 각 VectorStore 인스턴스마다 독립적인 ChromaDB 클라이언트 생성
            if self.client is None:
                os.makedirs(self.db_path, exist_ok=True)
                # 동시 접근 시 충돌 방지를 위해 데이터베이스 오픈 시도
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        self.client = chromadb.PersistentClient(path=self.db_path)
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"⚠️ ChromaDB 클라이언트 생성 시도 {attempt + 1} 실패 (KB: {self.kb_name}): {e}")
                            import time
                            time.sleep(0.1 + attempt * 0.1)  # 점진적 백오프
                        else:
                            raise e
            
            # 컬렉션 접근도 재시도 로직 적용
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.collection = self.client.get_or_create_collection(
                        name="spec_documents",
                        metadata={"hnsw:space": "cosine"},
                        embedding_function=self.embedding_function
                    )
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"⚠️ 컬렉션 접근 시도 {attempt + 1} 실패 (KB: {self.kb_name}): {e}")
                        import time
                        time.sleep(0.2 + attempt * 0.1)  # 점진적 백오프
                        # 클라이언트 재생성
                        self.client = chromadb.PersistentClient(path=self.db_path)
                    else:
                        raise e
        
        return self.collection

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
            
            self.get_collection().add(
                ids=ids[i:end_idx],
                documents=documents[i:end_idx],
                embeddings=embeddings[i:end_idx],
                metadatas=metadatas[i:end_idx]
            )
        
        print(f"✅ 지식 베이스 '{self.kb_name}' 저장 완료!")

    async def _search_initial_chunks(self, query: str, top_k: int) -> List[str]:
        """초기 벡터 검색을 수행하는 내부 헬퍼 함수 (비동기 개선된 버전)"""
        print(f"🔍 지식 베이스 '{self.kb_name}'에서 키워드 '{query}' 초기 검색 중... (top_k={top_k})")
        
        try:
            # 비동기로 컴렉션 접근
            import asyncio
            collection = await asyncio.get_event_loop().run_in_executor(
                None, self.get_collection
            )
            
            # 카운트 조회도 비동기로 처리
            collection_count = await asyncio.get_event_loop().run_in_executor(
                None, collection.count
            )
            
            if collection_count == 0:
                print("❌ 지식 베이스가 비어있습니다.")
                return []
            
            actual_top_k = min(top_k, collection_count)
            
            # 벡터 검색도 비동기로 처리
            results = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: collection.query(
                    query_texts=[query],
                    n_results=actual_top_k,
                    include=['documents', 'distances']
                )
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
        search_params = SearchIntensity.get_search_params(search_intensity)

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
    
    async def get_status(self) -> dict:
        """지식 베이스 상태 정보 반환 (비동기 개선된 버전)"""
        try:
            import asyncio
            collection = await asyncio.get_event_loop().run_in_executor(
                None, self.get_collection
            )
            count = await asyncio.get_event_loop().run_in_executor(
                None, collection.count
            )
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
        """지식 베이스 상세 정보 반환 (ChromaDB 파일 접근 최소화)"""
        import asyncio
        
        def get_info_without_chromadb():
            """ChromaDB 파일에 접근하지 않고 기본 정보만 반환"""
            # 디렉토리 존재 여부만 확인
            exists = os.path.exists(self.db_path)
            
            # 파일 개수로 대략적인 chunk 수 추정 (ChromaDB 접근 없이)
            estimated_count = 0
            if exists:
                try:
                    # ChromaDB 디렉토리 내 파일들의 개수로 추정
                    import glob
                    files = glob.glob(os.path.join(self.db_path, "**", "*"), recursive=True)
                    # 대략적인 추정 (정확하지 않지만 블로킹 없음)
                    estimated_count = max(0, len([f for f in files if os.path.isfile(f)]) // 10)
                except:
                    estimated_count = 0
                    
            return {
                'name': self.kb_name,
                'count': estimated_count,  # 추정값 (블로킹 방지)
                'path': self.db_path,
                'exists': exists
            }
        
        # 비동기로 실행하여 블로킹 방지
        loop = asyncio.get_event_loop()
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, get_info_without_chromadb)

