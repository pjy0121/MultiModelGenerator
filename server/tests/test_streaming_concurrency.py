"""
스트리밍 동시성 테스트 

여러 클라이언트가 동시에 스트리밍 워크플로우를 실행할 때 
서로 블로킹되지 않고 독립적으로 동작하는지 검증
"""

import pytest
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List, Tuple
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestStreamingConcurrency:
    """스트리밍 동시성 테스트 클래스"""
    
    BASE_URL = "http://localhost:5001"
    
    @pytest.fixture
    def simple_workflow_data(self) -> Dict[str, Any]:
        """간단한 테스트용 워크플로우 데이터 (LLM 없는 빠른 버전)"""
        return {
            "workflow": {
                "nodes": [
                    {
                        "id": "input-1",
                        "type": "input-node",
                        "position": {"x": 100, "y": 100},
                        "content": "스트리밍 동시성 테스트용 입력 텍스트입니다.",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    },
                    {
                        "id": "output-1",
                        "type": "output-node",
                        "position": {"x": 300, "y": 100},
                        "content": "최종 결과",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    }
                ],
                "edges": [
                    {"id": "edge-1", "source": "input-1", "target": "output-1"}
                ]
            }
        }

    async def _execute_streaming_client(
        self, 
        client_id: int, 
        session: aiohttp.ClientSession, 
        workflow_data: Dict[str, Any]
    ) -> Tuple[bool, float, int]:
        """단일 스트리밍 클라이언트 실행"""
        start_time = time.time()
        logger.info(f"[Client {client_id}] 스트리밍 시작")
        
        try:
            async with session.post(
                f"{self.BASE_URL}/execute-workflow-stream",
                json=workflow_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status != 200:
                    logger.error(f"[Client {client_id}] HTTP 오류: {response.status}")
                    response_text = await response.text()
                    logger.error(f"[Client {client_id}] 응답 내용: {response_text}")
                    return False, time.time() - start_time, 0
                
                # SSE 스트림 읽기 - 라인 단위로 버퍼링 처리
                chunk_count = 0
                completed = False
                buffer = ""
                
                async for chunk in response.content.iter_chunked(1024):
                    buffer += chunk.decode('utf-8')
                    
                    # 라인 단위로 처리
                    lines = buffer.split('\n')
                    buffer = lines[-1]  # 마지막 불완전한 라인은 버퍼에 유지
                    
                    for line in lines[:-1]:
                        line = line.strip()
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                chunk_count += 1
                                
                                # 주요 이벤트 로그
                                if data.get('type') in ['start', 'node_start', 'complete', 'error']:
                                    logger.info(f"[Client {client_id}] {data.get('type')}: {data.get('message', '')}")
                                
                                # 완료 또는 에러 시 종료
                                if data.get('type') in ['complete', 'error']:
                                    completed = True
                                    elapsed = time.time() - start_time
                                    if data.get('type') == 'error':
                                        logger.error(f"[Client {client_id}] 에러 응답: {data}")
                                    logger.info(f"[Client {client_id}] 완료 ({elapsed:.2f}초, {chunk_count}개 청크)")
                                    return data.get('type') == 'complete', elapsed, chunk_count
                                    
                            except json.JSONDecodeError as e:
                                logger.debug(f"[Client {client_id}] JSON 파싱 실패: {line[6:]} - {e}")
                                continue
                
                # 스트림이 정상 종료되었는지 확인
                elapsed = time.time() - start_time
                if completed:
                    logger.info(f"[Client {client_id}] 스트림 정상 완료 ({elapsed:.2f}초, {chunk_count}개 청크)")
                    return True, elapsed, chunk_count
                else:
                    logger.warning(f"[Client {client_id}] 스트림 종료 without completion ({elapsed:.2f}초)")
                    return False, elapsed, chunk_count
                
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[Client {client_id}] 에러: {e} ({elapsed:.2f}초)")
            return False, elapsed, 0

    async def _call_api_endpoint(
        self, 
        session: aiohttp.ClientSession, 
        endpoint: str
    ) -> Tuple[bool, float]:
        """단일 API 엔드포인트 호출"""
        start_time = time.time()
        try:
            async with session.get(f"{self.BASE_URL}{endpoint}") as response:
                elapsed = time.time() - start_time
                success = response.status == 200
                if success:
                    await response.json()  # JSON 응답 파싱까지 확인
                return success, elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"API 호출 실패 ({endpoint}): {e}")
            return False, elapsed

    @pytest.mark.asyncio
    async def test_concurrent_streaming_execution(self, simple_workflow_data):
        """동시 스트리밍 실행 테스트 - 블로킹 없이 독립적으로 실행되는지 확인"""
        logger.info("🚀 동시 스트리밍 실행 테스트 시작")
        
        num_clients = 3
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=120)
        
        async with aiohttp.ClientSession(
            connector=connector, 
            timeout=timeout
        ) as session:
            
            # 동시 실행
            tasks = [
                self._execute_streaming_client(i, session, simple_workflow_data)
                for i in range(1, num_clients + 1)
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            logger.info(f"전체 테스트 완료: {total_time:.2f}초")
            
            # 결과 분석
            successful = 0
            execution_times = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Client {i+1}: 예외 발생 - {result}")
                    assert False, f"Client {i+1} failed with exception: {result}"
                else:
                    success, elapsed, chunk_count = result
                    if success:
                        successful += 1
                        execution_times.append(elapsed)
                        logger.info(f"Client {i+1}: 성공 ({elapsed:.2f}초, {chunk_count}개 청크)")
                    else:
                        logger.error(f"Client {i+1}: 실패 ({elapsed:.2f}초)")
            
            # 검증
            assert successful == num_clients, f"모든 클라이언트가 성공해야 함 (성공: {successful}/{num_clients})"
            
            if execution_times:
                avg_time = sum(execution_times) / len(execution_times)
                min_time = min(execution_times)
                max_time = max(execution_times)
                time_variance = max_time - min_time
                
                logger.info(f"평균 실행 시간: {avg_time:.2f}초")
                logger.info(f"최단/최장 실행 시간: {min_time:.2f}초 / {max_time:.2f}초")
                logger.info(f"시간 차이: {time_variance:.2f}초")
                
                # 블로킹 여부 판단 - 실행 시간 차이가 너무 크면 안됨 (기준 완화)
                assert time_variance < 20.0, f"클라이언트 간 실행 시간 차이가 너무 큽니다 ({time_variance:.2f}초). 블로킹이 있을 수 있습니다."
                
                logger.info("✅ 동시 스트리밍 실행이 성공적으로 완료되었습니다.")

    @pytest.mark.asyncio
    async def test_streaming_during_api_calls(self, simple_workflow_data):
        """스트리밍 실행 중 다른 API 호출이 블로킹되지 않는지 테스트"""
        logger.info("🔄 스트리밍 중 API 호출 테스트 시작")
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=120)
        
        async with aiohttp.ClientSession(
            connector=connector, 
            timeout=timeout
        ) as session:
            
            # 백그라운드에서 스트리밍 실행
            streaming_task = asyncio.create_task(
                self._execute_streaming_client(1, session, simple_workflow_data)
            )
            
            # 스트리밍 시작 후 잠시 대기
            await asyncio.sleep(1.0)
            
            # 스트리밍 실행 중에 다른 API들 호출
            api_endpoints = [
                "/",
                "/knowledge-bases", 
                "/available-models/google"
            ]
            
            api_tasks = [
                self._call_api_endpoint(session, endpoint)
                for endpoint in api_endpoints
            ]
            
            # API 호출들이 빠르게 완료되는지 확인
            api_start_time = time.time()
            api_results = await asyncio.gather(*api_tasks, return_exceptions=True)
            api_total_time = time.time() - api_start_time
            
            # 스트리밍 완료 대기
            streaming_result = await streaming_task
            
            # API 결과 검증
            logger.info(f"API 호출들 완료: {api_total_time:.3f}초")
            
            for i, (endpoint, result) in enumerate(zip(api_endpoints, api_results)):
                if isinstance(result, Exception):
                    assert False, f"API 호출 실패 ({endpoint}): {result}"
                else:
                    success, elapsed = result
                    logger.info(f"{endpoint}: {elapsed:.3f}초 ({'성공' if success else '실패'})")
                    assert success, f"API 호출이 실패했습니다: {endpoint}"
                    
                    # API 호출이 너무 오래 걸리면 안됨 (블로킹 의심) - 기준 완화
                    assert elapsed < 10.0, f"API 호출이 너무 오래 걸립니다 ({endpoint}: {elapsed:.3f}초). 블로킹이 있을 수 있습니다."
            
            # 스트리밍 결과 검증
            assert not isinstance(streaming_result, Exception), f"스트리밍 실행 실패: {streaming_result}"
            success, elapsed, chunk_count = streaming_result
            assert success, f"스트리밍 실행이 실패했습니다 ({elapsed:.2f}초)"
            
            logger.info("✅ 스트리밍 중 API 호출이 성공적으로 완료되었습니다.")

    @pytest.mark.asyncio
    async def test_api_response_times(self):
        """기본 API 응답 시간 테스트"""
        logger.info("⏱️ API 응답 시간 테스트 시작")
        
        async with aiohttp.ClientSession() as session:
            api_endpoints = [
                ("/", "헬스체크"),
                ("/knowledge-bases", "지식베이스 목록"),
                ("/available-models/google", "Google 모델 목록")
            ]
            
            for endpoint, description in api_endpoints:
                success, elapsed = await self._call_api_endpoint(session, endpoint)
                logger.info(f"{description}: {elapsed:.3f}초 ({'성공' if success else '실패'})")
                
                assert success, f"{description} API 호출 실패"
                # 기본 API들은 10초 이내에 응답해야 함 (초기 로드 땅문에 시간 여유)
                assert elapsed < 10.0, f"{description} API 응답이 너무 느립니다 ({elapsed:.3f}초)"

    @pytest.mark.asyncio 
    async def test_concurrent_different_workflows(self, simple_workflow_data):
        """서로 다른 워크플로우의 동시 실행 테스트"""
        logger.info("🔀 서로 다른 워크플로우 동시 실행 테스트 시작")
        
        # 두 번째 워크플로우 생성 (더 긴 프롬프트)
        workflow_2 = {
            "workflow": {
                "nodes": [
                    {
                        "id": "input-2",
                        "type": "input-node",
                        "position": {"x": 100, "y": 100},
                        "content": "두 번째 워크플로우의 테스트 입력입니다. 이 텍스트는 더 길어서 처리 시간이 다를 수 있습니다.",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    },
                    {
                        "id": "generation-2",
                        "type": "generation-node",
                        "position": {"x": 300, "y": 100},
                        "content": None,
                        "model_type": "gemini-2.0-flash",
                        "llm_provider": "google",
                        "prompt": "다음 텍스트를 자세히 분석하고 주요 포인트 3가지를 추출해주세요: {input_data}",
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    },
                    {
                        "id": "output-2",
                        "type": "output-node",
                        "position": {"x": 500, "y": 100},
                        "content": "분석 결과",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    }
                ],
                "edges": [
                    {"id": "edge-2-1", "source": "input-2", "target": "generation-2"},
                    {"id": "edge-2-2", "source": "generation-2", "target": "output-2"}
                ]
            }
        }
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=120)
        
        async with aiohttp.ClientSession(
            connector=connector, 
            timeout=timeout
        ) as session:
            
            # 서로 다른 워크플로우 동시 실행
            tasks = [
                self._execute_streaming_client(1, session, simple_workflow_data),
                self._execute_streaming_client(2, session, workflow_2)
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            logger.info(f"서로 다른 워크플로우 실행 완료: {total_time:.2f}초")
            
            # 결과 검증
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    assert False, f"Workflow {i+1} failed with exception: {result}"
                else:
                    success, elapsed, chunk_count = result
                    assert success, f"Workflow {i+1} 실행 실패 ({elapsed:.2f}초)"
                    logger.info(f"Workflow {i+1}: 성공 ({elapsed:.2f}초, {chunk_count}개 청크)")
            
            logger.info("✅ 서로 다른 워크플로우 동시 실행이 성공적으로 완료되었습니다.")

    @pytest.mark.asyncio
    async def test_concurrent_llm_workflows(self):
        """LLM이 포함된 워크플로우 동시 실행 테스트 (Google API 키가 있을 때만)"""
        import os
        if not os.getenv("GOOGLE_API_KEY"):
            pytest.skip("Google API 키가 설정되지 않았습니다. 실제 LLM 동시성 테스트를 건너뜁니다.")
        
        logger.info("🤖 LLM 워크플로우 동시성 테스트 시작")
        
        # LLM이 포함된 워크플로우
        llm_workflow = {
            "workflow": {
                "nodes": [
                    {
                        "id": "input-llm",
                        "type": "input-node",
                        "position": {"x": 100, "y": 100},
                        "content": "이것은 LLM 테스트용 짧은 텍스트입니다.",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    },
                    {
                        "id": "generation-llm",
                        "type": "generation-node",
                        "position": {"x": 300, "y": 100},
                        "content": None,
                        "model_type": "gemini-1.5-flash",
                        "llm_provider": "google",
                        "prompt": "다음 텍스트를 한 문장으로 요약하세요: {input_data}",
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    },
                    {
                        "id": "output-llm",
                        "type": "output-node",
                        "position": {"x": 500, "y": 100},
                        "content": "LLM 결과",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    }
                ],
                "edges": [
                    {"id": "edge-llm-1", "source": "input-llm", "target": "generation-llm"},
                    {"id": "edge-llm-2", "source": "generation-llm", "target": "output-llm"}
                ]
            }
        }
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=180)  # LLM 호출을 위해 더 긴 타임아웃
        
        async with aiohttp.ClientSession(
            connector=connector, 
            timeout=timeout
        ) as session:
            
            # 2개의 LLM 워크플로우 동시 실행
            tasks = [
                self._execute_streaming_client(1, session, llm_workflow),
                self._execute_streaming_client(2, session, llm_workflow)
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            logger.info(f"LLM 워크플로우 동시 실행 완료: {total_time:.2f}초")
            
            # 결과 검증
            successful = 0
            execution_times = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"LLM Workflow {i+1}: 예외 발생 - {result}")
                else:
                    success, elapsed, chunk_count = result
                    if success:
                        successful += 1
                        execution_times.append(elapsed)
                        logger.info(f"LLM Workflow {i+1}: 성공 ({elapsed:.2f}초, {chunk_count}개 청크)")
                    else:
                        logger.error(f"LLM Workflow {i+1}: 실패 ({elapsed:.2f}초)")
            
            # 최소 1개는 성공해야 함 (API 키가 유효하다면)
            assert successful >= 1, f"최소 1개의 LLM 워크플로우는 성공해야 함 (성공: {successful}/2)"
            
            if len(execution_times) >= 2:
                time_variance = max(execution_times) - min(execution_times)
                logger.info(f"LLM 실행 시간 차이: {time_variance:.2f}초")
                
                # LLM 호출은 시간이 더 걸릴 수 있으므로 관대한 기준
                assert time_variance < 30.0, f"LLM 워크플로우 간 실행 시간 차이가 너무 큽니다 ({time_variance:.2f}초)"
            
            logger.info("✅ LLM 워크플로우 동시성 테스트가 성공적으로 완료되었습니다.")


if __name__ == "__main__":
    # 단독 실행 시 (개발/디버깅용)
    import sys
    import os
    
    # 프로젝트 루트를 Python 경로에 추가
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    pytest.main([__file__, "-v", "-s"])