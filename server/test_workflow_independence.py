"""
워크플로우 실행 중 클라이언트 독립성 테스트
"""

import asyncio
import aiohttp
import time

async def test_workflow_blocking():
    """워크플로우 실행 중에도 다른 API 호출이 블로킹되지 않는지 테스트"""
    print("=== 워크플로우 vs API 호출 독립성 테스트 시작 ===")
    
    base_url = "http://localhost:5001"
    
    # 간단한 워크플로우 데이터
    workflow_data = {
        'nodes': [
            {
                'id': 'input1',
                'type': 'input-node',
                'position': {'x': 100, 'y': 100},
                'data': {
                    'nodeType': 'input-node',
                    'content': 'Test input for independence verification'
                }
            },
            {
                'id': 'gen1', 
                'type': 'generation-node',
                'position': {'x': 300, 'y': 100},
                'data': {
                    'nodeType': 'generation-node',
                    'llm_provider': 'google',
                    'model_type': 'gemini-1.5-flash',
                    'system_prompt': 'Generate a simple response.',
                    'user_prompt': '{input}'
                }
            },
            {
                'id': 'output1',
                'type': 'output-node', 
                'position': {'x': 500, 'y': 100},
                'data': {
                    'nodeType': 'output-node'
                }
            }
        ],
        'edges': [
            {'id': 'e1', 'source': 'input1', 'target': 'gen1'},
            {'id': 'e2', 'source': 'gen1', 'target': 'output1'}
        ]
    }
    
    async def execute_workflow():
        """워크플로우 실행"""
        start_time = time.time()
        print(f"워크플로우 실행 시작 - {start_time:.2f}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f'{base_url}/execute-workflow', json=workflow_data, timeout=30) as resp:
                    result = await resp.text()
                    end_time = time.time()
                    execution_time = end_time - start_time
                    print(f"워크플로우 실행 완료 - {end_time:.2f} (소요시간: {execution_time:.2f}초)")
                    return {
                        'type': 'workflow',
                        'success': resp.status == 200,
                        'execution_time': execution_time,
                        'result_length': len(result)
                    }
            except Exception as e:
                print(f"워크플로우 실행 실패 - {str(e)}")
                return {
                    'type': 'workflow',
                    'success': False,
                    'execution_time': time.time() - start_time,
                    'error': str(e)
                }
    
    async def quick_api_calls():
        """빠른 API 호출들"""
        print("빠른 API 호출들 시작")
        results = []
        
        async with aiohttp.ClientSession() as session:
            # 지식베이스 목록 조회
            start_time = time.time()
            try:
                async with session.get(f'{base_url}/knowledge-bases', timeout=10) as resp:
                    kb_result = await resp.json()
                    response_time = time.time() - start_time
                    results.append({
                        'endpoint': 'knowledge-bases',
                        'success': resp.status == 200,
                        'response_time': response_time,
                        'kb_count': len(kb_result.get('knowledge_bases', []))
                    })
                    print(f"지식베이스 목록 조회 완료 - 응답시간: {response_time:.2f}초")
            except Exception as e:
                results.append({
                    'endpoint': 'knowledge-bases',
                    'success': False,
                    'error': str(e),
                    'response_time': time.time() - start_time
                })
            
            # 모델 목록 조회  
            start_time = time.time()
            try:
                async with session.get(f'{base_url}/models', timeout=10) as resp:
                    models_result = await resp.json()
                    response_time = time.time() - start_time
                    results.append({
                        'endpoint': 'models',
                        'success': resp.status == 200,
                        'response_time': response_time,
                        'model_count': len(models_result.get('models', []))
                    })
                    print(f"모델 목록 조회 완료 - 응답시간: {response_time:.2f}초")
            except Exception as e:
                results.append({
                    'endpoint': 'models',
                    'success': False,
                    'error': str(e),
                    'response_time': time.time() - start_time
                })
        
        return {'type': 'api_calls', 'results': results}
    
    # 워크플로우를 먼저 시작
    workflow_task = asyncio.create_task(execute_workflow())
    
    # 워크플로우가 시작된 후 0.5초 뒤에 API 호출들 시작
    await asyncio.sleep(0.5)
    api_calls_task = asyncio.create_task(quick_api_calls())
    
    # 두 태스크가 모두 완료될 때까지 대기
    workflow_result, api_calls_result = await asyncio.gather(workflow_task, api_calls_task, return_exceptions=True)
    
    print("\n=== 테스트 결과 분석 ===")
    print(f"워크플로우 결과: {workflow_result}")
    print(f"API 호출 결과: {api_calls_result}")
    
    # 결과 검증
    if isinstance(api_calls_result, dict) and api_calls_result.get('type') == 'api_calls':
        all_success = True
        max_response_time = 0
        
        for call in api_calls_result['results']:
            if not call['success']:
                print(f"❌ {call['endpoint']} API 호출 실패: {call.get('error', 'Unknown error')}")
                all_success = False
            else:
                response_time = call['response_time']
                max_response_time = max(max_response_time, response_time)
                print(f"✅ {call['endpoint']} API 호출 성공 - 응답시간: {response_time:.2f}초")
        
        if all_success:
            if max_response_time < 3.0:
                print(f"\n✅ 클라이언트 독립성 테스트 통과! 최대 응답시간: {max_response_time:.2f}초")
            else:
                print(f"\n⚠️ 클라이언트 독립성 테스트 부분 통과 - 응답시간이 다소 김: {max_response_time:.2f}초")
        else:
            print("\n❌ 클라이언트 독립성 테스트 실패 - API 호출 실패")
    else:
        print("\n❌ API 호출 태스크에서 예외 발생")

if __name__ == "__main__":
    asyncio.run(test_workflow_blocking())