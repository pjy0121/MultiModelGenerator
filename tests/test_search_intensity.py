"""
SearchIntensity system test - 3-level search intensity verification
"""
import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.models import SearchIntensity


class TestSearchIntensity:
    """SearchIntensity enum and parameter tests"""

    def test_search_intensity_values(self):
        """Verify SearchIntensity enum values"""
        assert SearchIntensity.EXACT == "exact"
        assert SearchIntensity.STANDARD == "standard"
        assert SearchIntensity.COMPREHENSIVE == "comprehensive"

    def test_exact_search_params(self):
        """Verify EXACT search parameters (BGE-M3 optimized)"""
        params = SearchIntensity.get_search_params(SearchIntensity.EXACT)

        assert "init" in params
        assert "final" in params
        assert params["init"] == 10
        assert params["final"] == 5
        assert params["init"] > params["final"], "Initial search should be more than rerank"

        # Ratio verification (approximately 2:1)
        ratio = params["init"] / params["final"]
        assert 1.5 <= ratio <= 2.5, f"Inappropriate ratio: {ratio}"

    def test_standard_search_params(self):
        """Verify STANDARD search parameters (default, BGE-M3 optimized)"""
        params = SearchIntensity.get_search_params(SearchIntensity.STANDARD)

        assert params["init"] == 20
        assert params["final"] == 12
        assert params["init"] > params["final"]

        # Ratio verification
        ratio = params["init"] / params["final"]
        assert 1.5 <= ratio <= 2.0, f"Inappropriate ratio: {ratio}"

    def test_comprehensive_search_params(self):
        """Verify COMPREHENSIVE search parameters (BGE-M3 optimized)"""
        params = SearchIntensity.get_search_params(SearchIntensity.COMPREHENSIVE)

        assert params["init"] == 40
        assert params["final"] == 25
        assert params["init"] > params["final"]

        # Ratio verification
        ratio = params["init"] / params["final"]
        assert 1.5 <= ratio <= 2.0, f"Inappropriate ratio: {ratio}"

    def test_search_params_ordering(self):
        """Verify search intensity ordering (EXACT < STANDARD < COMPREHENSIVE)"""
        exact = SearchIntensity.get_search_params(SearchIntensity.EXACT)
        standard = SearchIntensity.get_search_params(SearchIntensity.STANDARD)
        comprehensive = SearchIntensity.get_search_params(SearchIntensity.COMPREHENSIVE)

        # Initial search count ordering
        assert exact["init"] < standard["init"] < comprehensive["init"]

        # Final search count ordering
        assert exact["final"] < standard["final"] < comprehensive["final"]

    def test_get_default(self):
        """Verify default search intensity is STANDARD"""
        default = SearchIntensity.get_default()
        assert default == SearchIntensity.STANDARD

    def test_from_top_k(self):
        """Test search intensity inference from top_k value (BGE-M3 optimized)"""
        # EXACT range (<=12)
        assert SearchIntensity.from_top_k(5) == SearchIntensity.EXACT
        assert SearchIntensity.from_top_k(10) == SearchIntensity.EXACT
        assert SearchIntensity.from_top_k(12) == SearchIntensity.EXACT

        # STANDARD range (13-30)
        assert SearchIntensity.from_top_k(15) == SearchIntensity.STANDARD
        assert SearchIntensity.from_top_k(20) == SearchIntensity.STANDARD
        assert SearchIntensity.from_top_k(30) == SearchIntensity.STANDARD

        # COMPREHENSIVE range (>30)
        assert SearchIntensity.from_top_k(35) == SearchIntensity.COMPREHENSIVE
        assert SearchIntensity.from_top_k(40) == SearchIntensity.COMPREHENSIVE
        assert SearchIntensity.from_top_k(100) == SearchIntensity.COMPREHENSIVE

    def test_invalid_intensity_defaults_to_standard(self):
        """Invalid search intensity value falls back to STANDARD"""
        params = SearchIntensity.get_search_params("invalid")
        standard_params = SearchIntensity.get_search_params(SearchIntensity.STANDARD)

        assert params == standard_params

    def test_corpus_size_appropriateness(self):
        """Verify appropriateness for 700 chunk corpus (BGE-M3 optimized)"""
        corpus_size = 700

        exact = SearchIntensity.get_search_params(SearchIntensity.EXACT)
        standard = SearchIntensity.get_search_params(SearchIntensity.STANDARD)
        comprehensive = SearchIntensity.get_search_params(SearchIntensity.COMPREHENSIVE)

        # Initial search ratio (0.5-10% is appropriate - optimized for BGE-M3)
        assert 0.005 <= exact["init"] / corpus_size <= 0.10
        assert 0.005 <= standard["init"] / corpus_size <= 0.10
        assert 0.005 <= comprehensive["init"] / corpus_size <= 0.10

        # Final search ratio (0.5-5% is appropriate - high quality matching)
        assert 0.005 <= exact["final"] / corpus_size <= 0.05
        assert 0.005 <= standard["final"] / corpus_size <= 0.05
        assert 0.005 <= comprehensive["final"] / corpus_size <= 0.05

        print(f"\n📊 Ratio based on 700 chunks (BGE-M3 optimized):")
        print(f"  EXACT: {exact['init']/corpus_size*100:.1f}% → {exact['final']/corpus_size*100:.1f}%")
        print(f"  STANDARD: {standard['init']/corpus_size*100:.1f}% → {standard['final']/corpus_size*100:.1f}%")
        print(f"  COMPREHENSIVE: {comprehensive['init']/corpus_size*100:.1f}% → {comprehensive['final']/corpus_size*100:.1f}%")

    def test_similarity_threshold_in_params(self):
        """Verify similarity_threshold exists (for filtering irrelevant results)"""
        exact = SearchIntensity.get_search_params(SearchIntensity.EXACT)
        standard = SearchIntensity.get_search_params(SearchIntensity.STANDARD)
        comprehensive = SearchIntensity.get_search_params(SearchIntensity.COMPREHENSIVE)

        # similarity_threshold field must exist
        assert "similarity_threshold" in exact, "EXACT is missing similarity_threshold"
        assert "similarity_threshold" in standard, "STANDARD is missing similarity_threshold"
        assert "similarity_threshold" in comprehensive, "COMPREHENSIVE is missing similarity_threshold"

        # Value range check (0.0~1.0)
        assert 0.0 <= exact["similarity_threshold"] <= 1.0
        assert 0.0 <= standard["similarity_threshold"] <= 1.0
        assert 0.0 <= comprehensive["similarity_threshold"] <= 1.0

        # Search intensity ordering (EXACT > STANDARD > COMPREHENSIVE)
        assert exact["similarity_threshold"] > standard["similarity_threshold"]
        assert standard["similarity_threshold"] > comprehensive["similarity_threshold"]

        print(f"\n🎯 Similarity Thresholds:")
        print(f"  EXACT: {exact['similarity_threshold']} (high precision)")
        print(f"  STANDARD: {standard['similarity_threshold']} (balanced)")
        print(f"  COMPREHENSIVE: {comprehensive['similarity_threshold']} (broad search)")

