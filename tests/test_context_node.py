"""
Context node and knowledge base tests
"""
import pytest
import requests
import json


class TestContextNode:
    """Test context-node functionality and knowledge base integration"""
    
    @pytest.fixture
    def context_workflow(self):
        """Workflow with context-node"""
        return {
            "nodes": [
                {
                    "id": "input_1",
                    "type": "input-node",
                    "position": {"x": 100, "y": 100},
                    "data": {
                        "id": "input_1",
                        "nodeType": "input-node",
                        "label": "Input",
                        "content": "NVMe storage requirements"
                    }
                },
                {
                    "id": "context_1",
                    "type": "context-node",
                    "position": {"x": 200, "y": 50},
                    "data": {
                        "id": "context_1",
                        "nodeType": "context-node",
                        "label": "Context",
                        "knowledge_base": "sentence_nvme_2-2",
                        "search_intensity": "standard",
                        "rerank_provider": "none",
                        "rerank_model": None
                    }
                },
                {
                    "id": "output_1",
                    "type": "output-node",
                    "position": {"x": 500, "y": 100},
                    "data": {
                        "id": "output_1",
                        "nodeType": "output-node",
                        "label": "Output"
                    }
                }
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "input_1", 
                    "target": "context_1"
                },
                {
                    "id": "e2",
                    "source": "context_1",
                    "target": "output_1" 
                }
            ]
        }
    
    def test_knowledge_base_list(self, api_client: requests.Session, api_base_url: str):
        """Test knowledge base list endpoint"""
        try:
            kb_response = api_client.get(f"{api_base_url}/knowledge-bases", timeout=2)
            assert kb_response.status_code == 200
            
            knowledge_bases = kb_response.json().get("knowledge_bases", [])
            assert isinstance(knowledge_bases, list)
            
            if knowledge_bases:
                # Check structure of first KB
                kb = knowledge_bases[0]
                assert "name" in kb
                assert "chunk_count" in kb or "count" in kb
        except requests.exceptions.RequestException:
            pytest.skip("API server not running")
        
    def test_context_node_workflow(self, api_client: requests.Session, api_base_url: str, context_workflow):
        """Test workflow execution with context-node"""
        try:
            # Check if required knowledge base exists
            kb_response = api_client.get(f"{api_base_url}/knowledge-bases", timeout=2)
            kb_names = [kb["name"] for kb in kb_response.json().get("knowledge_bases", [])]
            
            if not kb_names:
                pytest.skip("No knowledge bases available")
            
            # Use first available KB if sentence_nvme_2-2 doesn't exist
            if "sentence_nvme_2-2" not in kb_names:
                context_workflow["nodes"][1]["data"]["knowledge_base"] = kb_names[0]
                
            payload = {
                "workflow": context_workflow
            }
            
            response = api_client.post(f"{api_base_url}/execute-workflow-stream", json=payload, stream=True, timeout=10)
            assert response.status_code == 200
            
            # Parse streaming response
            events = []
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        event_data = line[6:]  # Remove "data: " prefix
                        try:
                            event_json = json.loads(event_data)
                            events.append(event_json)
                        except json.JSONDecodeError:
                            continue
            
            # Check that we got events
            assert len(events) > 0, "No streaming events received"
            
            # Check for execution_started event
            event_types = [e.get('type') for e in events]
            assert 'execution_started' in event_types, "No execution_started event"
            
        except requests.exceptions.RequestException:
            pytest.skip("API server not running")