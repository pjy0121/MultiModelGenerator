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
        
        # 스트리밍 응답 처리
        events = []
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                try:
                    event_data = json.loads(line[6:])  # 'data: ' 제거
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue
        
        # 최소한 하나의 이벤트가 있어야 함
        assert len(events) > 0, "스트리밍 이벤트가 없습니다"
        
        # 이벤트 타입 확인
        event_types = [e.get('type') for e in events if 'type' in e]
        assert len(event_types) > 0, "이벤트 타입이 없습니다"
        
        # execution_started 이벤트 확인
        assert 'execution_started' in event_types, "execution_started 이벤트가 없습니다"