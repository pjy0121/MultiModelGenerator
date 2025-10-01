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

# 벡터 DB 설정
VECTOR_DB_CONFIG = {
    "root_dir": "./knowledge_bases",
    "embedding_model": "all-MiniLM-L6-v2",  # name or path
    "chunk_size": 6000,
    "chunk_overlap": 100,
    "similarity_threshold": 0.85
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
