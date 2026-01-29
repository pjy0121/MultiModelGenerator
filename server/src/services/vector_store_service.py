"""
VectorStoreService - Simple wrapper service for managing VectorStore instances
"""

from typing import List, Dict, Optional
from .vector_store import VectorStore
from ..config import NODE_EXECUTION_CONFIG
from ..utils import get_kb_list


class VectorStoreService:
    """
    Simple wrapper service for managing VectorStore instances
    Delegates actual implementation to VectorStore class
    Provides instance caching and connection recovery for concurrent access issues
    """

    def __init__(self):
        """Initialize VectorStoreService (independent cache per instance)"""
        self._store_cache: Dict[str, VectorStore] = {}

    def get_vector_store(self, kb_name: str) -> VectorStore:
        """Return VectorStore instance per knowledge base (instance-level cache)"""
        if kb_name not in self._store_cache:
            self._store_cache[kb_name] = VectorStore(kb_name)
        return self._store_cache[kb_name]
    
    async def get_knowledge_bases(self) -> List[str]:
        """Return list of available knowledge bases (async)"""
        return await get_kb_list()

    async def search(
        self,
        kb_name: str,
        query: str,
        search_intensity: str = "standard",
        rerank_info: Optional[Dict] = None
    ) -> Dict:
        """Vector search (delegates to VectorStore, includes error recovery)

        Returns:
            Dict with 'chunks', 'total_chunks', 'found_chunks'
        """
        try:
            store = self.get_vector_store(kb_name)
            return await store.search(query, search_intensity, rerank_info)
        except Exception as e:
            print(f"⚠️ Error during search (KB: {kb_name}): {e}")
            # Remove cached instance and retry
            if kb_name in self._store_cache:
                print(f"🔄 Attempting to recreate VectorStore instance: {kb_name}")
                del self._store_cache[kb_name]
                store = self.get_vector_store(kb_name)
                return await store.search(query, search_intensity, rerank_info)
            else:
                raise e

    async def get_knowledge_base_info(self, kb_name: str) -> Dict:
        """Return knowledge base info (delegates to VectorStore, includes error recovery)"""
        try:
            store = self.get_vector_store(kb_name)
            return await store.get_knowledge_base_info()
        except Exception as e:
            print(f"⚠️ Error querying KB info (KB: {kb_name}): {e}")
            # Remove cached instance and retry
            if kb_name in self._store_cache:
                print(f"🔄 Attempting to recreate VectorStore instance: {kb_name}")
                del self._store_cache[kb_name]
                store = self.get_vector_store(kb_name)
                return await store.get_knowledge_base_info()
            else:
                raise e

    def close_and_remove_kb(self, kb_name: str):
        """Close VectorStore connection and remove from cache (call before delete/rename)"""
        if kb_name in self._store_cache:
            try:
                store = self._store_cache[kb_name]
                store.close()  # Close ChromaDB connection
                del self._store_cache[kb_name]
                print(f"✅ VectorStore '{kb_name}' removed from cache")
            except Exception as e:
                print(f"⚠️ Error removing VectorStore '{kb_name}': {e}")
                # Remove from cache even if error occurs
                if kb_name in self._store_cache:
                    del self._store_cache[kb_name]

    def close_all(self):
        """Close all VectorStore connections (call on server shutdown)"""
        for kb_name, store in list(self._store_cache.items()):
            try:
                store.close()
                print(f"✅ VectorStore '{kb_name}' connection closed")
            except Exception as e:
                print(f"⚠️ Error closing VectorStore '{kb_name}': {e}")
        self._store_cache.clear()


# Global instance removed - each request uses independent instance
# vector_store_service = VectorStoreService()  # Removed