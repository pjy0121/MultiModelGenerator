"""
테스트: 지식 베이스 로딩 종합 테스트
"""
import pytest
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.services.vector_store_service import VectorStoreService


class TestKnowledgeBaseLoading:
    """지식 베이스 로딩 종합 테스트"""
    
    @pytest.fixture
    def vector_service(self):
        """VectorStoreService 인스턴스 fixture"""
        return VectorStoreService()
    
    @pytest.fixture(autouse=True)
    def setup_working_directory(self):
        """테스트를 위한 작업 디렉토리 설정"""
        original_cwd = os.getcwd()
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server')
        os.chdir(server_path)
        yield
        os.chdir(original_cwd)
    
    @pytest.fixture
    async def available_kbs_data(self, vector_service):
        """사용 가능한 지식 베이스 목록"""
        return await vector_service.get_knowledge_bases()
    
    @pytest.mark.asyncio
    async def test_knowledge_base_availability(self, vector_service):
        """지식 베이스 가용성 테스트"""
        available_kbs = await vector_service.get_knowledge_bases()
        assert isinstance(available_kbs, list), "KB 목록이 리스트가 아닙니다"
        assert len(available_kbs) > 0, "사용 가능한 지식 베이스가 없습니다"
        
        print(f"📚 사용 가능한 지식 베이스: {available_kbs}")
    
    @pytest.mark.asyncio
    async def test_all_knowledge_bases_info(self, vector_service):
        """모든 지식 베이스 정보 로딩 테스트"""
        available_kbs = await vector_service.get_knowledge_bases()
        
        if not available_kbs:
            pytest.skip("사용 가능한 지식 베이스가 없습니다")
        
        for kb_name in available_kbs:
            print(f"🔍 {kb_name} 정보 조회 중...")
            
            try:
                kb_info = await vector_service.get_knowledge_base_info(kb_name)
                
                # 기본 정보 확인
                assert kb_info['name'] == kb_name, f"{kb_name}: 이름 불일치"
                assert kb_info['exists'] is True, f"{kb_name}: 존재하지 않음"
                assert kb_info['count'] >= 0, f"{kb_name}: 문서 수가 음수"
                
                print(f"✅ {kb_name}:")
                print(f"   - 문서 수: {kb_info['count']}")
                print(f"   - 경로: {kb_info['path']}")
                print(f"   - 존재 여부: {kb_info['exists']}")
                
            except Exception as e:
                pytest.fail(f"{kb_name} 정보 조회 실패: {e}")
    
    @pytest.mark.asyncio 
    async def test_knowledge_base_search_functionality(self, vector_service):
        """지식 베이스 검색 기능 테스트"""
        available_kbs = await vector_service.get_knowledge_bases()
        
        if not available_kbs:
            pytest.skip("사용 가능한 지식 베이스가 없습니다")
        
        # 첫 번째 KB로 검색 테스트
        first_kb = available_kbs[0]
        
        try:
            # 간단한 검색 쿼리 테스트 - search 메서드는 Dict 반환
            results = await vector_service.search(
                kb_name=first_kb,
                query="specification",
                search_intensity="standard"
            )
            
            assert isinstance(results, dict), "검색 결과가 Dict가 아닙니다"
            assert 'chunks' in results, "결과에 'chunks' 키가 없습니다"
            assert 'total_chunks' in results, "결과에 'total_chunks' 키가 없습니다"
            assert 'found_chunks' in results, "결과에 'found_chunks' 키가 없습니다"
            
            chunks = results['chunks']
            assert isinstance(chunks, list), "chunks가 리스트가 아닙니다"
            
            print(f"🔍 {first_kb} 검색 테스트:")
            print(f"   - 쿼리: 'specification'")
            print(f"   - 검색된 청크: {results['found_chunks']}개")
            print(f"   - 전체 청크: {results['total_chunks']}개")
            
            # 검색 결과가 있는 경우 구조 확인
            if chunks:
                chunk = chunks[0]
                assert isinstance(chunk, str), "검색 결과가 문자열이 아닙니다"
                assert len(chunk) > 0, "검색 결과 내용이 비어있습니다"
                
                print(f"   - 첫 번째 결과 미리보기: {chunk[:100]}...")
            
        except Exception as e:
            pytest.fail(f"{first_kb} 검색 기능 테스트 실패: {e}")
    
    @pytest.mark.asyncio
    async def test_knowledge_base_consistency(self, vector_service):
        """지식 베이스 일관성 테스트"""
        available_kbs = await vector_service.get_knowledge_bases()
        
        if not available_kbs:
            pytest.skip("사용 가능한 지식 베이스가 없습니다")
        
        # 중복된 KB 이름이 없는지 확인
        assert len(available_kbs) == len(set(available_kbs)), "중복된 KB 이름이 있습니다"
        
        # KB 이름 형식 확인
        for kb_name in available_kbs:
            assert isinstance(kb_name, str), f"KB 이름이 문자열이 아닙니다: {kb_name}"
            assert len(kb_name) > 0, "빈 KB 이름이 있습니다"
            assert not kb_name.isspace(), "공백으로만 이루어진 KB 이름이 있습니다"
        
        print(f"✅ 모든 KB 이름 일관성 확인 완료: {len(available_kbs)}개")