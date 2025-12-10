import os
from dotenv import load_dotenv

load_dotenv()

# API 키 설정
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "google": os.getenv("GOOGLE_API_KEY"),
    "internal": os.getenv("INTERNAL_API_KEY")
}

# 내부 LLM 설정
INTERNAL_LLM_CONFIG = {
    "api_endpoint": os.getenv("INTERNAL_API_ENDPOINT"),
    "api_key": os.getenv("INTERNAL_API_KEY"),
    "model_name": os.getenv("INTERNAL_MODEL_NAME"),
    "timeout": 30
}

# LLM 설정
LLM_CONFIG = {
    "supported_providers": ["openai", "google", "internal"],
    "default_provider": "google", 
    "default_model": "gemini-2.0-flash",
    "default_temperature": 0.1,
    "chunk_processing_size": 10,
    "simulation_sleep_interval": 0.1
}

# 벡터 DB 설정 (BGE-M3 최적화)
VECTOR_DB_CONFIG = {
    "root_dir": "./knowledge_bases",
    # TEI (Text Embeddings Inference) 설정
    "tei_enabled": os.getenv("TEI_ENABLED", "true").lower() == "true",  # TEI 사용 여부
    "tei_base_url": os.getenv("TEI_BASE_URL", "http://localhost:8080"),  # TEI 서버 주소
    "tei_timeout": int(os.getenv("TEI_TIMEOUT", "30")),  # TEI 요청 타임아웃 (초)
    "tei_model_name": "BAAI/bge-m3",  # TEI 서버에서 사용하는 모델
    "embedding_dimension": 1024,  # BAAI/bge-m3 임베딩 차원
    # 로컬 embedding 설정 (TEI 사용 안 할 때 fallback)
    "local_embedding_model": "all-MiniLM-L6-v2",  # name or path
    # 문서 처리 설정 (BGE-M3 최적화: 512 tokens, 15% overlap)
    "chunk_size": 2048,              # 512 tokens * 4 characters/token
    "chunk_overlap": 307,            # 15% overlap (2048 * 0.15 ≈ 307)
    # Reranker 설정
    "default_rerank_model": "BAAI/bge-reranker-v2-m3"  # BGE-M3 최적화 reranker
    # similarity_threshold는 SearchIntensity에서 동적으로 결정됨
}

# 노드 실행 엔진 설정
NODE_EXECUTION_CONFIG = {
    "stream_timeout": 10.0,           # 스트림 완료 대기 시간 (초)
    "stream_poll_timeout": 0.1,       # 스트림 폴링 간격 (초) 
    "max_tokens_default": 128000,     # LLM 응답 기본 토큰 수
    "score_decay_factor": 0.1         # VectorStore mock 점수 감소율
}

# Admin 설정 
ADMIN_CONFIG = {
    "chunk_size_min": 512,           # 최소 청크 크기
    "chunk_size_max": 8192,          # 최대 청크 크기  
    "chunk_size_default": 2048,      # 기본 청크 크기
    "chunk_overlap_ratio": 0.25      # 기본 오버랩 비율 (25%)
}
