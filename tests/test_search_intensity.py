"""
SearchIntensity 시스템 테스트 - 3단계 검색 강도 검증
"""
import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.core.models import SearchIntensity


class TestSearchIntensity:
    """SearchIntensity enum 및 파라미터 테스트"""
    
    def test_search_intensity_values(self):
        """SearchIntensity enum 값 확인"""
        assert SearchIntensity.EXACT == "exact"
        assert SearchIntensity.STANDARD == "standard"
        assert SearchIntensity.COMPREHENSIVE == "comprehensive"
    
    def test_exact_search_params(self):
        """EXACT 검색 파라미터 검증"""
        params = SearchIntensity.get_search_params(SearchIntensity.EXACT)
        
        assert "init" in params
        assert "final" in params
        assert params["init"] == 20
        assert params["final"] == 10
        assert params["init"] > params["final"], "초기 검색이 재정렬보다 많아야 함"
        
        # 비율 검증 (약 2:1)
        ratio = params["init"] / params["final"]
        assert 1.5 <= ratio <= 2.5, f"비율이 적절하지 않음: {ratio}"
    
    def test_standard_search_params(self):
        """STANDARD 검색 파라미터 검증 (기본값)"""
        params = SearchIntensity.get_search_params(SearchIntensity.STANDARD)
        
        assert params["init"] == 50
        assert params["final"] == 30
        assert params["init"] > params["final"]
        
        # 비율 검증
        ratio = params["init"] / params["final"]
        assert 1.5 <= ratio <= 2.0, f"비율이 적절하지 않음: {ratio}"
    
    def test_comprehensive_search_params(self):
        """COMPREHENSIVE 검색 파라미터 검증"""
        params = SearchIntensity.get_search_params(SearchIntensity.COMPREHENSIVE)
        
        assert params["init"] == 70
        assert params["final"] == 40
        assert params["init"] > params["final"]
        
        # 비율 검증
        ratio = params["init"] / params["final"]
        assert 1.5 <= ratio <= 2.0, f"비율이 적절하지 않음: {ratio}"
    
    def test_search_params_ordering(self):
        """검색 강도 순서 검증 (EXACT < STANDARD < COMPREHENSIVE)"""
        exact = SearchIntensity.get_search_params(SearchIntensity.EXACT)
        standard = SearchIntensity.get_search_params(SearchIntensity.STANDARD)
        comprehensive = SearchIntensity.get_search_params(SearchIntensity.COMPREHENSIVE)
        
        # 초기 검색 개수 순서
        assert exact["init"] < standard["init"] < comprehensive["init"]
        
        # 최종 검색 개수 순서
        assert exact["final"] < standard["final"] < comprehensive["final"]
    
    def test_get_default(self):
        """기본 검색 강도가 STANDARD인지 확인"""
        default = SearchIntensity.get_default()
        assert default == SearchIntensity.STANDARD
    
    def test_from_top_k(self):
        """top_k 값으로 검색 강도 추론 테스트"""
        # EXACT 범위 (≤25)
        assert SearchIntensity.from_top_k(10) == SearchIntensity.EXACT
        assert SearchIntensity.from_top_k(20) == SearchIntensity.EXACT
        assert SearchIntensity.from_top_k(25) == SearchIntensity.EXACT
        
        # STANDARD 범위 (26-55)
        assert SearchIntensity.from_top_k(30) == SearchIntensity.STANDARD
        assert SearchIntensity.from_top_k(50) == SearchIntensity.STANDARD
        assert SearchIntensity.from_top_k(55) == SearchIntensity.STANDARD
        
        # COMPREHENSIVE 범위 (>55)
        assert SearchIntensity.from_top_k(60) == SearchIntensity.COMPREHENSIVE
        assert SearchIntensity.from_top_k(70) == SearchIntensity.COMPREHENSIVE
        assert SearchIntensity.from_top_k(100) == SearchIntensity.COMPREHENSIVE
    
    def test_invalid_intensity_defaults_to_standard(self):
        """잘못된 검색 강도 값은 STANDARD로 폴백"""
        params = SearchIntensity.get_search_params("invalid")
        standard_params = SearchIntensity.get_search_params(SearchIntensity.STANDARD)
        
        assert params == standard_params
    
    def test_corpus_size_appropriateness(self):
        """700개 청크 코퍼스에 대한 적절성 검증"""
        corpus_size = 700
        
        exact = SearchIntensity.get_search_params(SearchIntensity.EXACT)
        standard = SearchIntensity.get_search_params(SearchIntensity.STANDARD)
        comprehensive = SearchIntensity.get_search_params(SearchIntensity.COMPREHENSIVE)
        
        # 초기 검색 비율 (1-15% 범위가 적절)
        assert 0.01 <= exact["init"] / corpus_size <= 0.15
        assert 0.01 <= standard["init"] / corpus_size <= 0.15
        assert 0.01 <= comprehensive["init"] / corpus_size <= 0.15
        
        # 최종 검색 비율 (1-10% 범위가 적절)
        assert 0.01 <= exact["final"] / corpus_size <= 0.10
        assert 0.01 <= standard["final"] / corpus_size <= 0.10
        assert 0.01 <= comprehensive["final"] / corpus_size <= 0.10
        
        print(f"\n📊 700개 청크 기준 비율:")
        print(f"  EXACT: {exact['init']/corpus_size*100:.1f}% → {exact['final']/corpus_size*100:.1f}%")
        print(f"  STANDARD: {standard['init']/corpus_size*100:.1f}% → {standard['final']/corpus_size*100:.1f}%")
        print(f"  COMPREHENSIVE: {comprehensive['init']/corpus_size*100:.1f}% → {comprehensive['final']/corpus_size*100:.1f}%")
