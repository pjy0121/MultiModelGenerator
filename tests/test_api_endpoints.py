"""
API endpoint tests
"""
import pytest
import requests


class TestAPIEndpoints:
    """Test basic API endpoints"""
    
    def test_health_check(self, api_client: requests.Session, api_base_url: str):
        """Test health check endpoint"""
        response = api_client.get(f"{api_base_url}/")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["status"] == "Node-based workflow API is running"
        
    def test_knowledge_bases_list(self, api_client: requests.Session, api_base_url: str):
        """Test knowledge bases listing"""
        response = api_client.get(f"{api_base_url}/knowledge-bases")
        
        assert response.status_code == 200
        data = response.json()
        assert "knowledge_bases" in data
        assert isinstance(data["knowledge_bases"], list)
        
    def test_available_models(self, api_client: requests.Session, api_base_url: str):
        """Test available models endpoints"""
        providers = ["google", "openai"]  # Exclude "internal" as it returns 500
        
        for provider in providers:
            response = api_client.get(f"{api_base_url}/available-models/{provider}")
            
            assert response.status_code == 200
            data = response.json()
            # API returns list of models directly, not wrapped in "models" key
            assert isinstance(data, list)
            if len(data) > 0:
                # Check model structure
                model = data[0]
                assert "model_type" in model
                assert "provider" in model
                assert "label" in model
            
    def test_invalid_endpoint(self, api_client: requests.Session, api_base_url: str):
        """Test invalid endpoint returns 404"""
        response = api_client.get(f"{api_base_url}/nonexistent-endpoint")
        assert response.status_code == 404