import os
from dotenv import load_dotenv

load_dotenv()

# API 키 설정
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "google": os.getenv("GOOGLE_API_KEY")
}

# 서버 설정
SERVER_CONFIG = {
    "host": os.getenv("API_HOST", "localhost"),
    "port": int(os.getenv("API_PORT", "5001"))
}

# LLM 설정
LLM_CONFIG = {
    "supported_providers": ["openai", "google"],
    "default_provider": "google", 
    "default_model": "gemini-2.0-flash",
    "default_temperature": 0.1,
    "chunk_processing_size": 10,
    "simulation_sleep_interval": 0.1
}



# 벡터 DB 설정
VECTOR_DB_CONFIG = {
    "root_dir": "./knowledge_bases",
    "chunk_size": 6000,
    "chunk_overlap": 100,
    "similarity_threshold": 0.85,
    "search_timeout": 10.0,  # 검색 타임아웃 (초)
    "search_intensity_map": {
        "very_low":  {"init": 8, "final": 3},
        "low":       {"init": 12, "final": 5},
        "medium":    {"init": 15, "final": 7},   # 기본값 더 가볍게
        "high":      {"init": 25, "final": 12},
        "very_high": {"init": 40, "final": 18}
    }
}

# 유틸리티 함수들
def is_llm_provider_available(provider: str) -> bool:
    """LLM 제공자가 사용 가능한지 확인"""
    return bool(API_KEYS.get(provider))

def get_kb_path(kb_name: str) -> str:
    """지식 베이스별 경로 반환"""
    return os.path.join(VECTOR_DB_CONFIG["root_dir"], kb_name)

def get_kb_list() -> list:
    """존재하는 지식 베이스 목록 반환"""
    root_dir = VECTOR_DB_CONFIG["root_dir"]
    if not os.path.exists(root_dir):
        return []
    
    kb_list = []
    for item in os.listdir(root_dir):
        kb_path = os.path.join(root_dir, item)
        if os.path.isdir(kb_path):
            kb_list.append(item)
    
    return sorted(kb_list)
