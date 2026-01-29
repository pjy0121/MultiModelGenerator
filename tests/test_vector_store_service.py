"""
Test: VectorStoreService Tests
"""
import pytest
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.services.vector_store_service import VectorStoreService


class TestVectorStoreService:
    """VectorStoreService tests"""

    @pytest.fixture
    def vector_service(self):
        """VectorStoreService instance fixture"""
        return VectorStoreService()

    @pytest.fixture(autouse=True)
    def setup_working_directory(self):
        """Set up working directory for tests"""
        original_cwd = os.getcwd()
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server')
        os.chdir(server_path)
        yield
        os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_get_knowledge_bases(self, vector_service):
        """Test knowledge base list retrieval"""
        kb_list = await vector_service.get_knowledge_bases()

        assert isinstance(kb_list, list), "KB list is not a list"

        # Empty list is not an error (KB may not have been created yet)
        if len(kb_list) == 0:
            pytest.skip("No available knowledge bases (need to regenerate KB with TEI)")

        # Verify each item in KB list actually exists
        for kb in kb_list:
            kb_path = f"./knowledge_bases/{kb}"
            assert os.path.exists(kb_path), f"KB directory does not exist: {kb_path}"

        print(f"KB list ({len(kb_list)} items): {kb_list}")

    @pytest.mark.asyncio
    async def test_get_vector_store(self, vector_service):
        """Test getting VectorStore instance"""
        kb_list = await vector_service.get_knowledge_bases()

        if not kb_list:
            pytest.skip("No available KB")

        first_kb = kb_list[0]
        vs = vector_service.get_vector_store(first_kb)

        assert vs is not None, "VectorStore instance is None"
        assert vs.kb_name == first_kb, "KB name mismatch"

        # Caching test - same instance should be returned for same KB
        vs2 = vector_service.get_vector_store(first_kb)
        assert vs is vs2, "VectorStore instance not cached"

        print(f"VectorStore instance creation and caching successful: {first_kb}")

    @pytest.mark.asyncio
    async def test_get_knowledge_base_info(self, vector_service):
        """Test knowledge base info retrieval"""
        kb_list = await vector_service.get_knowledge_bases()

        if not kb_list:
            pytest.skip("No available KB")

        first_kb = kb_list[0]
        kb_info = await vector_service.get_knowledge_base_info(first_kb)

        # Verify info structure
        required_fields = ['name', 'count', 'path', 'exists']
        for field in required_fields:
            assert field in kb_info, f"KB info missing '{field}' field"

        # Verify info values
        assert kb_info['name'] == first_kb, "KB name mismatch"
        assert kb_info['exists'] is True, "KB marked as non-existent"
        assert kb_info['count'] >= 0, "Document count is negative"

        print(f"KB info retrieval successful: {kb_info}")

    @pytest.mark.asyncio
    async def test_search(self, vector_service):
        """Test vector search"""
        kb_list = await vector_service.get_knowledge_bases()

        if not kb_list:
            pytest.skip("No available KB")

        first_kb = kb_list[0]

        # Search test - search method returns Dict
        results = await vector_service.search(
            kb_name=first_kb,
            query="NVMe specification",
            search_intensity="standard"  # Standard search mode
        )

        # API change: Dict with 'chunks', 'total_chunks', 'found_chunks'
        assert isinstance(results, dict), "Search results is not a Dict"
        assert 'chunks' in results, "Results missing 'chunks' key"
        assert 'total_chunks' in results, "Results missing 'total_chunks' key"
        assert 'found_chunks' in results, "Results missing 'found_chunks' key"

        chunks = results['chunks']
        assert isinstance(chunks, list), "chunks is not a list"

        # Results should be a list of strings
        if chunks:
            assert isinstance(chunks[0], str), "Search result is not a string"

        print(f"Search test successful: {results['found_chunks']} results (total {results['total_chunks']} chunks)")
