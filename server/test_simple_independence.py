"""
간단한 클라이언트 독립성 테스트 스크립트
"""

import asyncio
import aiohttp
import time

async def test_basic_client_independence():
    """기본적인 클라이언트 독립성 테스트"""
    print("=== 클라이언트 독립성 기본 테스트 시작 ===")
    
    base_url = "http://localhost:5001"
    
    async def quick_api_call(client_id: str):
        """빠른 API 호출"""
        start_time = time.time()
        print(f"클라이언트 {client_id}: API 호출 시작 - {start_time:.2f}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f'{base_url}/knowledge-bases', timeout=10) as resp:
                    result = await resp.json()
                    end_time = time.time()
                    response_time = end_time - start_time
                    print(f"클라이언트 {client_id}: API 호출 완료 - {end_time:.2f} (응답시간: {response_time:.2f}초)")
                    return {
                        'client_id': client_id,
                        'success': resp.status == 200,
                        'response_time': response_time,
                        'kb_count': len(result.get('knowledge_bases', []))
                    }
            except Exception as e:
                print(f"클라이언트 {client_id}: API 호출 실패 - {str(e)}")
                return {
                    'client_id': client_id,
                    'success': False,
                    'error': str(e),
                    'response_time': time.time() - start_time
                }
    
    # 5개의 클라이언트가 동시에 API 호출
    tasks = []
    for i in range(5):
        task = asyncio.create_task(quick_api_call(f"C{i+1}"))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    print("\n=== 테스트 결과 ===")
    success_count = 0
    total_response_time = 0
    
    for result in results:
        print(f"클라이언트 {result['client_id']}: 성공={result['success']}, 응답시간={result.get('response_time', 0):.2f}초")
        if result['success']:
            success_count += 1
            total_response_time += result['response_time']
    
    if success_count > 0:
        avg_response_time = total_response_time / success_count
        print(f"\n성공한 호출 수: {success_count}/5")
        print(f"평균 응답시간: {avg_response_time:.2f}초")
        
        if avg_response_time < 2.0:
            print("✅ 클라이언트 독립성 테스트 통과! (평균 응답시간이 합리적)")
        else:
            print("❌ 클라이언트 독립성 테스트 실패! (평균 응답시간이 너무 김)")
    else:
        print("❌ 모든 API 호출이 실패함")

if __name__ == "__main__":
    asyncio.run(test_basic_client_independence())