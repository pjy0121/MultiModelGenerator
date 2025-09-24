"""
Workflow execution tests
"""
import pytest
import requests
import json


class TestWorkflowExecution:
    """Test workflow execution functionality"""
    
    def test_simple_workflow_execution(self, api_client: requests.Session, api_base_url: str, sample_workflow):
        """Test basic workflow execution"""
        payload = {
            "workflow": sample_workflow,
            "rerank_enabled": False
        }
        
        response = api_client.post(f"{api_base_url}/execute-workflow", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure based on actual API response
        assert "success" in data
        assert "final_output" in data
        assert "total_execution_time" in data
        assert "results" in data  # API returns "results" not "node_results"
        assert "execution_order" in data
        
        # Check execution metadata
        assert data["total_execution_time"] >= 0
        assert len(data["results"]) == 3  # input, generation, output nodes
        assert len(data["execution_order"]) == 3
        
    def test_workflow_with_rerank(self, api_client: requests.Session, api_base_url: str, sample_workflow):
        """Test workflow execution with rerank enabled"""
        payload = {
            "workflow": sample_workflow,
            "rerank_enabled": True
        }
        
        response = api_client.post(f"{api_base_url}/execute-workflow", json=payload)
        assert response.status_code == 200
        
    def test_invalid_workflow_structure(self, api_client: requests.Session, api_base_url: str):
        """Test workflow execution with invalid structure"""
        invalid_workflow = {
            "nodes": [],  # Empty nodes
            "edges": []
        }
        
        payload = {
            "workflow": invalid_workflow,
            "rerank_enabled": False
        }
        
        response = api_client.post(f"{api_base_url}/execute-workflow", json=payload)
        
        # API returns 200 but with success: false for validation errors
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"] is not None
        
    def test_workflow_validation_errors(self, api_client: requests.Session, api_base_url: str):
        """Test workflow with validation errors"""
        # Workflow with disconnected nodes
        invalid_workflow = {
            "nodes": [
                {
                    "id": "input_1",
                    "type": "input-node",
                    "config": {
                        "id": "input_1",
                        "content": "Test"
                    }
                },
                {
                    "id": "output_1", 
                    "type": "output-node",
                    "config": {
                        "id": "output_1",
                        "content": ""
                    }
                }
            ],
            "edges": []  # No edges - disconnected nodes
        }
        
        payload = {
            "workflow": invalid_workflow,
            "rerank_enabled": False
        }
        
        response = api_client.post(f"{api_base_url}/execute-workflow", json=payload)
        
        # API returns 200 but with success: false for validation errors
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"] is not None