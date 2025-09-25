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
                import json
                try:
                    event_data = json.loads(line[6:])  # 'data: ' 제거
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue
        
        # 최소한 하나의 이벤트가 있어야 함
        assert len(events) > 0, "스트리밍 이벤트가 없습니다"
        
        # 마지막 이벤트 확인 (완료 또는 에러)
        if events:
            last_event = events[-1]
            assert last_event.get('type') in ['complete', 'error', 'final_result'], f"예상치 못한 마지막 이벤트: {last_event}"
        assert "total_execution_time" in data
        assert "results" in data  # API returns "results" not "node_results"
        assert "execution_order" in data
        
        # Check execution metadata
        assert data["total_execution_time"] >= 0
        assert len(data["results"]) == 3  # input, generation, output nodes
        assert len(data["execution_order"]) == 3