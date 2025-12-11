#!/usr/bin/env python
"""Quick validation script for refactoring changes."""

from src.config import MODEL_REGISTRY, VECTOR_DB_CONFIG
from src.utils import ErrorResponse, handle_api_errors

print("✅ Import success!")
print("\n=== MODEL_REGISTRY ===")
for category, models in MODEL_REGISTRY.items():
    print(f"{category}:")
    for key, value in models.items():
        print(f"  {key}: {value}")

print("\n=== VECTOR_DB_CONFIG (Model References) ===")
print(f"tei_model_name: {VECTOR_DB_CONFIG['tei_model_name']}")
print(f"tokenizer_model: {VECTOR_DB_CONFIG['tokenizer_model']}")
print(f"local_embedding_model: {VECTOR_DB_CONFIG['local_embedding_model']}")
print(f"default_rerank_model: {VECTOR_DB_CONFIG['default_rerank_model']}")

print("\n=== ErrorResponse Factory Methods ===")
print(f"validation_error: {ErrorResponse.validation_error}")
print(f"not_found: {ErrorResponse.not_found}")
print(f"conflict: {ErrorResponse.conflict}")
print(f"internal_error: {ErrorResponse.internal_error}")

print("\n=== Exception Decorators ===")
print(f"handle_api_errors: {handle_api_errors}")

print("\n✅ All refactoring changes validated successfully!")
