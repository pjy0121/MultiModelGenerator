"""
테스트: VectorStore 클래스 직접 테스트
"""
import pytest
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.services.vector_store import VectorStore


class TestVectorStoreDirect:
    """VectorStore 클래스 직접 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup_working_directory(self):
        """테스트를 위한 작업 디렉토리 설정"""
        original_cwd = os.getcwd()
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server')
        os.chdir(server_path)
        yield
        os.chdir(original_cwd)
    
    @pytest.fixture
    def vector_store(self):
        """VectorStore 인스턴스 생성"""
        return VectorStore("keyword_nvme_2-2")
    
    def test_vector_store_creation(self, vector_store):
        """VectorStore 인스턴스 생성 테스트"""
        assert vector_store is not None, "VectorStore 생성 실패"
        assert vector_store.kb_name == "keyword_nvme_2-2", "KB 이름 불일치"
        assert hasattr(vector_store, 'collection'), "컬렉션 속성 없음"
        assert hasattr(vector_store, 'db_path'), "DB 경로 속성 없음"
    
    def test_vector_store_collection_info(self, vector_store):
        """VectorStore 컬렉션 정보 테스트"""
        # 컬렉션 이름 확인
        assert vector_store.collection.name == "spec_documents", "컬렉션 이름 불일치"
        
        # 문서 수 확인
        count = vector_store.collection.count()
        assert count >= 0, "문서 수가 음수입니다"
        
        print(f"✅ 컬렉션 '{vector_store.collection.name}'에 {count}개 문서")
    
    def test_vector_store_get_status(self, vector_store):
        """VectorStore get_status() 메서드 테스트"""
        status = vector_store.get_status()
        
        # 상태 정보 구조 확인
        required_fields = ['exists', 'count', 'path', 'name']
        for field in required_fields:
            assert field in status, f"상태 정보에 '{field}' 필드가 없습니다"
        
        # 상태 값 확인
        assert status['exists'] is True, "지식 베이스가 존재하지 않는다고 표시됨"
        assert status['count'] >= 0, "문서 수가 음수입니다"
        assert status['name'] == "keyword_nvme_2-2", "KB 이름 불일치"
        
        print(f"✅ 상태 정보: {status}")
    
    @pytest.mark.asyncio
    async def test_vector_store_get_knowledge_base_info(self, vector_store):
        """VectorStore get_knowledge_base_info() 메서드 테스트"""
        kb_info = await vector_store.get_knowledge_base_info()
        
        # 정보 구조 확인
        required_fields = ['name', 'count', 'path', 'exists']
        for field in required_fields:
            assert field in kb_info, f"KB 정보에 '{field}' 필드가 없습니다"
        
        # 정보 값 확인
        assert kb_info['name'] == "keyword_nvme_2-2", "KB 이름 불일치"
        assert kb_info['exists'] is True, "KB가 존재하지 않는다고 표시됨"
        assert kb_info['count'] >= 0, "문서 수가 음수입니다"
        
        print(f"✅ KB 정보: {kb_info}")
    
    def test_vector_store_get_knowledge_bases(self, vector_store):
        """VectorStore get_knowledge_bases() 메서드 테스트"""
        kb_list = vector_store.get_knowledge_bases()
        
        assert isinstance(kb_list, list), "KB 목록이 리스트가 아닙니다"
        assert len(kb_list) > 0, "사용 가능한 KB가 없습니다"
        assert "keyword_nvme_2-2" in kb_list, "테스트 KB가 목록에 없습니다"
        
        print(f"✅ KB 목록: {kb_list}")