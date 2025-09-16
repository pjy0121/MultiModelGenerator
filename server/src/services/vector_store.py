import chromadb
import os
from typing import List, Dict
from ..core.config import Config

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
    
    def search_similar_chunks(self, query: str, top_k: int = None) -> List[str]:
        """유사한 청크 검색"""
        if top_k is None:
            top_k = Config.SEARCH_TOP_K
        
        # 최대 검색 결과 수 제한 적용
        if top_k > Config.SEARCH_MAX_TOP_K:
            top_k = Config.SEARCH_MAX_TOP_K
            
        print(f"🔍 지식 베이스 '{self.kb_name}'에서 키워드 '{query}' 검색 중... (top_k={top_k})")
        
        try:
            # 컬렉션이 비어있는지 확인
            collection_count = self.collection.count()
            if collection_count == 0:
                print("❌ 지식 베이스가 비어있습니다.")
                return []
            
            # 포괄적 검색 모드가 활성화된 경우, 더 많은 결과 검색
            if Config.SEARCH_ENABLE_COMPREHENSIVE:
                # 전체 문서의 80% 또는 설정된 top_k 중 더 큰 값 사용
                comprehensive_top_k = max(top_k, int(collection_count * 0.8))
                actual_top_k = min(comprehensive_top_k, collection_count)
                print(f"📖 포괄적 검색 모드: {actual_top_k}개 청크 검색 (전체 {collection_count}개 중)")
            else:
                # 실제 검색할 결과 수 조정 (전체 청크 수보다 많을 수 없음)
                actual_top_k = min(top_k, collection_count)
            
            results = self.collection.query(
                query_texts=[query],
                n_results=actual_top_k,
                include=['documents', 'distances', 'metadatas']
            )
            
            if results['documents'] and results['documents'][0]:
                chunks = results['documents'][0]
                distances = results['distances'][0] if results['distances'] else []
                
                # 유사도 점수 기반 필터링 (설정된 임계값 사용)
                filtered_chunks = []
                for i, (chunk, distance) in enumerate(zip(chunks, distances)):
                    if distance <= Config.SEARCH_SIMILARITY_THRESHOLD:
                        filtered_chunks.append(chunk)
                    # 포괄적 검색 모드에서는 중단하지 않고 모든 결과 확인
                    elif not Config.SEARCH_ENABLE_COMPREHENSIVE:
                        break  # 일반 모드에서만 중단
                
                print(f"📚 {len(filtered_chunks)}개 관련 청크 발견 (총 {len(chunks)}개 검색 결과 중)")
                return filtered_chunks
            else:
                print("❌ 관련 문서를 찾지 못했습니다.")
                return []
                
        except Exception as e:
            print(f"⚠️ 검색 중 오류 발생: {e}")
            return []
    
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
        pass
    
    def search(self, query: str, collection_name: str, top_k: int = 5) -> List[Dict]:
        """
        지정된 컬렉션에서 벡터 검색 수행
        
        Args:
            query: 검색 쿼리
            collection_name: 지식 베이스 이름
            top_k: 반환할 최대 결과 수
            
        Returns:
            검색 결과 리스트 [{"content": "...", "distance": 0.5}, ...]
        """
        try:
            vector_store = VectorStore(collection_name)
            chunks = vector_store.search_similar_chunks(query, top_k)
            
            # VectorStore 결과를 통일된 형식으로 변환
            results = []
            for chunk in chunks:
                results.append({
                    "content": chunk,
                    "distance": 0.0  # VectorStore는 거리 정보를 반환하지 않음
                })
            
            return results
            
        except Exception as e:
            print(f"벡터 검색 실패: {e}")
            return []
    
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
            vector_store = VectorStore(kb_name)
            return vector_store.collection
        except Exception as e:
            print(f"컬렉션 조회 실패 ({kb_name}): {e}")
            return None
    
    def get_knowledge_base_info(self, kb_name: str) -> Dict:
        """지정된 지식 베이스의 상세 정보 반환"""
        try:
            vector_store = VectorStore(kb_name)
            status = vector_store.get_status()
            return {
                'name': kb_name,
                'exists': status.get('exists', False),
                'chunk_count': status.get('count', 0),  # document_count -> chunk_count
                'path': status.get('path', ''),
                'created_at': 'Unknown'
            }
        except Exception as e:
            print(f"지식 베이스 정보 조회 실패 ({kb_name}): {e}")
            return {
                'name': kb_name,
                'exists': False,
                'chunk_count': 0,  # document_count -> chunk_count
                'path': '',
                'created_at': 'Unknown'
            }
