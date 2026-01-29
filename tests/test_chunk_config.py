"""
Chunk Configuration test - Token-based configuration verification
"""
import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.config import VECTOR_DB_CONFIG


class TestChunkConfiguration:
    """Token-based Chunk configuration tests"""

    def test_token_based_config_exists(self):
        """Verify token-based configuration exists"""
        assert "chunk_tokens" in VECTOR_DB_CONFIG
        assert "overlap_ratio" in VECTOR_DB_CONFIG
        assert "chars_per_token" in VECTOR_DB_CONFIG

    def test_chunk_tokens_value(self):
        """Verify chunk_tokens value is 512 (BGE-M3 optimized)"""
        assert VECTOR_DB_CONFIG["chunk_tokens"] == 512

    def test_overlap_ratio_value(self):
        """Verify overlap_ratio value is 0.15 (15%)"""
        assert VECTOR_DB_CONFIG["overlap_ratio"] == 0.15

    def test_chars_per_token_value(self):
        """Verify chars_per_token value is 4 (average chars/token ratio)"""
        assert VECTOR_DB_CONFIG["chars_per_token"] == 4

    def test_no_deprecated_chunk_params(self):
        """Verify deprecated character-based parameters are removed"""
        # Check that previously used parameters are removed
        deprecated_keys = ["chunk_size", "chunk_overlap", "chunk_overlap_tokens"]

        for key in deprecated_keys:
            assert key not in VECTOR_DB_CONFIG, f"Deprecated parameter '{key}' still exists in config"

    def test_calculated_chunk_size(self):
        """Verify token-based calculated chunk_size is correct"""
        chunk_tokens = VECTOR_DB_CONFIG["chunk_tokens"]
        chars_per_token = VECTOR_DB_CONFIG["chars_per_token"]

        calculated_chunk_size = chunk_tokens * chars_per_token
        expected_chunk_size = 512 * 4  # 2048

        assert calculated_chunk_size == expected_chunk_size
        assert calculated_chunk_size == 2048

    def test_calculated_chunk_overlap(self):
        """Verify token-based calculated chunk_overlap is correct"""
        chunk_tokens = VECTOR_DB_CONFIG["chunk_tokens"]
        chars_per_token = VECTOR_DB_CONFIG["chars_per_token"]
        overlap_ratio = VECTOR_DB_CONFIG["overlap_ratio"]

        chunk_size = chunk_tokens * chars_per_token
        calculated_overlap = int(chunk_size * overlap_ratio)
        expected_overlap = int(2048 * 0.15)  # 307

        assert calculated_overlap == expected_overlap
        assert calculated_overlap == 307

    def test_overlap_token_calculation(self):
        """Verify overlap calculation in token count is correct"""
        chunk_tokens = VECTOR_DB_CONFIG["chunk_tokens"]
        overlap_ratio = VECTOR_DB_CONFIG["overlap_ratio"]

        overlap_tokens = int(chunk_tokens * overlap_ratio)
        expected_overlap_tokens = int(512 * 0.15)  # 76.8 -> 76

        assert overlap_tokens == expected_overlap_tokens
        assert 76 <= overlap_tokens <= 77  # Allow rounding error

    def test_config_consistency(self):
        """Verify configuration values are logically consistent"""
        chunk_tokens = VECTOR_DB_CONFIG["chunk_tokens"]
        overlap_ratio = VECTOR_DB_CONFIG["overlap_ratio"]
        chars_per_token = VECTOR_DB_CONFIG["chars_per_token"]

        # chunk_tokens is positive
        assert chunk_tokens > 0

        # overlap_ratio is between 0 and 1
        assert 0 < overlap_ratio < 1

        # chars_per_token is typically between 2-6
        assert 2 <= chars_per_token <= 6

        # Overlap is less than chunk_size
        overlap_tokens = int(chunk_tokens * overlap_ratio)
        assert overlap_tokens < chunk_tokens

    def test_tokenizer_model_config(self):
        """Verify tokenizer model is set to BGE-M3"""
        assert "tokenizer_model" in VECTOR_DB_CONFIG
        assert VECTOR_DB_CONFIG["tokenizer_model"] == "BAAI/bge-m3"

    def test_single_source_of_truth(self):
        """Verify token-based parameters are the single source of truth"""
        # Only required parameters should exist
        required_params = {"chunk_tokens", "overlap_ratio", "chars_per_token"}
        chunk_params = {k for k in VECTOR_DB_CONFIG.keys()
                       if "chunk" in k.lower() or "overlap" in k.lower() or "chars_per_token" in k}

        # chunk-related parameters should include required_params
        assert required_params.issubset(chunk_params), f"Missing params: {required_params - chunk_params}"

        # deprecated parameters should not exist
        deprecated_params = {"chunk_size", "chunk_overlap", "chunk_overlap_tokens"}
        assert not deprecated_params.intersection(chunk_params), f"Deprecated params found: {deprecated_params.intersection(chunk_params)}"

        print(f"\n📏 Chunk-related parameters: {chunk_params}")
        print(f"✅ Token-based single source of truth: {required_params}")
