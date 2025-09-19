import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 서버 설정
    API_HOST = os.getenv("API_HOST", "localhost")
    API_PORT = int(os.getenv("API_PORT", "5001"))
    API_BASE_URL = f"http://{API_HOST}:{API_PORT}"
    
    # 응답 타입 상수
    RESPONSE_TYPE_START = "start"
    RESPONSE_TYPE_STREAM = "stream"
    RESPONSE_TYPE_NODE_START = "node_start"
    RESPONSE_TYPE_NODE_COMPLETE = "node_complete"
    RESPONSE_TYPE_RESULT = "result"
    RESPONSE_TYPE_PARSED_RESULT = "parsed_result"
    RESPONSE_TYPE_ERROR = "error"
    RESPONSE_TYPE_COMPLETE = "complete"
    
    # 노드 타입 상수
    NODE_TYPE_INPUT = "input-node"
    NODE_TYPE_OUTPUT = "output-node"
    NODE_TYPE_GENERATION = "generation-node"
    NODE_TYPE_ENSEMBLE = "ensemble-node"
    NODE_TYPE_VALIDATION = "validation-node"
    
    # LLM API 설정
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # LLM 제공자 설정
    SUPPORTED_LLM_PROVIDERS = ["openai", "google"]
    DEFAULT_LLM_PROVIDER = "openai"
    DEFAULT_LLM_MODEL = "gpt-3.5-turbo"
    DEFAULT_LLM_TEMPERATURE = 0.1
    
    # 타임아웃 설정
    STREAM_TIMEOUT_SHORT = 0.1  # 스트림 대기 타임아웃 (초)
    STREAM_TIMEOUT_LONG = 10.0  # 긴 스트림 타임아웃 (초)
    SIMULATION_SLEEP_INTERVAL = 0.1  # 스트리밍 시뮬레이션 간격 (초)
    CHUNK_PROCESSING_SIZE = 10  # 스트리밍 청크 크기
    
    @classmethod
    def is_llm_provider_available(cls, provider: str) -> bool:
        """LLM 제공자가 사용 가능한지 확인 (API 키 존재 여부)"""
        if provider == "openai":
            return bool(cls.OPENAI_API_KEY)
        elif provider == "google":
            return bool(cls.GOOGLE_API_KEY)
        return False
    
    # 청킹 설정
    CHUNK_SIZE = 6000
    CHUNK_OVERLAP = 100
    
    # 벡터 DB 설정 (여러 지식 베이스 지원)
    VECTOR_DB_ROOT = "./knowledge_bases"
    
    # 검색 설정 - VectorDB 검색 및 재정렬(Re-rank) 제어
    SEARCH_SIMILARITY_THRESHOLD = 0.85  # 유사도 임계값 (재정렬 전 1차 필터링)
    
    SEARCH_INTENSITY_MAP = {
        "very_low":  {"init": 10, "final": 3},
        "low":       {"init": 15, "final": 4},
        "medium":    {"init": 20, "final": 5},
        "high":      {"init": 30, "final": 7},
        "very_high": {"init": 40, "final": 10}
    }
    
    # 출력 설정
    OUTPUT_DIR = "./output"
    
    @staticmethod
    def get_kb_path(kb_name: str) -> str:
        """지식 베이스별 경로 반환"""
        return os.path.join(Config.VECTOR_DB_ROOT, kb_name)
    
    @staticmethod
    def get_kb_list() -> list:
        """존재하는 지식 베이스 목록 반환"""
        if not os.path.exists(Config.VECTOR_DB_ROOT):
            return []
        
        kb_list = []
        for item in os.listdir(Config.VECTOR_DB_ROOT):
            kb_path = os.path.join(Config.VECTOR_DB_ROOT, item)
            if os.path.isdir(kb_path):
                kb_list.append(item)
        
        return sorted(kb_list)
