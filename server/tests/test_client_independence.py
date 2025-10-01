"""
클라이언트 독립성 테스트

여러 클라이언트가 동시에 API를 호출할 때 서로 블로킹되지 않는지 확인하는 테스트
특히 워크플로우 실행 중에도 다른 클라이언트의 API 호출(지식베이스 목록, 모델 목록 등)이
정상적으로 처리되는지 검증
"""

import pytest
import asyncio
import aiohttp
import time
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
import threading


class TestClientIndependence:
    """클라이언트 독립성 테스트 클래스"""
    
    BASE_URL = "http://localhost:5001"
    
    @pytest.fixture
    def simple_workflow_data(self) -> Dict[str, Any]:
        """간단한 테스트용 워크플로우 데이터"""
        return {
            'nodes': [
                {
                    'id': 'input1',
                    'type': 'input-node',
                    'position': {'x': 100, 'y': 100},
                    'data': {
                        'nodeType': 'input-node',
                        'content': 'Test input for client independence verification'
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
                        'system_prompt': 'Generate requirements from input.',
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

    async def _execute_workflow(self, workflow_data: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """워크플로우 실행 (시간이 오래 걸리는 작업)"""
        start_time = time.time()
        print(f"클라이언트 {client_id}: 워크플로우 실행 시작 - {start_time:.2f}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f'{self.BASE_URL}/execute-workflow', json=workflow_data, timeout=30) as resp:
                    result = await resp.text()
                    end_time = time.time()
                    execution_time = end_time - start_time
                    print(f"클라이언트 {client_id}: 워크플로우 실행 완료 - {end_time:.2f} (소요시간: {execution_time:.2f}초)")
                    
                    return {
                        'client_id': client_id,
                        'success': resp.status == 200,
                        'execution_time': execution_time,
                        'result_length': len(result)
                    }
            except Exception as e:
                print(f"클라이언트 {client_id}: 워크플로우 실행 실패 - {str(e)}")
                return {
                    'client_id': client_id,
                    'success': False,
                    'execution_time': time.time() - start_time,
                    'error': str(e)
                }

    async def _make_quick_api_calls(self, client_id: str) -> Dict[str, Any]:
        """빠른 API 호출들 (독립성 확인용)"""
        start_time = time.time()
        print(f"클라이언트 {client_id}: 빠른 API 호출들 시작 - {start_time:.2f}")
        
        results = {'client_id': client_id, 'calls': []}
        
        async with aiohttp.ClientSession() as session:
            # 지식베이스 목록 조회
            try:
                call_start = time.time()
                async with session.get(f'{self.BASE_URL}/knowledge-bases', timeout=10) as resp:
                    kb_result = await resp.json()
                    call_time = time.time() - call_start
                    results['calls'].append({
                        'endpoint': 'knowledge-bases',
                        'success': resp.status == 200,
                        'response_time': call_time,
                        'result_count': len(kb_result.get('knowledge_bases', []))
                    })
                    print(f"클라이언트 {client_id}: KB 목록 조회 완료 - {time.time():.2f} (응답시간: {call_time:.2f}초)")
            except Exception as e:
                results['calls'].append({
                    'endpoint': 'knowledge-bases',
                    'success': False,
                    'error': str(e)
                })
            
            # 모델 목록 조회  
            try:
                call_start = time.time()
                async with session.get(f'{self.BASE_URL}/models', timeout=10) as resp:
                    models_result = await resp.json()
                    call_time = time.time() - call_start
                    results['calls'].append({
                        'endpoint': 'models',
                        'success': resp.status == 200,
                        'response_time': call_time,
                        'result_count': len(models_result.get('models', []))
                    })
                    print(f"클라이언트 {client_id}: 모델 목록 조회 완료 - {time.time():.2f} (응답시간: {call_time:.2f}초)")
            except Exception as e:
                results['calls'].append({
                    'endpoint': 'models',
                    'success': False,
                    'error': str(e)
                })
        
        total_time = time.time() - start_time
        results['total_time'] = total_time
        print(f"클라이언트 {client_id}: 모든 API 호출 완료 - 총 소요시간: {total_time:.2f}초")
        
        return results

    @pytest.mark.asyncio
    async def test_workflow_execution_does_not_block_other_api_calls(self, simple_workflow_data):
        """
        워크플로우 실행 중에도 다른 클라이언트의 API 호출이 블로킹되지 않는지 테스트
        
        시나리오:
        1. 클라이언트 A가 워크플로우 실행 시작 (시간이 오래 걸림)
        2. 클라이언트 B가 빠른 API 호출들 실행 (지식베이스 목록, 모델 목록)
        3. 클라이언트 B의 응답시간이 합리적인 범위 내에 있는지 확인
        """
        print("\n=== 클라이언트 독립성 테스트 시작 ===")
        
        # 두 클라이언트 태스크 생성
        workflow_task = asyncio.create_task(
            self._execute_workflow(simple_workflow_data, "A")
        )
        
        # 워크플로우가 먼저 시작되도록 잠깐 대기
        await asyncio.sleep(0.5)
        
        quick_calls_task = asyncio.create_task(
            self._make_quick_api_calls("B")
        )
        
        # 두 태스크를 동시에 실행
        workflow_result, quick_calls_result = await asyncio.gather(
            workflow_task, quick_calls_task, return_exceptions=True
        )
        
        print("\n=== 테스트 결과 분석 ===")
        print(f"워크플로우 결과: {workflow_result}")
        print(f"빠른 API 호출 결과: {quick_calls_result}")
        
        # 결과 검증
        assert isinstance(quick_calls_result, dict), "빠른 API 호출이 정상적으로 완료되어야 함"
        assert quick_calls_result['client_id'] == 'B', "클라이언트 B의 결과여야 함"
        
        # 모든 API 호출이 성공했는지 확인
        for call in quick_calls_result['calls']:
            assert call['success'], f"{call['endpoint']} API 호출이 실패함: {call.get('error', 'Unknown error')}"
            
            # 응답시간이 합리적인 범위 내에 있는지 확인 (5초 이내)
            assert call['response_time'] < 5.0, f"{call['endpoint']} API 응답시간이 너무 김: {call['response_time']:.2f}초"
        
        # 전체 빠른 API 호출들의 총 소요시간이 합리적인지 확인 (10초 이내)
        assert quick_calls_result['total_time'] < 10.0, f"빠른 API 호출들의 총 소요시간이 너무 김: {quick_calls_result['total_time']:.2f}초"
        
        print("✅ 클라이언트 독립성 테스트 통과!")

    @pytest.mark.asyncio
    async def test_multiple_concurrent_workflows(self, simple_workflow_data):
        """
        여러 워크플로우가 동시에 실행될 때 서로 블로킹되지 않는지 테스트
        """
        print("\n=== 다중 워크플로우 동시 실행 테스트 시작 ===")
        
        # 3개의 워크플로우를 동시에 실행
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                self._execute_workflow(simple_workflow_data, f"W{i+1}")
            )
            tasks.append(task)
        
        # 모든 워크플로우 실행 완료 대기
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"\n=== 다중 워크플로우 결과 ===")
        for i, result in enumerate(results):
            print(f"워크플로우 {i+1}: {result}")
            
            # 각 워크플로우가 성공적으로 완료되었는지 확인
            if isinstance(result, dict):
                assert result['success'], f"워크플로우 {i+1}이 실패함: {result.get('error', 'Unknown error')}"
            else:
                pytest.fail(f"워크플로우 {i+1}에서 예외 발생: {result}")
        
        print("✅ 다중 워크플로우 동시 실행 테스트 통과!")

    @pytest.mark.asyncio
    async def test_concurrent_knowledge_base_access(self):
        """
        여러 클라이언트가 동시에 지식베이스에 접근할 때 독립성 테스트
        """
        print("\n=== 동시 지식베이스 접근 테스트 시작 ===")
        
        async def access_kb(client_id: str, kb_name: str) -> Dict[str, Any]:
            """지식베이스 검색 테스트"""
            start_time = time.time()
            
            search_data = {
                'query': f'Test query from client {client_id}',
                'top_k': 5
            }
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        f'{self.BASE_URL}/knowledge-bases/{kb_name}/search',
                        json=search_data,
                        timeout=15
                    ) as resp:
                        result = await resp.json()
                        response_time = time.time() - start_time
                        
                        return {
                            'client_id': client_id,
                            'kb_name': kb_name,
                            'success': resp.status == 200,
                            'response_time': response_time,
                            'result_count': len(result.get('results', []))
                        }
                except Exception as e:
                    return {
                        'client_id': client_id,
                        'kb_name': kb_name,
                        'success': False,
                        'error': str(e),
                        'response_time': time.time() - start_time
                    }
        
        # 먼저 사용가능한 지식베이스 목록을 가져옴
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.BASE_URL}/knowledge-bases') as resp:
                kb_list = await resp.json()
                available_kbs = kb_list.get('knowledge_bases', [])
        
        if not available_kbs:
            pytest.skip("테스트할 지식베이스가 없음")
        
        # 첫 번째 지식베이스를 사용하여 동시 접근 테스트
        test_kb = available_kbs[0]
        
        # 5개의 클라이언트가 동시에 같은 지식베이스에 접근
        tasks = []
        for i in range(5):
            task = asyncio.create_task(access_kb(f"KB{i+1}", test_kb))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"\n=== 동시 지식베이스 접근 결과 (KB: {test_kb}) ===")
        for result in results:
            print(f"클라이언트 {result['client_id']}: 성공={result['success']}, 응답시간={result.get('response_time', 0):.2f}초")
            
            assert result['success'], f"클라이언트 {result['client_id']}의 지식베이스 접근이 실패함: {result.get('error', 'Unknown')}"
            assert result['response_time'] < 10.0, f"클라이언트 {result['client_id']}의 응답시간이 너무 김: {result['response_time']:.2f}초"
        
        print("✅ 동시 지식베이스 접근 테스트 통과!")