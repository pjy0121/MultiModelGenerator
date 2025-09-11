import chromadb
import os
from typing import List, Dict
from config import Config

class VectorStore:
    def __init__(self, kb_name: str):
        self.kb_name = kb_name
        self.db_path = Config.get_kb_path(kb_name)
        
        # 지식베이스 디렉토리 생성
        os.makedirs(self.db_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(
            name="spec_documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    def store_chunks(self, chunks: List[Dict]) -> None:
        """청크들을 벡터 DB에 저장"""
        print(f"💾 지식베이스 '{self.kb_name}'에 {len(chunks)}개 청크 저장 중...")
        
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
        
        print(f"✅ 지식베이스 '{self.kb_name}' 저장 완료!")
    
    def search_similar_chunks(self, query: str, top_k: int = Config.SEARCH_TOP_K) -> List[str]:
        """유사한 청크 검색"""
        print(f"🔍 지식베이스 '{self.kb_name}'에서 키워드 '{query}' 검색 중...")
        
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        if results['documents'] and results['documents'][0]:
            chunks = results['documents'][0]
            print(f"📚 {len(chunks)}개 관련 청크 발견")
            return chunks
        else:
            print("❌ 관련 문서를 찾지 못했습니다.")
            return []
    
    def get_status(self) -> dict:
        """지식베이스 상태 정보 반환"""
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
