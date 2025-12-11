"""Model registry and vector database configurations."""

from .api_config import load_dotenv
import os

load_dotenv()

MODEL_REGISTRY = {
    "embedding": {
        "default": "BAAI/bge-m3",
        "tei": "BAAI/bge-m3",
        "tokenizer": "BAAI/bge-m3",
        "local": "all-MiniLM-L6-v2"
    },
    "reranker": {
        "default": "BAAI/bge-reranker-v2-m3"
    }
}

VECTOR_DB_CONFIG = {
    "root_dir": "./knowledge_bases",
    "tei_enabled": os.getenv("TEI_ENABLED", "true").lower() == "true",
    "tei_base_url": os.getenv("TEI_BASE_URL", "http://localhost:8080"),
    "tei_timeout": int(os.getenv("TEI_TIMEOUT", "30")),
    "tei_model_name": MODEL_REGISTRY["embedding"]["tei"],
    "embedding_dimension": 1024,
    "local_embedding_model": MODEL_REGISTRY["embedding"]["local"],
    "tokenizer_model": MODEL_REGISTRY["embedding"]["tokenizer"],
    "chunk_tokens": 512,
    "overlap_ratio": 0.15,
    "chars_per_token": 4,
    "default_rerank_model": MODEL_REGISTRY["reranker"]["default"]
}

SEARCH_INTENSITY_CONFIG = {
    "exact": {
        "init": 10,
        "final": 5,
        "similarity_threshold": 0.3
    },
    "standard": {
        "init": 20,
        "final": 12,
        "similarity_threshold": 0.25
    },
    "comprehensive": {
        "init": 40,
        "final": 25,
        "similarity_threshold": 0.2
    }
}
