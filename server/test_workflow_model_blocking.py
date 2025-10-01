"""
워크플로우 실행 중 모델 API 블로킹 테스트
"""

import asyncio
import aiohttp
import time

async def test_workflow_blocking_models():
    """워크플로우 실행 중 모델 API가 블로킹되는지 테스트"""
    print("=== 워크플로우 실행 중 모델 API 블로킹 테스트 시작 ===")
    
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
                    'content': 'Test input for blocking test'
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
                    'system_prompt': 'Generate a long response to test blocking.',
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
                        'success': resp.status == 200,
                        'execution_time': execution_time
                    }
            except Exception as e:
                print(f"워크플로우 실행 실패 - {str(e)}")
                return {
                    'success': False,
                    'execution_time': time.time() - start_time,
                    'error': str(e)
                }
    
    async def test_models_during_workflow():
        """워크플로우 실행 중 모델 API 테스트"""
        print("모델 API 호출들 시작")
        results = []
        
        providers = ["google", "openai"]  # internal은 API 키 없어서 제외
        
        async with aiohttp.ClientSession() as session:
            for provider in providers:
                start_time = time.time()
                try:
                    async with session.get(f'{base_url}/available-models/{provider}', timeout=10) as resp:
                        await resp.json()  # 응답 읽기
                        response_time = time.time() - start_time
                        results.append({
                            'provider': provider,
                            'success': resp.status == 200,
                            'response_time': response_time
                        })
                        print(f"{provider} 모델 목록 조회 완료 - 응답시간: {response_time:.2f}초")
                except Exception as e:
                    results.append({
                        'provider': provider,
                        'success': False,
                        'error': str(e),
                        'response_time': time.time() - start_time
                    })
                    print(f"{provider} 모델 목록 조회 실패 - {str(e)}")
        
        return results
    
    # 워크플로우를 먼저 시작
    workflow_task = asyncio.create_task(execute_workflow())
    
    # 워크플로우가 시작된 후 0.5초 뒤에 모델 API 호출들 시작
    await asyncio.sleep(0.5)
    models_task = asyncio.create_task(test_models_during_workflow())
    
    # 두 태스크가 모두 완료될 때까지 대기
    workflow_result, models_results = await asyncio.gather(workflow_task, models_task, return_exceptions=True)
    
    print("\n=== 테스트 결과 분석 ===")
    print(f"워크플로우 결과: {workflow_result}")
    print(f"모델 API 결과: {models_results}")
    
    # 결과 검증
    if isinstance(models_results, list):
        for result in models_results:
            if result['success']:
                if result['response_time'] > 3.0:
                    print(f"⚠️ {result['provider']} 응답시간이 김: {result['response_time']:.2f}초 - 블로킹 의심")
                else:
                    print(f"✅ {result['provider']} 정상 응답: {result['response_time']:.2f}초")
            else:
                print(f"❌ {result['provider']} 실패: {result.get('error', 'Unknown')}")
    else:
        print("❌ 모델 API 테스트에서 예외 발생")

if __name__ == "__main__":
    asyncio.run(test_workflow_blocking_models())