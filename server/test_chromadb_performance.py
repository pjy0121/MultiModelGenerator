"""
ChromaDB 동시 접근 테스트
"""

import asyncio
import aiohttp
import time

async def test_chromadb_concurrent_access():
    """ChromaDB에 동시 접근할 때의 성능 테스트"""
    print("=== ChromaDB 동시 접근 성능 테스트 시작 ===")
    
    base_url = "http://localhost:5001"
    
    async def access_knowledge_base(client_id: str):
        """지식베이스 목록 조회"""
        start_time = time.time()
        print(f"클라이언트 {client_id}: 지식베이스 목록 조회 시작 - {start_time:.2f}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f'{base_url}/knowledge-bases', timeout=15) as resp:
                    result = await resp.json()
                    end_time = time.time()
                    response_time = end_time - start_time
                    print(f"클라이언트 {client_id}: 지식베이스 목록 조회 완료 - {end_time:.2f} (응답시간: {response_time:.2f}초)")
                    return {
                        'client_id': client_id,
                        'success': resp.status == 200,
                        'response_time': response_time,
                        'kb_count': len(result.get('knowledge_bases', []))
                    }
            except Exception as e:
                print(f"클라이언트 {client_id}: 지식베이스 목록 조회 실패 - {str(e)}")
                return {
                    'client_id': client_id,
                    'success': False,
                    'error': str(e),
                    'response_time': time.time() - start_time
                }
    
    # 순차적으로 3번 호출
    print("\n--- 순차 호출 테스트 ---")
    sequential_results = []
    for i in range(3):
        result = await access_knowledge_base(f"SEQ{i+1}")
        sequential_results.append(result)
    
    sequential_avg = sum(r['response_time'] for r in sequential_results if r['success']) / len([r for r in sequential_results if r['success']])
    print(f"순차 평균 응답시간: {sequential_avg:.2f}초")
    
    # 동시에 3번 호출
    print("\n--- 동시 호출 테스트 ---")
    tasks = []
    for i in range(3):
        task = asyncio.create_task(access_knowledge_base(f"PARA{i+1}"))
        tasks.append(task)
    
    parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    parallel_times = [r['response_time'] for r in parallel_results if isinstance(r, dict) and r['success']]
    if parallel_times:
        parallel_avg = sum(parallel_times) / len(parallel_times)
        parallel_max = max(parallel_times)
        print(f"동시 평균 응답시간: {parallel_avg:.2f}초")
        print(f"동시 최대 응답시간: {parallel_max:.2f}초")
        
        if parallel_max > sequential_avg * 2:
            print("❌ 동시 접근에서 심각한 성능 저하 발견 - 블로킹 문제 의심")
        elif parallel_max > sequential_avg * 1.5:
            print("⚠️ 동시 접근에서 성능 저하 발견 - 경쟁 상태 의심")
        else:
            print("✅ 동시 접근 성능 정상")
    else:
        print("❌ 모든 동시 호출이 실패함")

if __name__ == "__main__":
    asyncio.run(test_chromadb_concurrent_access())