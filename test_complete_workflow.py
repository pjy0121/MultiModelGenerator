#!/usr/bin/env python3
"""
완전한 워크플로우 실행 테스트 - Node-based workflow API
"""

import requests
import json
import os
from time import sleep

def test_complete_workflow():
    # 환경변수 또는 기본값 사용
    api_host = os.getenv("API_HOST", "localhost") 
    api_port = os.getenv("API_PORT", "5001")
    base_url = f"http://{api_host}:{api_port}"
    
    print("🚀 Node-based Workflow 완전 테스트 시작")
    print("=" * 50)
    
    try:
        # 1. Health check
        print("\n1. ✅ Health Check")
        response = requests.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        print(f"   Version: {response.json().get('version', 'Unknown')}")
        
        # 2. Knowledge bases
        print("\n2. 📚 Knowledge Base 목록")
        response = requests.get(f"{base_url}/knowledge-bases")
        kb_response = response.json()
        knowledge_bases = kb_response.get('knowledge_bases', [])
        print(f"   Found {len(knowledge_bases)} knowledge bases:")
        kb_names = []
        for kb in knowledge_bases:
            if isinstance(kb, dict):
                name = kb.get('name', 'Unknown')
                count = kb.get('document_count', 0)
                print(f"   - {name} ({count} documents)")
                kb_names.append(name)
            else:
                print(f"   - {kb}")
                kb_names.append(str(kb))
        
        # 3. Simple Input → Output workflow
        print("\n3. 🔄 단순 워크플로우 (Input → Output)")
        simple_workflow = {
            "nodes": [
                {
                    "id": "input-1",
                    "type": "input-node",
                    "content": "이것은 테스트 입력 내용입니다."
                },
                {
                    "id": "output-1", 
                    "type": "output-node",
                    "content": ""
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
        
        # 3a. Validation
        print("   3a. 워크플로우 검증")
        response = requests.post(
            f"{base_url}/validate-workflow",
            json=simple_workflow,
            headers={"Content-Type": "application/json"}
        )
        validation_result = response.json()
        print(f"   Valid: {validation_result.get('valid', False)}")
        if validation_result.get('errors'):
            print(f"   Errors: {validation_result['errors']}")
        if validation_result.get('warnings'):
            print(f"   Warnings: {validation_result['warnings']}")
        
        # 3b. Execution
        if validation_result.get('valid', False):
            print("   3b. 워크플로우 실행")
            execution_request = {
                "workflow": simple_workflow,
                "knowledge_base": kb_names[0] if kb_names else None,
                "search_intensity": 3
            }
            
            response = requests.post(
                f"{base_url}/execute-workflow",
                json=execution_request,
                headers={"Content-Type": "application/json"}
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                execution_result = response.json()
                print(f"   Success: {execution_result.get('success', False)}")
                print(f"   Execution time: {execution_result.get('execution_time_seconds', 'N/A')}s")
                
                # 실행 결과 표시
                results = execution_result.get('results', [])
                print(f"   Node results: {len(results)}")
                for result in results:
                    if isinstance(result, dict):
                        node_id = result.get('node_id', 'Unknown')
                        success = result.get('success', False)
                        output_data = result.get('output', {})
                        if isinstance(output_data, dict):
                            output = output_data.get('output', 'No output')
                        else:
                            output = str(output_data)
                        print(f"     - {node_id}: {'✅' if success else '❌'} {output[:50]}{'...' if len(output) > 50 else ''}")
                    else:
                        print(f"     - Result: {str(result)[:50]}{'...' if len(str(result)) > 50 else ''}")
            else:
                print(f"   Error: {response.text}")
        
        # 4. 지식 베이스 검색 테스트 (지식 베이스가 있는 경우)
        if kb_names:
            print(f"\n4. 🔍 지식 베이스 검색 테스트 ({kb_names[0]})")
            search_request = {
                "query": "specification",
                "knowledge_base": kb_names[0],
                "top_k": 3
            }
            
            response = requests.post(
                f"{base_url}/search-knowledge-base",
                json=search_request,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                search_results = response.json().get('results', [])
                print(f"   Found {len(search_results)} results")
                for i, result in enumerate(search_results[:2]):  # 상위 2개만 표시
                    # result는 문자열이므로 직접 사용
                    content = result if isinstance(result, str) else str(result)
                    print(f"     {i+1}. {content[:100]}{'...' if len(content) > 100 else ''}")
            else:
                print(f"   Error: {response.text}")
        
        print("\n" + "=" * 50)
        print("🎉 Node-based Workflow 테스트 완료!")
        
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    test_complete_workflow()