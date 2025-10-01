"""
LLM을 더 많이 사용하는 워크플로우로 블로킹 테스트 (Context-node 포함)
"""

import asyncio
import aiohttp
import time

async def test_heavy_workflow_blocking():
    """더 무거운 워크플로우로 블로킹 테스트"""
    print("=== 무거운 워크플로우 vs 모델 API 블로킹 테스트 시작 ===")
    
    base_url = "http://localhost:5001"
    
    # Context-node를 포함한 더 복잡한 워크플로우
    workflow_data = {
        'nodes': [
            {
                'id': 'input1',
                'type': 'input-node',
                'position': {'x': 100, 'y': 100},
                'data': {
                    'nodeType': 'input-node',
                    'content': 'What is NVMe and how does it work? Please provide detailed technical information.'
                }
            },
            {
                'id': 'context1',
                'type': 'context-node',
                'position': {'x': 100, 'y': 200},
                'data': {
                    'nodeType': 'context-node',
                    'knowledge_base': 'keyword_nvme_2-2',
                    'search_intensity': 'high',
                    'user_prompt': '{input}'
                }
            },
            {
                'id': 'gen1', 
                'type': 'generation-node',
                'position': {'x': 300, 'y': 150},
                'data': {
                    'nodeType': 'generation-node',
                    'llm_provider': 'google',
                    'model_type': 'gemini-1.5-flash',
                    'system_prompt': 'You are a technical expert. Generate a comprehensive response based on the provided context and user input.',
                    'user_prompt': 'User question: {input}\n\nContext information:\n{context}\n\nPlease provide a detailed technical explanation.'
                }
            },
            {
                'id': 'validation1',
                'type': 'validation-node',
                'position': {'x': 500, 'y': 150},
                'data': {
                    'nodeType': 'validation-node',
                    'llm_provider': 'google',
                    'model_type': 'gemini-1.5-flash',
                    'system_prompt': 'Review and improve the technical response for accuracy and completeness.',
                    'user_prompt': 'Original response: {input}\n\nPlease review and enhance this response.'
                }
            },
            {
                'id': 'output1',
                'type': 'output-node', 
                'position': {'x': 700, 'y': 150},
                'data': {
                    'nodeType': 'output-node'
                }
            }
        ],
        'edges': [
            {'id': 'e1', 'source': 'input1', 'target': 'context1'},
            {'id': 'e2', 'source': 'input1', 'target': 'gen1'},
            {'id': 'e3', 'source': 'context1', 'target': 'gen1'},
            {'id': 'e4', 'source': 'gen1', 'target': 'validation1'},
            {'id': 'e5', 'source': 'validation1', 'target': 'output1'}
        ]
    }
    
    async def execute_heavy_workflow():
        """무거운 워크플로우 실행"""
        start_time = time.time()
        print(f"무거운 워크플로우 실행 시작 - {start_time:.2f}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f'{base_url}/execute-workflow', json=workflow_data, timeout=60) as resp:
                    result = await resp.text()
                    end_time = time.time()
                    execution_time = end_time - start_time
                    print(f"무거운 워크플로우 실행 완료 - {end_time:.2f} (소요시간: {execution_time:.2f}초)")
                    return {
                        'success': resp.status == 200,
                        'execution_time': execution_time
                    }
            except Exception as e:
                print(f"무거운 워크플로우 실행 실패 - {str(e)}")
                return {
                    'success': False,
                    'execution_time': time.time() - start_time,
                    'error': str(e)
                }
    
    async def rapid_model_api_calls():
        """빠른 연속 모델 API 호출들"""
        print("빠른 연속 모델 API 호출들 시작")
        results = []
        
        async with aiohttp.ClientSession() as session:
            # 여러 번 연속으로 호출해서 블로킹 확인
            for i in range(5):
                start_time = time.time()
                try:
                    async with session.get(f'{base_url}/available-models/google', timeout=5) as resp:
                        await resp.json()
                        response_time = time.time() - start_time
                        results.append({
                            'call': i + 1,
                            'success': resp.status == 200,
                            'response_time': response_time
                        })
                        print(f"Google 모델 API 호출 #{i+1} 완료 - 응답시간: {response_time:.2f}초")
                except Exception as e:
                    results.append({
                        'call': i + 1,
                        'success': False,
                        'error': str(e),
                        'response_time': time.time() - start_time
                    })
                    print(f"Google 모델 API 호출 #{i+1} 실패 - {str(e)}")
                
                # 0.2초 간격으로 호출
                await asyncio.sleep(0.2)
        
        return results
    
    # 무거운 워크플로우를 먼저 시작
    workflow_task = asyncio.create_task(execute_heavy_workflow())
    
    # 워크플로우가 시작되고 1초 후에 연속 모델 API 호출
    await asyncio.sleep(1.0)
    models_task = asyncio.create_task(rapid_model_api_calls())
    
    # 두 태스크가 모두 완료될 때까지 대기
    workflow_result, models_results = await asyncio.gather(workflow_task, models_task, return_exceptions=True)
    
    print("\n=== 무거운 워크플로우 블로킹 테스트 결과 ===")
    print(f"워크플로우 결과: {workflow_result}")
    
    if isinstance(models_results, list):
        successful_calls = [r for r in models_results if r['success']]
        failed_calls = [r for r in models_results if not r['success']]
        
        if successful_calls:
            avg_response_time = sum(r['response_time'] for r in successful_calls) / len(successful_calls)
            max_response_time = max(r['response_time'] for r in successful_calls)
            
            print(f"성공한 모델 API 호출: {len(successful_calls)}/{len(models_results)}")
            print(f"평균 응답시간: {avg_response_time:.2f}초")
            print(f"최대 응답시간: {max_response_time:.2f}초")
            
            if max_response_time > 3.0:
                print("❌ 모델 API가 블로킹되고 있습니다!")
            elif avg_response_time > 1.5:
                print("⚠️ 모델 API 응답이 평소보다 느립니다")
            else:
                print("✅ 모델 API가 정상적으로 작동하고 있습니다")
        
        if failed_calls:
            print(f"실패한 호출: {len(failed_calls)}개")
            for call in failed_calls:
                print(f"  호출 #{call['call']}: {call.get('error', 'Unknown error')}")
    else:
        print("❌ 모델 API 테스트에서 예외 발생")

if __name__ == "__main__":
    asyncio.run(test_heavy_workflow_blocking())