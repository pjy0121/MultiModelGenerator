import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM API 설정
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # LLM 제공자 설정
    SUPPORTED_LLM_PROVIDERS = ["openai", "google"]
    
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
    
    # 검색 설정 - VectorDB 검색 성능 및 포괄성 제어
    SEARCH_TOP_K = 50  # 기본 검색 결과 수 (더 많은 문서 검색으로 포괄성 향상)
    SEARCH_MAX_TOP_K = 100  # 최대 검색 결과 수 (시스템 부하 방지를 위한 상한선)
    SEARCH_SIMILARITY_THRESHOLD = 0.9  # 유사도 임계값 (0.8 → 0.9로 완화하여 더 관대한 검색)
    SEARCH_ENABLE_COMPREHENSIVE = True  # 포괄적 검색 모드 (전체 문서의 80% 검색, 시간은 오래 걸리지만 더 정확한 결과)
    
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
