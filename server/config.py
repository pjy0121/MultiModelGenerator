import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
    PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
    
    # 청킹 설정
    CHUNK_SIZE = 6000
    CHUNK_OVERLAP = 100
    
    # 벡터 DB 설정 (여러 지식베이스 지원)
    VECTOR_DB_ROOT = "./knowledge_bases"
    
    # 검색 설정
    SEARCH_TOP_K = 5
    
    # 출력 설정
    OUTPUT_DIR = "./output"
    
    @staticmethod
    def get_kb_path(kb_name: str) -> str:
        """지식베이스별 경로 반환"""
        return os.path.join(Config.VECTOR_DB_ROOT, kb_name)
    
    @staticmethod
    def get_kb_list() -> list:
        """존재하는 지식베이스 목록 반환"""
        if not os.path.exists(Config.VECTOR_DB_ROOT):
            return []
        
        kb_list = []
        for item in os.listdir(Config.VECTOR_DB_ROOT):
            kb_path = os.path.join(Config.VECTOR_DB_ROOT, item)
            if os.path.isdir(kb_path):
                kb_list.append(item)
        
        return sorted(kb_list)
