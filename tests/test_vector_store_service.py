"""
테스트: VectorStoreService 테스트
"""
import pytest
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.services.vector_store_service import vector_store_service


class TestVectorStoreService:
    """VectorStoreService 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup_working_directory(self):
        """테스트를 위한 작업 디렉토리 설정"""
        original_cwd = os.getcwd()
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server')
        os.chdir(server_path)
        yield
        os.chdir(original_cwd)
    
    def test_get_knowledge_bases(self):
        """지식 베이스 목록 조회 테스트"""
        kb_list = vector_store_service.get_knowledge_bases()
        
        assert isinstance(kb_list, list), "KB 목록이 리스트가 아닙니다"
        
        # 빈 목록이어도 오류가 아님 (KB가 아직 생성되지 않았을 수 있음)
        if len(kb_list) == 0:
            pytest.skip("사용 가능한 지식 베이스가 없습니다 (TEI로 KB 재생성 필요)")
        
        # KB 목록의 각 항목이 실제로 존재하는지 확인
        for kb in kb_list:
            kb_path = f"./knowledge_bases/{kb}"
            assert os.path.exists(kb_path), f"KB 디렉토리가 존재하지 않습니다: {kb_path}"
        
        print(f"✅ KB 목록 ({len(kb_list)}개): {kb_list}")
    
    def test_get_vector_store(self):
        """VectorStore 인스턴스 가져오기 테스트"""
        kb_list = vector_store_service.get_knowledge_bases()
        
        if not kb_list:
            pytest.skip("사용 가능한 KB가 없습니다")
        
        first_kb = kb_list[0]
        vs = vector_store_service.get_vector_store(first_kb)
        
        assert vs is not None, "VectorStore 인스턴스가 None입니다"
        assert vs.kb_name == first_kb, "KB 이름이 일치하지 않습니다"
        assert hasattr(vs, 'collection'), "VectorStore에 컬렉션 속성이 없습니다"
        
        # 캐싱 테스트 - 같은 KB에 대해 같은 인스턴스 반환
        vs2 = vector_store_service.get_vector_store(first_kb)
        assert vs is vs2, "VectorStore 인스턴스가 캐싱되지 않았습니다"
        
        print(f"✅ VectorStore 인스턴스 생성 및 캐싱 성공: {first_kb}")
    
    @pytest.mark.asyncio
    async def test_get_knowledge_base_info(self):
        """지식 베이스 정보 조회 테스트"""
        kb_list = vector_store_service.get_knowledge_bases()
        
        if not kb_list:
            pytest.skip("사용 가능한 KB가 없습니다")
        
        first_kb = kb_list[0]
        kb_info = await vector_store_service.get_knowledge_base_info(first_kb)
        
        # 정보 구조 확인
        required_fields = ['name', 'count', 'path', 'exists']
        for field in required_fields:
            assert field in kb_info, f"KB 정보에 '{field}' 필드가 없습니다"
        
        # 정보 값 확인
        assert kb_info['name'] == first_kb, "KB 이름 불일치"
        assert kb_info['exists'] is True, "KB가 존재하지 않는다고 표시됨"
        assert kb_info['count'] >= 0, "문서 수가 음수입니다"
        
        print(f"✅ KB 정보 조회 성공: {kb_info}")
    
    @pytest.mark.asyncio
    async def test_search(self):
        """벡터 검색 테스트"""
        kb_list = vector_store_service.get_knowledge_bases()
        
        if not kb_list:
            pytest.skip("사용 가능한 KB가 없습니다")
        
        first_kb = kb_list[0]
        
        # 검색 테스트 - search 메서드 사용
        results = await vector_store_service.search(
            kb_name=first_kb,
            query="NVMe specification",
            search_intensity="standard"  # 표준 검색 모드
        )
        
        assert isinstance(results, list), "검색 결과가 리스트가 아닙니다"
        assert len(results) >= 0, "검색 결과 수가 음수입니다"
        
        # 결과는 문자열 리스트여야 함 (search 메서드의 실제 반환 타입)
        if results:
            assert isinstance(results[0], str), "검색 결과가 문자열이 아닙니다"
        
        print(f"✅ 검색 테스트 성공: {len(results)}개 결과")