"""
TEI (Text Embeddings Inference) Client
TEI server client for BAAI/bge-m3 model
"""
import os
import requests
import numpy as np
from typing import List, Optional
from chromadb import Documents, EmbeddingFunction, Embeddings


class TEIClient:
    """Client for communicating with TEI server"""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Args:
            base_url: TEI server address
            token: Authentication token (optional)
            timeout: Request timeout (seconds)
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self.embed_url = f"{self.base_url}/embed"
        
    def test_connection(self) -> tuple[bool, str]:
        """
        Test TEI server connection

        Returns:
            (success, message)
        """
        try:
            response = requests.post(
                self.embed_url,
                json={"inputs": ["test"]},
                headers=self._get_headers(),
                timeout=5
            )

            if response.status_code == 200:
                return True, "TEI server connection successful"
            else:
                return False, f"TEI server response error: {response.status_code} - {response.text}"

        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to TEI server: {self.base_url}"
        except requests.exceptions.Timeout:
            return False, f"TEI server response timeout (timeout={self.timeout}s)"
        except Exception as e:
            return False, f"TEI server connection test failed: {str(e)}"

    def _get_headers(self) -> dict:
        """Generate HTTP headers"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        """
        Convert text to embedding vectors

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (each vector is 1024-dimensional)
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
            error_msg = f"TEI embedding request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\nServer response: {e.response.text}"
            raise RuntimeError(error_msg)


class TEIEmbeddingFunction(EmbeddingFunction):
    """TEI embedding function for ChromaDB"""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Args:
            base_url: TEI server address
            token: Authentication token (optional)
            timeout: Request timeout (seconds)
        """
        self.client = TEIClient(base_url=base_url, token=token, timeout=timeout)

    def __call__(self, input: Documents) -> Embeddings:
        """
        Embedding function called by ChromaDB

        Args:
            input: List of text documents

        Returns:
            List of embedding vectors
        """
        embeddings = self.client.encode(input)
        return embeddings


def get_tei_client_from_config() -> Optional[TEIClient]:
    """
    Create TEI client from config

    Returns:
        TEIClient instance or None (if TEI is disabled)
    """
    from ..config import VECTOR_DB_CONFIG

    if not VECTOR_DB_CONFIG.get('tei_enabled', False):
        return None

    base_url = VECTOR_DB_CONFIG.get('tei_base_url', 'http://localhost:8080')
    token = os.getenv('TEI_TOKEN')
    timeout = VECTOR_DB_CONFIG.get('tei_timeout', 30)

    return TEIClient(base_url=base_url, token=token, timeout=timeout)


def get_tei_embedding_function() -> Optional[TEIEmbeddingFunction]:
    """
    Create TEI embedding function from config

    Returns:
        TEIEmbeddingFunction instance or None (if TEI is disabled)
    """
    from ..config import VECTOR_DB_CONFIG

    if not VECTOR_DB_CONFIG.get('tei_enabled', False):
        return None

    base_url = VECTOR_DB_CONFIG.get('tei_base_url', 'http://localhost:8080')
    token = os.getenv('TEI_TOKEN')
    timeout = VECTOR_DB_CONFIG.get('tei_timeout', 30)

    return TEIEmbeddingFunction(base_url=base_url, token=token, timeout=timeout)
