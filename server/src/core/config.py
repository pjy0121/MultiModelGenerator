import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
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
    "similarity_threshold": 0.85,
    "search_intensity_map": {
        "very_low":  {"init": 7, "final": 5},
        "low":       {"init": 10, "final": 7},
        "medium":    {"init": 20, "final": 10},
        "high":      {"init": 30, "final": 15},
        "very_high": {"init": 50, "final": 20}
    }
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

# 유틸리티 함수들
def is_llm_provider_available(provider: str) -> bool:
    """LLM Provider가 사용 가능한지 확인"""
    return bool(API_KEYS.get(provider))

def get_kb_path(kb_name: str) -> str:
    """지식 베이스별 경로 반환"""
    return os.path.join(VECTOR_DB_CONFIG["root_dir"], kb_name)

def _get_kb_list_sync() -> list:
    """동기 방식으로 지식 베이스 목록 반환 (내부 사용)"""
    root_dir = VECTOR_DB_CONFIG["root_dir"]
    if not os.path.exists(root_dir):
        return []
    
    kb_list = []
    for item in os.listdir(root_dir):
        kb_path = os.path.join(root_dir, item)
        if os.path.isdir(kb_path):
            kb_list.append(item)
    
    return sorted(kb_list)

async def get_kb_list() -> list:
    """존재하는 지식 베이스 목록 반환 (비동기)"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, _get_kb_list_sync)

def get_kb_list_sync() -> list:
    """동기 방식으로 지식 베이스 목록 반환 (호환성 유지)"""
    return _get_kb_list_sync()
