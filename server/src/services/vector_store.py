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
        # TEI 또는 로컬 embedding 함수 선택
        config = VECTOR_DB_CONFIG
        if config.get('tei_enabled', False):
            from .tei_embedding import TEIEmbeddingFunction
            self.embedding_function = TEIEmbeddingFunction(
                base_url=config.get('tei_base_url', 'http://localhost:8080'),
                timeout=config.get('tei_timeout', 30)
            )
        else:
            # 로컬 sentence-transformers 사용
            self.embedding_function = chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=config.get('local_embedding_model', 'all-MiniLM-L6-v2')
            )

        self.kb_name = kb_name
        self.db_path = get_kb_path(kb_name)
        
        # 지연 초기화 - 실제 사용할 때만 ChromaDB 파일 접근
        self.client = None
        self.collection = None
        self._closed = False
    
    def __enter__(self):
        """Context manager 진입"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료 - 자동으로 연결 닫기"""
        self.close()
        return False
    
    def close(self):
        """ChromaDB 연결 명시적으로 닫기 (SQLite WAL 체크포인트 포함)"""
        if self._closed:
            return
        
        try:
            # SQLite WAL 체크포인트 강제 실행 (쓰기 완료 보장)
            import sqlite3
            db_file = os.path.join(self.db_path, 'chroma.sqlite3')
            if os.path.exists(db_file):
                try:
                    conn = sqlite3.connect(db_file, timeout=10.0)
                    conn.execute('PRAGMA wal_checkpoint(FULL);')  # WAL 파일 병합
                    conn.commit()
                    conn.close()
                except Exception as checkpoint_err:
                    print(f"⚠️ WAL checkpoint 실패 (무시): {checkpoint_err}")
            
            # 컬렉션과 클라이언트 참조 제거
            self.collection = None
            if self.client is not None:
                # ChromaDB client는 명시적 close가 없으므로 참조만 제거
                self.client = None
            
            # 가비지 컬렉션 강제 실행 (2회)
            import gc
            gc.collect()
            import time
            time.sleep(0.05)  # 파일 핸들 해제 대기
            gc.collect()
            
            self._closed = True
            print(f"✅ VectorStore '{self.kb_name}' 연결 닫힘 (WAL checkpoint 완료)")
        except Exception as e:
            print(f"⚠️ VectorStore '{self.kb_name}' 닫기 중 오류: {e}")
        
    def get_collection(self):
        """컬렉션을 지연 초기화로 반환 (동시성 문제 해결된 버전)"""
        if self.collection is None:
            # 각 VectorStore 인스턴스마다 독립적인 ChromaDB 클라이언트 생성
            if self.client is None:
                os.makedirs(self.db_path, exist_ok=True)
                # 동시 접근 시 충돌 방지를 위해 데이터베이스 오픈 시도
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        # ChromaDB 설정: SQLite 동시성 개선
                        settings = chromadb.Settings(
                            allow_reset=True,
                            anonymized_telemetry=False,
                            # SQLite WAL 모드는 자동 설정됨 (ChromaDB 내부)
                        )
                        self.client = chromadb.PersistentClient(
                            path=self.db_path,
                            settings=settings
                        )
                        
                        # SQLite busy_timeout 설정 (readonly 에러 완화)
                        # ChromaDB의 내부 SQLite 연결에 직접 접근
                        import sqlite3
                        db_file = os.path.join(self.db_path, 'chroma.sqlite3')
                        if os.path.exists(db_file):
                            conn = sqlite3.connect(db_file, timeout=30.0)
                            conn.execute('PRAGMA journal_mode=WAL;')  # WAL 모드 강제
                            conn.execute('PRAGMA busy_timeout=30000;')  # 30초 대기
                            conn.close()
                        
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"⚠️ ChromaDB 클라이언트 생성 시도 {attempt + 1}/{max_retries} 실패 (KB: {self.kb_name}): {e}")
                            import time
                            time.sleep(0.2 * (2 ** attempt))  # 지수 백오프: 0.2s, 0.4s, 0.8s, 1.6s
                        else:
                            raise e
            
            # 컬렉션 접근도 재시도 로직 적용
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    self.collection = self.client.get_or_create_collection(
                        name="spec_documents",
                        metadata={"hnsw:space": "cosine"},
                        embedding_function=self.embedding_function
                    )
                    break
                except Exception as e:
                    error_msg = str(e).lower()
                    is_readonly = 'readonly' in error_msg or 'locked' in error_msg
                    
                    if is_readonly and attempt < max_retries - 1:
                        print(f"⚠️ DB 잠금/읽기전용 에러 - 재시도 {attempt + 1}/{max_retries} (KB: {self.kb_name})")
                        import time
                        time.sleep(0.5 * (2 ** attempt))  # 지수 백오프: 0.5s, 1s, 2s, 4s
                        
                        # 클라이언트 완전 재생성
                        self.client = None
                        import gc
                        gc.collect()  # 강제 가비지 컬렉션
                        time.sleep(0.1)  # 파일 핸들 해제 대기
                        
                        # 재생성
                        settings = chromadb.Settings(
                            allow_reset=True,
                            anonymized_telemetry=False,
                        )
                        self.client = chromadb.PersistentClient(
                            path=self.db_path,
                            settings=settings
                        )
                    elif attempt < max_retries - 1:
                        print(f"⚠️ 컬렉션 접근 시도 {attempt + 1}/{max_retries} 실패 (KB: {self.kb_name}): {e}")
                        import time
                        time.sleep(0.2 * (2 ** attempt))
                    else:
                        raise e
        
        return self.collection

    def store_chunks(self, chunks: List[Dict], max_retries: int = 3) -> None:
        """청크들을 벡터 DB에 저장 (재시도 로직 포함)"""
        print(f"💾 지식 베이스 '{self.kb_name}'에 {len(chunks)}개 청크 저장 중...")
        
        import time
        import sqlite3
        
        for attempt in range(max_retries):
            try:
                collection = self.get_collection()
                
                # 기존 데이터 삭제 (안전한 방법: 기존 ID 조회 후 삭제)
                try:
                    existing_data = collection.get()
                    if existing_data and existing_data['ids']:
                        collection.delete(ids=existing_data['ids'])
                        print(f"🗑️  기존 {len(existing_data['ids'])}개 청크 삭제됨")
                except Exception as e:
                    print(f"⚠️ 기존 데이터 삭제 중 오류 (무시하고 계속): {e}")
                
                ids = [f"chunk_{chunk['id']}" for chunk in chunks]
                documents = [chunk['content'] for chunk in chunks]
                embeddings = [chunk['embedding'] for chunk in chunks]
                metadatas = [{'length': chunk['length'], 'chunk_id': chunk['id']} for chunk in chunks]
                
                # 배치 크기로 나누어 저장 (ChromaDB 제한)
                batch_size = 100
                for i in range(0, len(chunks), batch_size):
                    end_idx = min(i + batch_size, len(chunks))
                    
                    collection.add(
                        ids=ids[i:end_idx],
                        documents=documents[i:end_idx],
                        embeddings=embeddings[i:end_idx],
                        metadatas=metadatas[i:end_idx]
                    )
                
                print(f"✅ 지식 베이스 '{self.kb_name}' 저장 완료!")
                return  # 성공 시 종료
                
            except (sqlite3.OperationalError, Exception) as e:
                error_msg = str(e).lower()
                is_db_error = 'readonly' in error_msg or 'locked' in error_msg or 'database' in error_msg
                
                if is_db_error and attempt < max_retries - 1:
                    print(f"⚠️ DB 쓰기 에러 발생 - 재시도 {attempt + 1}/{max_retries}: {e}")
                    time.sleep(1.0 * (2 ** attempt))  # 1s, 2s 대기
                    
                    # 컬렉션 재초기화
                    self.collection = None
                    self.client = None
                    import gc
                    gc.collect()
                    time.sleep(0.2)
                else:
                    raise Exception(f"지식 베이스 저장 실패 ({attempt + 1}회 시도): {e}")

    async def _search_initial_chunks(self, query: str, top_k: int, threshold: float) -> List[str]:
        """초기 벡터 검색을 수행하는 내부 헬퍼 함수 (비동기 개선된 버전)
        
        Args:
            query: 검색 쿼리
            top_k: 초기 검색 개수
            threshold: cosine distance 임계값
        """
        print(f"🔍 지식 베이스 '{self.kb_name}'에서 키워드 '{query}' 초기 검색 중... (top_k={top_k}, threshold={threshold:.2f})")
        
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
            
            # 거리(distance)와 유사도(similarity) 정보 출력
            print(f"🔍 검색된 {len(initial_chunks)}개 청크의 거리 범위: {min(distances):.3f} ~ {max(distances):.3f}")
            print(f"   임계값: {threshold:.2f} (이하만 통과) - Cosine similarity: {1-threshold:.2f} 이상")
            
            # 거리 기반 필터링 (cosine distance: 0=identical, 2=opposite)
            filtered_chunks = [
                chunk for chunk, distance in zip(initial_chunks, distances)
                if distance <= threshold
            ]
            
            print(f"📚 임계값 필터링 후 {len(filtered_chunks)}개 관련 청크 발견 (전체 {len(initial_chunks)}개 중)")
            
            # 필터링된 청크가 없으면 상위 결과라도 반환 (최소 1개)
            if not filtered_chunks and initial_chunks:
                print(f"⚠️ 임계값을 통과한 청크가 없어 가장 유사한 1개 청크 반환 (distance: {distances[0]:.3f})")
                filtered_chunks = [initial_chunks[0]]
            
            return filtered_chunks

        except Exception as e:
            print(f"⚠️ 초기 검색 중 오류 발생: {e}")
            return []

    async def search(
        self,
        query: str,
        search_intensity: str,
        rerank_info: Optional[Dict[str, str]] = None
    ) -> Dict[str, any]:
        """
        통합 검색 메서드 - 공통 로직을 하나로 통합
        
        Args:
            query: 검색 쿼리
            search_intensity: 검색 강도
            rerank_info: rerank 정보 {"provider": "openai", "model": "gpt-3.5-turbo"}
            
        Returns:
            Dict with 'chunks' (검색 결과), 'total_chunks' (전체 청크 수), 'found_chunks' (검색된 청크 수)
        """
        # 전체 청크 수 조회
        import asyncio
        collection = await asyncio.get_event_loop().run_in_executor(
            None, self.get_collection
        )
        total_chunks = await asyncio.get_event_loop().run_in_executor(
            None, collection.count
        )
        
        # 공통: 검색 파라미터 설정 (top_k, threshold 모두 포함)
        search_params = SearchIntensity.get_search_params(search_intensity)

        top_k_init = search_params["init"]
        threshold = search_params["threshold"]
        
        print(f"🎯 검색 강도: {search_intensity} (초기 {top_k_init}개, threshold {threshold:.2f}, similarity {1-threshold:.2f}+)")
        
        # rerank 사용 시에는 더 많은 초기 검색, 아니면 final과 동일
        if rerank_info:
            initial_chunks = await self._search_initial_chunks(query, top_k_init, threshold)
            
            if not initial_chunks:
                return {"chunks": [], "total_chunks": total_chunks, "found_chunks": 0}
            
            top_k_final = search_params["final"]
            try:
                reranker = ReRanker(provider=rerank_info["provider"], model=rerank_info["model"])
                reranked_chunks = await reranker.rerank_documents(query, initial_chunks, top_k_final)
                return {"chunks": reranked_chunks, "total_chunks": total_chunks, "found_chunks": len(reranked_chunks)}
            except Exception as e:
                print(f"⚠️ 재정렬 중 오류 발생: {e}. 초기 검색 결과의 일부를 반환합니다.")
                result_chunks = initial_chunks[:top_k_final]
                return {"chunks": result_chunks, "total_chunks": total_chunks, "found_chunks": len(result_chunks)}
        else:
            initial_chunks = await self._search_initial_chunks(query, top_k_init, threshold)
            return {"chunks": initial_chunks, "total_chunks": total_chunks, "found_chunks": len(initial_chunks)}
    
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
        """사용 가능한 지식 베이스 목록 반환 (재귀적으로 모든 하위 폴더 검색)"""
        try:
            kb_base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge_bases')
            kb_base_path = os.path.abspath(kb_base_path)
            
            if not os.path.exists(kb_base_path):
                return []
            
            knowledge_bases = []
            
            def scan_directory(current_path: str, relative_path: str = ""):
                """재귀적으로 디렉토리 스캔 - chroma.sqlite3 파일이 있는 디렉토리만 KB로 간주"""
                try:
                    for item in os.listdir(current_path):
                        item_path = os.path.join(current_path, item)
                        
                        if os.path.isdir(item_path):
                            # chroma.sqlite3 파일이 있고 크기가 0보다 크면 KB로 간주
                            chroma_file = os.path.join(item_path, 'chroma.sqlite3')
                            if os.path.exists(chroma_file):
                                try:
                                    # 파일 크기 확인 (빈 파일 제외)
                                    file_size = os.path.getsize(chroma_file)
                                    if file_size > 0:
                                        # 상대 경로 포함하여 저장
                                        if relative_path:
                                            kb_name = f"{relative_path}/{item}"
                                        else:
                                            kb_name = item
                                        knowledge_bases.append(kb_name)
                                    else:
                                        # 빈 chroma.sqlite3 파일은 무시하고 하위 폴더 스캔
                                        new_relative = f"{relative_path}/{item}" if relative_path else item
                                        scan_directory(item_path, new_relative)
                                except OSError:
                                    # 파일 크기 확인 실패 시 하위 폴더 스캔
                                    new_relative = f"{relative_path}/{item}" if relative_path else item
                                    scan_directory(item_path, new_relative)
                            else:
                                # chroma.sqlite3가 없으면 하위 폴더 스캔
                                new_relative = f"{relative_path}/{item}" if relative_path else item
                                scan_directory(item_path, new_relative)
                except Exception as e:
                    print(f"디렉토리 스캔 실패 ({current_path}): {e}")
            
            scan_directory(kb_base_path)
            return sorted(knowledge_bases)
            
        except Exception as e:
            print(f"지식 베이스 목록 조회 실패: {e}")
            return []
    
    async def get_knowledge_base_info(self) -> Dict:
        """지식 베이스 상세 정보 반환 (실제 ChromaDB 청크 개수 포함)"""
        import asyncio
        
        def get_info_with_chromadb():
            """ChromaDB에서 실제 청크 개수 조회"""
            exists = os.path.exists(self.db_path)
            
            actual_count = 0
            if exists:
                try:
                    # 실제 ChromaDB 컬렉션에서 개수 조회
                    collection = self.get_collection()
                    actual_count = collection.count()
                except Exception as e:
                    print(f"⚠️ ChromaDB 개수 조회 실패 ({self.kb_name}): {e}")
                    actual_count = 0
                    
            return {
                'name': self.kb_name,
                'count': actual_count,  # 실제 청크 개수
                'path': self.db_path,
                'exists': exists
            }
        
        # 비동기로 실행하여 블로킹 방지
        loop = asyncio.get_event_loop()
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, get_info_with_chromadb)
    
    def close(self):
        """ChromaDB 연결을 명시적으로 닫아 파일 잠금 해제"""
        try:
            if self.collection is not None:
                self.collection = None
            if self.client is not None:
                # ChromaDB client의 연결 닫기
                try:
                    # PersistentClient는 명시적인 close 메서드가 없으므로
                    # 참조를 None으로 설정하고 가비지 컬렉션에 맡김
                    self.client = None
                except Exception as e:
                    print(f"⚠️ ChromaDB client 닫기 중 오류: {e}")
            print(f"✅ VectorStore '{self.kb_name}' 연결 닫힘")
        except Exception as e:
            print(f"⚠️ VectorStore 닫기 중 오류: {e}")

