"""Enum types for workflow models."""

from enum import Enum
from typing import Dict, List
from ..config import SEARCH_INTENSITY_CONFIG


class NodeType(str, Enum):
    INPUT = "input-node"
    GENERATION = "generation-node"
    ENSEMBLE = "ensemble-node"
    VALIDATION = "validation-node"
    CONTEXT = "context-node"
    OUTPUT = "output-node"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    INTERNAL = "internal"
    
    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """Return list of supported LLM providers"""
        return [cls.OPENAI, cls.GOOGLE, cls.INTERNAL]

    @classmethod
    def get_default_provider(cls) -> str:
        """Return default LLM provider"""
        return cls.GOOGLE


class SearchIntensity(str, Enum):
    EXACT = "exact"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    
    @classmethod
    def get_search_params(cls, intensity: str) -> Dict[str, any]:
        """Return parameters based on search mode (based on BGE-M3 actual similarity distribution)

        Top-K + Similarity Threshold parallel filtering:
        1. init: Initial search count (fetch from ChromaDB)
        2. similarity_threshold: Minimum similarity (cosine similarity 0.0~1.0)
        3. final: Final count after Reranker

        Threshold setting rationale (based on empirical data):
        - BGE-M3 actual similarity range: related documents at 0.2~0.4 level
        - Theoretical recommendations (0.8/0.65/0.5) are too high, filtering out most results
        - Practical values (0.3/0.25/0.2) adjusted to get appropriate search results

        - EXACT (high precision): init=10, final=5, threshold=0.3 (30%+ similarity)
          Use cases: "exact command ID", "specific spec"
          Characteristic: Select only clearly related documents

        - STANDARD (standard search): init=20, final=12, threshold=0.25 (25%+ similarity) [default]
          Use cases: "general features", "standard procedures"
          Characteristic: Include reasonably related documents, optimal for most cases

        - COMPREHENSIVE (broad search): init=40, final=25, threshold=0.2 (20%+ similarity)
          Use cases: "overall mechanisms", "exploratory research"
          Characteristic: Include all documents with any relevance possibility

        * Similarity Threshold: Filter irrelevant results (return at least 1 to prevent empty results)
        * With Reranker: LLM-based reranking of init results to final after threshold
        * Without Reranker: Return only threshold-filtered results
        """
        intensity_map = {
            cls.EXACT: SEARCH_INTENSITY_CONFIG["exact"],
            cls.STANDARD: SEARCH_INTENSITY_CONFIG["standard"],
            cls.COMPREHENSIVE: SEARCH_INTENSITY_CONFIG["comprehensive"]
        }
        return intensity_map.get(intensity, intensity_map[cls.STANDARD])
    
    @classmethod
    def from_top_k(cls, top_k: int) -> str:
        """Return appropriate search mode based on top_k value (criterion: final count)"""
        if top_k <= 12:
            return cls.EXACT
        elif top_k <= 30:
            return cls.STANDARD
        else:
            return cls.COMPREHENSIVE

    @classmethod
    def get_default(cls) -> str:
        """Return default search mode (balanced standard search)"""
        return cls.STANDARD
