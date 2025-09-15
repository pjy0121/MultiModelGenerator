import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """애플리케이션 설정"""
    
    # LLM API 키
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # 지원되는 LLM 제공자
    SUPPORTED_LLM_PROVIDERS = ["openai", "google"]
    
    # 문서 청킹 설정
    CHUNK_SIZE = 6000
    CHUNK_OVERLAP = 100
    
    # 벡터 DB 설정
    VECTOR_DB_ROOT = "./knowledge_bases"
    
    # 검색 설정
    SEARCH_TOP_K = 50
    SEARCH_MAX_TOP_K = 100
    SEARCH_SIMILARITY_THRESHOLD = 0.9
    SEARCH_ENABLE_COMPREHENSIVE = True
    
    @classmethod
    def is_llm_provider_available(cls, provider: str) -> bool:
        """LLM 제공자가 사용 가능한지 확인"""
        if provider == "openai":
            return bool(cls.OPENAI_API_KEY)
        elif provider == "google":
            return bool(cls.GOOGLE_API_KEY)
        return False
    
    @staticmethod
    def get_kb_path(kb_name: str) -> str:
        """지식 베이스 경로 반환"""
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
