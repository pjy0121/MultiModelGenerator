#!/usr/bin/env python3
"""
API 테스트 스크립트 - Node-based workflow API
"""

import requests
import json
from time import sleep

def test_api():
    base_url = "http://localhost:5001"
    
    # 서버 시작 대기
    print("⏳ 서버 시작 대기 중...")
    sleep(3)
    
    try:
        # Health check
        print("\n1. Health Check 테스트")
        response = requests.get(f"{base_url}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Test endpoint
        print("\n2. Test 엔드포인트 테스트")
        response = requests.get(f"{base_url}/test")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Knowledge bases
        print("\n3. Knowledge Base 목록 테스트")
        response = requests.get(f"{base_url}/knowledge-bases")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Simple workflow validation
        print("\n4. Workflow Validation 테스트")
        sample_workflow = {
            "id": "test-workflow",
            "name": "Test Workflow",
            "nodes": [
                {
                    "id": "input-1",
                    "type": "input-node",
                    "name": "Input Node",
                    "content": "Test input content",
                    "model_type": "",
                    "llm_provider": "",
                    "prompt": "",
                    "position": {"x": 0, "y": 0}
                },
                {
                    "id": "output-1", 
                    "type": "output-node",
                    "name": "Output Node",
                    "content": "",
                    "model_type": "",
                    "llm_provider": "",
                    "prompt": "",
                    "position": {"x": 200, "y": 0}
                }
            ],
            "edges": [
                {
                    "id": "edge-1",
                    "source": "input-1",
                    "target": "output-1"
                }
            ]
        }
        
        response = requests.post(
            f"{base_url}/validate-workflow",
            json=sample_workflow,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        print("\n✅ 모든 기본 API 테스트 완료!")
        
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    test_api()