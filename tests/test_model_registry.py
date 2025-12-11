#!/usr/bin/env python
"""Test that services correctly use MODEL_REGISTRY."""

import asyncio
from src.services.rerank import ReRanker
from src.config import MODEL_REGISTRY

async def test_reranker():
    print("=== Testing ReRanker with MODEL_REGISTRY ===")
    
    # Test with default model from MODEL_REGISTRY
    reranker = ReRanker(provider="internal", model=None)
    print(f"✅ ReRanker initialized with model: {reranker.model_name}")
    print(f"   Expected: {MODEL_REGISTRY['reranker']['default']}")
    assert reranker.model_name == MODEL_REGISTRY['reranker']['default'], "Model mismatch!"
    
    # Test with explicit model
    custom_reranker = ReRanker(provider="internal", model="custom-model")
    print(f"✅ Custom ReRanker initialized with model: {custom_reranker.model_name}")
    assert custom_reranker.model_name == "custom-model", "Custom model not set!"
    
    print("\n✅ ReRanker MODEL_REGISTRY integration validated!")

if __name__ == "__main__":
    asyncio.run(test_reranker())
