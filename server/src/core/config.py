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
    "tei_enabled": os.getenv("TEI_ENABLED", "true").lower() == "true",
    "tei_base_url": os.getenv("TEI_BASE_URL", "http://localhost:8080"),
    "tei_timeout": int(os.getenv("TEI_TIMEOUT", "30")),
    "tei_model_name": "BAAI/bge-m3",
    "embedding_dimension": 1024,
    # 로컬 embedding 설정
    "local_embedding_model": "all-MiniLM-L6-v2",
    # BGE-M3 Tokenizer 설정
    "tokenizer_model": "BAAI/bge-m3",
    # 문서 처리 설정 (Token 기반 - 단일 진실 공급원)
    "chunk_tokens": 512,             # 청크 크기 (tokens)
    "overlap_ratio": 0.15,           # 오버랩 비율 (15%)
    "chars_per_token": 4,            # 토큰당 평균 문자 수 (계산용)
    # Reranker 설정
    "default_rerank_model": "BAAI/bge-reranker-v2-m3"
}

# 노드 실행 엔진 설정
NODE_EXECUTION_CONFIG = {
    "stream_timeout": 10.0,           # 스트림 완료 대기 시간 (초)
    "stream_poll_timeout": 0.1,       # 스트림 폴링 간격 (초) 
    "max_tokens_default": 128000,     # LLM 응답 기본 토큰 수
    "score_decay_factor": 0.1         # VectorStore mock 점수 감소율
}

# 검색 강도 설정 (Top-K + Similarity Threshold 병행)
# 임계값: BGE-M3 실제 유사도 분포 기반 (실측값 0.2~0.4 범위)
# - 이론적 권장값(0.8/0.65/0.5)은 실제로는 너무 높아 대부분 필터링됨
# - 실용적 값(0.3/0.2/0.1)으로 조정하여 적절한 검색 결과 확보
SEARCH_INTENSITY_CONFIG = {
    "exact": {
        "init": 10,                # 초기 검색 개수
        "final": 5,               # Rerank 후 최종 개수
        "similarity_threshold": 0.3  # 최소 유사도 (명확히 관련된 문서)
    },
    "standard": {
        "init": 20,
        "final": 12,
        "similarity_threshold": 0.2  # 어느 정도 관련성 (balanced, 기본값)
    },
    "comprehensive": {
        "init": 40,
        "final": 25,
        "similarity_threshold": 0.1  # 약간이라도 관련 가능성 (broad coverage)
    }
}

# Admin 설정 
ADMIN_CONFIG = {
    "chunk_size_min": 512,
    "chunk_size_max": 8192,
    "chunk_size_default": 2048,
    "chunk_overlap_ratio": 0.25
}
