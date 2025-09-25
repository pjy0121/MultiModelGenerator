"""
테스트: ChromaDB 직접 연결 테스트
"""
import pytest
import os
import chromadb
from chromadb.config import Settings


class TestChromaDBDirect:
    """ChromaDB 직접 연결 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup_working_directory(self):
        """테스트를 위한 작업 디렉토리 설정"""
        original_cwd = os.getcwd()
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server')
        os.chdir(server_path)
        yield
        os.chdir(original_cwd)
    
    def test_chromadb_connection(self):
        """ChromaDB 직접 연결 테스트"""
        # 지식 베이스 경로 (server 디렉토리 기준)
        kb_path = "./knowledge_bases/keyword_nvme_2-2"
        
        if not os.path.exists(kb_path):
            pytest.skip(f"지식 베이스 경로가 존재하지 않습니다: {kb_path}")
        
        # ChromaDB 클라이언트 생성
        client = chromadb.PersistentClient(path=kb_path)
        assert client is not None, "ChromaDB 클라이언트 생성 실패"
        
        # 컬렉션 목록 조회
        collections = client.list_collections()
        assert len(collections) > 0, "컬렉션이 존재하지 않습니다"
        
        # 첫 번째 컬렉션의 문서 수 확인
        collection = collections[0]
        count = collection.count()
        assert count > 0, f"컬렉션 {collection.name}에 문서가 없습니다"
        
        print(f"✅ {collection.name} 컬렉션에 {count}개 문서 확인됨")
    
    def test_collection_content_sample(self):
        """컬렉션 내용 샘플 확인"""
        kb_path = "./knowledge_bases/keyword_nvme_2-2"
        
        if not os.path.exists(kb_path):
            pytest.skip(f"지식 베이스 경로가 존재하지 않습니다: {kb_path}")
        
        client = chromadb.PersistentClient(path=kb_path)
        collections = client.list_collections()
        
        if not collections:
            pytest.skip("컬렉션이 없습니다")
            
        collection = collections[0]
        count = collection.count()
        
        if count == 0:
            pytest.skip("컬렉션이 비어있습니다")
        
        # 샘플 문서 조회
        results = collection.peek(limit=3)
        assert 'documents' in results, "문서 결과가 없습니다"
        assert len(results['documents']) > 0, "샘플 문서가 없습니다"
        
        # 첫 번째 문서 내용 확인
        first_doc = results['documents'][0]
        assert len(first_doc) > 0, "첫 번째 문서가 비어있습니다"
        
        print(f"✅ 샘플 문서 확인: {first_doc[:100]}...")