"""
Chunk Configuration 테스트 - Token 기반 설정 검증
"""
import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.config import VECTOR_DB_CONFIG


class TestChunkConfiguration:
    """Token 기반 Chunk 설정 테스트"""
    
    def test_token_based_config_exists(self):
        """Token 기반 설정이 존재하는지 확인"""
        assert "chunk_tokens" in VECTOR_DB_CONFIG
        assert "overlap_ratio" in VECTOR_DB_CONFIG
        assert "chars_per_token" in VECTOR_DB_CONFIG
    
    def test_chunk_tokens_value(self):
        """chunk_tokens 값이 512인지 확인 (BGE-M3 최적화)"""
        assert VECTOR_DB_CONFIG["chunk_tokens"] == 512
    
    def test_overlap_ratio_value(self):
        """overlap_ratio 값이 0.15(15%)인지 확인"""
        assert VECTOR_DB_CONFIG["overlap_ratio"] == 0.15
    
    def test_chars_per_token_value(self):
        """chars_per_token 값이 4인지 확인 (평균 문자/토큰 비율)"""
        assert VECTOR_DB_CONFIG["chars_per_token"] == 4
    
    def test_no_deprecated_chunk_params(self):
        """더 이상 사용하지 않는 character 기반 파라미터가 없는지 확인"""
        # 이전에 사용하던 파라미터들이 제거되었는지 확인
        deprecated_keys = ["chunk_size", "chunk_overlap", "chunk_overlap_tokens"]
        
        for key in deprecated_keys:
            assert key not in VECTOR_DB_CONFIG, f"Deprecated parameter '{key}' still exists in config"
    
    def test_calculated_chunk_size(self):
        """Token 기반으로 계산한 chunk_size가 올바른지 검증"""
        chunk_tokens = VECTOR_DB_CONFIG["chunk_tokens"]
        chars_per_token = VECTOR_DB_CONFIG["chars_per_token"]
        
        calculated_chunk_size = chunk_tokens * chars_per_token
        expected_chunk_size = 512 * 4  # 2048
        
        assert calculated_chunk_size == expected_chunk_size
        assert calculated_chunk_size == 2048
    
    def test_calculated_chunk_overlap(self):
        """Token 기반으로 계산한 chunk_overlap이 올바른지 검증"""
        chunk_tokens = VECTOR_DB_CONFIG["chunk_tokens"]
        chars_per_token = VECTOR_DB_CONFIG["chars_per_token"]
        overlap_ratio = VECTOR_DB_CONFIG["overlap_ratio"]
        
        chunk_size = chunk_tokens * chars_per_token
        calculated_overlap = int(chunk_size * overlap_ratio)
        expected_overlap = int(2048 * 0.15)  # 307
        
        assert calculated_overlap == expected_overlap
        assert calculated_overlap == 307
    
    def test_overlap_token_calculation(self):
        """Overlap을 토큰 수로 계산했을 때 올바른지 검증"""
        chunk_tokens = VECTOR_DB_CONFIG["chunk_tokens"]
        overlap_ratio = VECTOR_DB_CONFIG["overlap_ratio"]
        
        overlap_tokens = int(chunk_tokens * overlap_ratio)
        expected_overlap_tokens = int(512 * 0.15)  # 76.8 -> 76
        
        assert overlap_tokens == expected_overlap_tokens
        assert 76 <= overlap_tokens <= 77  # 반올림 오차 허용
    
    def test_config_consistency(self):
        """설정값들이 논리적으로 일관성 있는지 확인"""
        chunk_tokens = VECTOR_DB_CONFIG["chunk_tokens"]
        overlap_ratio = VECTOR_DB_CONFIG["overlap_ratio"]
        chars_per_token = VECTOR_DB_CONFIG["chars_per_token"]
        
        # chunk_tokens는 양수
        assert chunk_tokens > 0
        
        # overlap_ratio는 0~1 사이
        assert 0 < overlap_ratio < 1
        
        # chars_per_token은 2~6 사이가 일반적
        assert 2 <= chars_per_token <= 6
        
        # Overlap은 chunk_size보다 작아야 함
        overlap_tokens = int(chunk_tokens * overlap_ratio)
        assert overlap_tokens < chunk_tokens
    
    def test_tokenizer_model_config(self):
        """Tokenizer 모델 설정이 BGE-M3인지 확인"""
        assert "tokenizer_model" in VECTOR_DB_CONFIG
        assert VECTOR_DB_CONFIG["tokenizer_model"] == "BAAI/bge-m3"
    
    def test_single_source_of_truth(self):
        """Token 기반 파라미터가 단일 진실 공급원인지 확인"""
        # 필수 파라미터만 존재해야 함
        required_params = {"chunk_tokens", "overlap_ratio", "chars_per_token"}
        chunk_params = {k for k in VECTOR_DB_CONFIG.keys() 
                       if "chunk" in k.lower() or "overlap" in k.lower() or "chars_per_token" in k}
        
        # chunk 관련 파라미터는 required_params를 포함해야 함
        assert required_params.issubset(chunk_params), f"Missing params: {required_params - chunk_params}"
        
        # deprecated 파라미터가 없어야 함
        deprecated_params = {"chunk_size", "chunk_overlap", "chunk_overlap_tokens"}
        assert not deprecated_params.intersection(chunk_params), f"Deprecated params found: {deprecated_params.intersection(chunk_params)}"
        
        print(f"\n📏 Chunk 관련 파라미터: {chunk_params}")
        print(f"✅ Token 기반 단일 진실 공급원: {required_params}")
