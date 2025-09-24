"""
Streaming execution tests
"""
import pytest
import requests
import json
import asyncio
import aiohttp


class TestStreamingExecution:
    """Test streaming workflow execution"""
    
    def test_streaming_workflow_execution(self, api_client: requests.Session, api_base_url: str, sample_workflow):
        """Test streaming workflow execution endpoint"""
        payload = {
            "workflow": sample_workflow
        }
        
        response = api_client.post(
            f"{api_base_url}/execute-workflow-stream", 
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"}
        )
        
        assert response.status_code == 200
        assert response.headers.get("Content-Type") == "text/event-stream"
        
        # Collect streaming data
        events = []
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith("data: "):
                try:
                    event_data = json.loads(line[6:])  # Remove "data: " prefix
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue
                    
        # Verify we received streaming events
        assert len(events) > 0
        
        # Check that we get some kind of streaming response
        # May not have completion events depending on workflow success/failure
        assert any("type" in event for event in events)
        
    def test_streaming_with_long_workflow(self, api_client: requests.Session, api_base_url: str):
        """Test streaming with a more complex workflow"""
        complex_workflow = {
            "nodes": [
                {
                    "id": "input_1",
                    "type": "input-node",
                    "position": {"x": 100, "y": 100},
                    "content": "Analyze this topic in detail"
                },
                {
                    "id": "gen_1",
                    "type": "generation-node",
                    "position": {"x": 250, "y": 100},
                    "model_type": "gemini-1.5-flash",
                    "llm_provider": "google",
                    "prompt": "Provide a detailed analysis of: {input_data}"
                },
                {
                    "id": "val_1",
                    "type": "validation-node",
                    "position": {"x": 400, "y": 100}, 
                    "model_type": "gemini-1.5-flash",
                    "llm_provider": "google",
                    "prompt": "Review and validate this analysis: {input_data}"
                },
                {
                    "id": "output_1",
                    "type": "output-node",
                    "position": {"x": 550, "y": 100}
                }
            ],
            "edges": [
                {"id": "e1", "source": "input_1", "target": "gen_1"},
                {"id": "e2", "source": "gen_1", "target": "val_1"},
                {"id": "e3", "source": "val_1", "target": "output_1"}
            ]
        }
        
        payload = {
            "workflow": complex_workflow
        }
        
        response = api_client.post(
            f"{api_base_url}/execute-workflow-stream",
            json=payload,
            stream=True,
            timeout=60  # Longer timeout for complex workflow
        )
        
        assert response.status_code == 200
        
        # Verify streaming works for longer workflows
        events = []
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith("data: "):
                try:
                    event_data = json.loads(line[6:])
                    events.append(event_data)
                    # Break after some events to avoid hanging
                    if len(events) >= 10:
                        break
                except json.JSONDecodeError:
                    continue
                    
        assert len(events) > 0
        # Just verify we get streaming events, not specific completion
        assert any("type" in event for event in events)