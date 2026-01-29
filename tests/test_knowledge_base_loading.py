"""
Test: Comprehensive Knowledge Base Loading Tests
"""
import pytest
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.services.vector_store_service import VectorStoreService


class TestKnowledgeBaseLoading:
    """Comprehensive knowledge base loading tests"""

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

    @pytest.fixture
    async def available_kbs_data(self, vector_service):
        """List of available knowledge bases"""
        return await vector_service.get_knowledge_bases()

    @pytest.mark.asyncio
    async def test_knowledge_base_availability(self, vector_service):
        """Test knowledge base availability"""
        available_kbs = await vector_service.get_knowledge_bases()
        assert isinstance(available_kbs, list), "KB list is not a list"
        assert len(available_kbs) > 0, "No available knowledge bases"

        print(f"Available knowledge bases: {available_kbs}")

    @pytest.mark.asyncio
    async def test_all_knowledge_bases_info(self, vector_service):
        """Test loading info for all knowledge bases"""
        available_kbs = await vector_service.get_knowledge_bases()

        if not available_kbs:
            pytest.skip("No available knowledge bases")

        for kb_name in available_kbs:
            print(f"Retrieving info for {kb_name}...")

            try:
                kb_info = await vector_service.get_knowledge_base_info(kb_name)

                # Verify basic info
                assert kb_info['name'] == kb_name, f"{kb_name}: name mismatch"
                assert kb_info['exists'] is True, f"{kb_name}: does not exist"
                assert kb_info['count'] >= 0, f"{kb_name}: document count is negative"

                print(f"{kb_name}:")
                print(f"   - Document count: {kb_info['count']}")
                print(f"   - Path: {kb_info['path']}")
                print(f"   - Exists: {kb_info['exists']}")

            except Exception as e:
                pytest.fail(f"Failed to retrieve info for {kb_name}: {e}")

    @pytest.mark.asyncio
    async def test_knowledge_base_search_functionality(self, vector_service):
        """Test knowledge base search functionality"""
        available_kbs = await vector_service.get_knowledge_bases()

        if not available_kbs:
            pytest.skip("No available knowledge bases")

        # Search test with first KB
        first_kb = available_kbs[0]

        try:
            # Simple search query test - search method returns Dict
            results = await vector_service.search(
                kb_name=first_kb,
                query="specification",
                search_intensity="standard"
            )

            assert isinstance(results, dict), "Search results is not a Dict"
            assert 'chunks' in results, "Results missing 'chunks' key"
            assert 'total_chunks' in results, "Results missing 'total_chunks' key"
            assert 'found_chunks' in results, "Results missing 'found_chunks' key"

            chunks = results['chunks']
            assert isinstance(chunks, list), "chunks is not a list"

            print(f"{first_kb} search test:")
            print(f"   - Query: 'specification'")
            print(f"   - Found chunks: {results['found_chunks']}")
            print(f"   - Total chunks: {results['total_chunks']}")

            # Verify structure if results exist
            if chunks:
                chunk = chunks[0]
                assert isinstance(chunk, str), "Search result is not a string"
                assert len(chunk) > 0, "Search result content is empty"

                print(f"   - First result preview: {chunk[:100]}...")

        except Exception as e:
            pytest.fail(f"{first_kb} search functionality test failed: {e}")

    @pytest.mark.asyncio
    async def test_knowledge_base_consistency(self, vector_service):
        """Test knowledge base consistency"""
        available_kbs = await vector_service.get_knowledge_bases()

        if not available_kbs:
            pytest.skip("No available knowledge bases")

        # Verify no duplicate KB names
        assert len(available_kbs) == len(set(available_kbs)), "Duplicate KB names exist"

        # Verify KB name format
        for kb_name in available_kbs:
            assert isinstance(kb_name, str), f"KB name is not a string: {kb_name}"
            assert len(kb_name) > 0, "Empty KB name exists"
            assert not kb_name.isspace(), "KB name with only whitespace exists"

        print(f"All KB name consistency verified: {len(available_kbs)} items")
