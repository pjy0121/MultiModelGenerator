"""
TEI (Text Embeddings Inference) Client
BAAI/bge-m3 모델을 위한 TEI 서버 클라이언트
"""
import os
import requests
import numpy as np
from typing import List, Optional
from chromadb import Documents, EmbeddingFunction, Embeddings


class TEIClient:
    """TEI 서버와 통신하는 클라이언트"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Args:
            base_url: TEI 서버 주소
            token: 인증 토큰 (선택사항)
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self.embed_url = f"{self.base_url}/embed"
        
    def test_connection(self) -> tuple[bool, str]:
        """
        TEI 서버 연결 테스트
        
        Returns:
            (성공 여부, 메시지)
        """
        try:
            response = requests.post(
                self.embed_url,
                json={"inputs": ["test"]},
                headers=self._get_headers(),
                timeout=5
            )
            
            if response.status_code == 200:
                return True, "TEI 서버 연결 성공"
            else:
                return False, f"TEI 서버 응답 오류: {response.status_code} - {response.text}"
                
        except requests.exceptions.ConnectionError:
            return False, f"TEI 서버에 연결할 수 없습니다: {self.base_url}"
        except requests.exceptions.Timeout:
            return False, f"TEI 서버 응답 시간 초과 (timeout={self.timeout}s)"
        except Exception as e:
            return False, f"TEI 서버 연결 테스트 실패: {str(e)}"
    
    def _get_headers(self) -> dict:
        """HTTP 헤더 생성"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트를 임베딩 벡터로 변환
        
        Args:
            texts: 임베딩할 텍스트 리스트
            
        Returns:
            임베딩 벡터 리스트 (각 벡터는 1024차원)
        """
        if not texts:
            return []
        
        try:
            response = requests.post(
                self.embed_url,
                json={"inputs": texts},
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            embeddings = response.json()
            return embeddings
            
        except requests.exceptions.RequestException as e:
            error_msg = f"TEI 임베딩 요청 실패: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\n서버 응답: {e.response.text}"
            raise RuntimeError(error_msg)


class TEIEmbeddingFunction(EmbeddingFunction):
    """ChromaDB용 TEI 임베딩 함수"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Args:
            base_url: TEI 서버 주소
            token: 인증 토큰 (선택사항)
            timeout: 요청 타임아웃 (초)
        """
        self.client = TEIClient(base_url=base_url, token=token, timeout=timeout)
    
    def __call__(self, input: Documents) -> Embeddings:
        """
        ChromaDB가 호출하는 임베딩 함수
        
        Args:
            input: 텍스트 문서 리스트
            
        Returns:
            임베딩 벡터 리스트
        """
        embeddings = self.client.encode(input)
        return embeddings


def get_tei_client_from_config() -> Optional[TEIClient]:
    """
    설정에서 TEI 클라이언트 생성
    
    Returns:
        TEIClient 인스턴스 또는 None (TEI가 비활성화된 경우)
    """
    from src.core.config import Config
    
    config = Config.get_vector_db_config()
    
    if not config.get('tei_enabled', False):
        return None
    
    base_url = config.get('tei_base_url', 'http://localhost:8080')
    token = os.getenv('TEI_TOKEN')
    timeout = config.get('tei_timeout', 30)
    
    return TEIClient(base_url=base_url, token=token, timeout=timeout)


def get_tei_embedding_function() -> Optional[TEIEmbeddingFunction]:
    """
    설정에서 TEI 임베딩 함수 생성
    
    Returns:
        TEIEmbeddingFunction 인스턴스 또는 None (TEI가 비활성화된 경우)
    """
    from src.core.config import Config
    
    config = Config.get_vector_db_config()
    
    if not config.get('tei_enabled', False):
        return None
    
    base_url = config.get('tei_base_url', 'http://localhost:8080')
    token = os.getenv('TEI_TOKEN')
    timeout = config.get('tei_timeout', 30)
    
    return TEIEmbeddingFunction(base_url=base_url, token=token, timeout=timeout)
