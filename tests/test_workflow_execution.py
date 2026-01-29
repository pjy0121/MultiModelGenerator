"""
Workflow execution tests
"""
import pytest
import requests
import json


class TestWorkflowExecution:
    """Test workflow execution functionality"""
    
    def test_simple_workflow_execution_stream(self, api_client: requests.Session, api_base_url: str, sample_workflow):
        """Test basic workflow execution via streaming"""
        payload = {
            "workflow": sample_workflow
        }
        
        response = api_client.post(f"{api_base_url}/execute-workflow-stream", json=payload, stream=True)
        
        assert response.status_code == 200
        
        # Handle streaming response
        events = []
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                try:
                    event_data = json.loads(line[6:])  # Remove 'data: '
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue

        # Should have at least one event
        assert len(events) > 0, "No streaming events found"

        # Check event types
        event_types = [e.get('type') for e in events if 'type' in e]
        assert len(event_types) > 0, "No event types found"

        # Check execution_started event
        assert 'execution_started' in event_types, "execution_started event not found"