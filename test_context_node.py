import requests
import json
import time

# 워크플로우 JSON 로드
with open('test_context_workflow.json', 'r') as f:
    workflow = json.load(f)

print("=== Context-Node 테스트 ===")
print("워크플로우:", json.dumps(workflow, indent=2))

# API 호출
try:
    response = requests.post(
        'http://localhost:5001/execute-workflow',
        json={
            'workflow': workflow,
            'rerank_enabled': False
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print("\n=== 실행 결과 ===")
        print("Success:", result.get('success'))
        print("Final Output:", result.get('final_output'))
        print("Execution Time:", result.get('total_execution_time'))
        
        print("\n=== 노드별 결과 ===")
        for node_result in result.get('execution_results', []):
            print(f"Node {node_result['node_id']}:")
            print(f"  Success: {node_result['success']}")
            if node_result.get('output'):
                print(f"  Output: {node_result.get('output', 'N/A')[:200]}...")
            if node_result.get('description'):
                print(f"  Description: {node_result.get('description', 'N/A')[:100]}...")
            if node_result.get('error'):
                print(f"  Error: {node_result['error']}")
            print()
        
        # 전체 응답도 출력
        print("\n=== 전체 응답 ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"API 호출 실패: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"테스트 실패: {e}")