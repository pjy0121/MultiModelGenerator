#!/usr/bin/env python3
"""
스트리밍 동시성 테스트 스크립트
여러 클라이언트가 동시에 스트리밍 요청을 보내서 블로킹 여부를 확인
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

SERVER_URL = "http://localhost:5001"

# 테스트용 간단한 워크플로우 정의
TEST_WORKFLOW = {
    "workflow": {
        "nodes": [
            {
                "id": "input-1",
                "type": "input-node",
                "position": {"x": 100, "y": 100},
                "content": "테스트 입력 텍스트입니다.",
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
                "id": "generation-1",
                "type": "generation-node",
                "position": {"x": 300, "y": 100},
                "content": None,
                "model_type": "gemini-1.5-flash",
                "llm_provider": "google",
                "prompt": "다음 텍스트를 요약해주세요: {input}",
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
                "position": {"x": 500, "y": 100},
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
            {"id": "edge-1", "source": "input-1", "target": "generation-1"},
            {"id": "edge-2", "source": "generation-1", "target": "output-1"}
        ]
    }
}

async def streaming_client(client_id: int, session: aiohttp.ClientSession):
    """단일 클라이언트 스트리밍 테스트"""
    start_time = time.time()
    print(f"[Client {client_id}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]} - 스트리밍 시작")
    
    try:
        async with session.post(
            f"{SERVER_URL}/execute-workflow-stream",
            json=TEST_WORKFLOW,
            headers={"Content-Type": "application/json"}
        ) as response:
            
            if response.status != 200:
                print(f"[Client {client_id}] HTTP 오류: {response.status}")
                return False, time.time() - start_time
            
            # SSE 스트림 읽기
            chunk_count = 0
            async for line in response.content:
                line_str = line.decode('utf-8').strip()
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        chunk_count += 1
                        
                        # 주요 이벤트만 로그
                        if data.get('type') in ['start', 'node_start', 'complete', 'error']:
                            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                            print(f"[Client {client_id}] {timestamp} - {data.get('type')}: {data.get('message', '')}")
                        
                        # 완료 또는 에러 시 종료
                        if data.get('type') in ['complete', 'error']:
                            elapsed = time.time() - start_time
                            print(f"[Client {client_id}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]} - 완료 ({elapsed:.2f}초, {chunk_count}개 청크)")
                            return True, elapsed
                            
                    except json.JSONDecodeError:
                        continue
            
            elapsed = time.time() - start_time
            print(f"[Client {client_id}] 스트림 종료 ({elapsed:.2f}초, {chunk_count}개 청크)")
            return True, elapsed
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[Client {client_id}] 에러: {e} ({elapsed:.2f}초)")
        return False, elapsed

async def test_concurrent_streaming(num_clients: int = 3):
    """동시 스트리밍 테스트"""
    print(f"\n🚀 {num_clients}개 클라이언트 동시 스트리밍 테스트 시작")
    print(f"시작 시간: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 60)
    
    # 모든 클라이언트를 동시에 시작
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
    timeout = aiohttp.ClientTimeout(total=120)  # 2분 타임아웃
    
    async with aiohttp.ClientSession(
        connector=connector, 
        timeout=timeout
    ) as session:
        
        # 동시 실행
        tasks = [
            streaming_client(i, session) 
            for i in range(1, num_clients + 1)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        print("-" * 60)
        print(f"전체 테스트 완료: {total_time:.2f}초")
        
        # 결과 분석
        successful = 0
        failed = 0
        times = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Client {i+1}: 예외 발생 - {result}")
                failed += 1
            else:
                success, elapsed = result
                if success:
                    successful += 1
                    times.append(elapsed)
                else:
                    failed += 1
        
        print(f"\n📊 결과 요약:")
        print(f"- 성공: {successful}/{num_clients}")
        print(f"- 실패: {failed}/{num_clients}")
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            print(f"- 평균 실행 시간: {avg_time:.2f}초")
            print(f"- 최단 실행 시간: {min_time:.2f}초")
            print(f"- 최장 실행 시간: {max_time:.2f}초")
            print(f"- 시간 차이: {max_time - min_time:.2f}초")
            
            # 블로킹 여부 판단
            if max_time - min_time > 5.0:  # 5초 이상 차이나면 블로킹 의심
                print("⚠️  클라이언트 간 실행 시간 차이가 큽니다. 블로킹이 있을 수 있습니다.")
            else:
                print("✅ 클라이언트들이 비슷한 시간에 완료되었습니다. 블로킹이 해결된 것 같습니다.")

async def test_api_response_times():
    """기본 API 응답 시간 테스트"""
    print("\n🔍 API 응답 시간 테스트")
    print("-" * 40)
    
    async with aiohttp.ClientSession() as session:
        # 헬스체크
        start = time.time()
        async with session.get(f"{SERVER_URL}/") as response:
            if response.status == 200:
                health_time = time.time() - start
                print(f"헬스체크: {health_time:.3f}초")
        
        # 지식베이스 목록
        start = time.time()
        async with session.get(f"{SERVER_URL}/knowledge-bases") as response:
            if response.status == 200:
                kb_time = time.time() - start
                print(f"지식베이스 목록: {kb_time:.3f}초")
        
        # Google 모델 목록
        start = time.time()
        async with session.get(f"{SERVER_URL}/available-models/google") as response:
            if response.status == 200:
                models_time = time.time() - start
                print(f"Google 모델 목록: {models_time:.3f}초")

if __name__ == "__main__":
    print("🧪 MultiModelGenerator 스트리밍 동시성 테스트")
    print("=" * 60)
    
    # 기본 API 응답 시간 테스트
    asyncio.run(test_api_response_times())
    
    # 스트리밍 동시성 테스트 (3개 클라이언트)
    asyncio.run(test_concurrent_streaming(3))
    
    print("\n🎯 테스트 완료!")