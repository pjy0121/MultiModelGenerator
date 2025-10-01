"""
ChromaDB 블로킹 문제 진단 도구
"""

import asyncio
import aiohttp
import time
import threading

async def diagnose_chromadb_blocking():
    """ChromaDB 블로킹 문제를 정확히 진단"""
    print("=== ChromaDB 블로킹 문제 진단 시작 ===")
    
    base_url = "http://localhost:5001"
    
    # 1. 단일 호출 성능 측정
    print("\n1. 단일 API 호출 성능 측정")
    single_times = []
    for i in range(3):
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f'{base_url}/knowledge-bases', timeout=15) as resp:
                    result = await resp.json()
                    response_time = time.time() - start_time
                    single_times.append(response_time)
                    print(f"호출 {i+1}: {response_time:.2f}초")
            except Exception as e:
                print(f"호출 {i+1} 실패: {str(e)}")
    
    if single_times:
        avg_single = sum(single_times) / len(single_times)
        print(f"단일 호출 평균: {avg_single:.2f}초")
    
    # 2. 동시 호출 - 타임아웃 패턴 확인
    print("\n2. 동시 API 호출 패턴 분석")
    
    async def timed_call(client_id: str, delay: float = 0):
        """시간 측정이 포함된 API 호출"""
        if delay > 0:
            await asyncio.sleep(delay)
            
        start_time = time.time()
        print(f"[{time.time():.2f}] 클라이언트 {client_id}: 호출 시작")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{base_url}/knowledge-bases', timeout=15) as resp:
                    result = await resp.json()
                    response_time = time.time() - start_time
                    print(f"[{time.time():.2f}] 클라이언트 {client_id}: 완료 ({response_time:.2f}초)")
                    return {
                        'client_id': client_id,
                        'success': True,
                        'response_time': response_time,
                        'start_time': start_time
                    }
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            print(f"[{time.time():.2f}] 클라이언트 {client_id}: 타임아웃 ({response_time:.2f}초)")
            return {
                'client_id': client_id,
                'success': False,
                'error': 'timeout',
                'response_time': response_time,
                'start_time': start_time
            }
        except Exception as e:
            response_time = time.time() - start_time
            print(f"[{time.time():.2f}] 클라이언트 {client_id}: 오류 ({response_time:.2f}초) - {str(e)}")
            return {
                'client_id': client_id,
                'success': False,
                'error': str(e),
                'response_time': response_time,
                'start_time': start_time
            }
    
    # 2개의 동시 호출
    print("2-1. 2개 동시 호출")
    tasks = [
        asyncio.create_task(timed_call("A")),
        asyncio.create_task(timed_call("B"))
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 결과 분석
    success_results = [r for r in results if isinstance(r, dict) and r['success']]
    failed_results = [r for r in results if isinstance(r, dict) and not r['success']]
    
    if success_results:
        times = [r['response_time'] for r in success_results]
        print(f"성공한 호출들: {len(success_results)}개, 평균 시간: {sum(times)/len(times):.2f}초")
        print(f"최대 시간: {max(times):.2f}초, 최소 시간: {min(times):.2f}초")
    
    if failed_results:
        print(f"실패한 호출들: {len(failed_results)}개")
        for r in failed_results:
            print(f"  - {r['client_id']}: {r.get('error', 'unknown')}")
    
    # 3. 간격을 두고 호출 - 큐잉 문제 확인
    print("\n3. 간격을 두고 호출 (0.1초 간격)")
    tasks = [
        asyncio.create_task(timed_call("S1", 0)),
        asyncio.create_task(timed_call("S2", 0.1)),
        asyncio.create_task(timed_call("S3", 0.2))
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    print("\n=== 진단 결과 요약 ===")
    if single_times and avg_single > 5.0:
        print("❌ 단일 호출도 느림 - ChromaDB 자체 성능 문제")
    elif failed_results:
        print("❌ 동시 호출에서 타임아웃 발생 - 파일 락/블로킹 문제 의심")
        print("   해결방안: Connection Pool 또는 단일 클라이언트 + 큐 방식")
    else:
        print("✅ 특별한 블로킹 문제 없음")

if __name__ == "__main__":
    asyncio.run(diagnose_chromadb_blocking())