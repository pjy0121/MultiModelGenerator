"""
VectorStore 검색 기능 테스트
"""

import asyncio
import aiohttp

async def test_vector_search():
    """VectorStore 검색 기능이 제대로 작동하는지 테스트"""
    print("=== VectorStore 검색 기능 테스트 시작 ===")
    
    base_url = "http://localhost:5001"
    
    # 지식베이스 목록 조회
    async with aiohttp.ClientSession() as session:
        # 1. 지식베이스 목록 확인
        async with session.get(f'{base_url}/knowledge-bases') as resp:
            kb_list = await resp.json()
            print(f"사용 가능한 지식베이스: {kb_list}")
            
            if not kb_list.get('knowledge_bases'):
                print("❌ 지식베이스가 없습니다.")
                return
            
            # NVMe 관련 지식베이스 찾아서 테스트
            nvme_kbs = [kb for kb in kb_list['knowledge_bases'] if 'nvme' in kb['name'].lower()]
            if nvme_kbs:
                test_kb = nvme_kbs[0]['name']  # sentence_nvme_2-2 같은 것
            else:
                test_kb = kb_list['knowledge_bases'][0]['name']
            print(f"테스트 지식베이스: {test_kb}")
            
        # 2. VectorStore 검색 테스트
        search_data = {
            'knowledge_base': test_kb,  # API에서 기대하는 파라미터 이름
            'query': 'NVMe',  # 간단한 검색어
            'top_k': 3
        }
        
        async with session.post(f'{base_url}/search-knowledge-base', json=search_data) as resp:
            if resp.status == 200:
                search_results = await resp.json()
                print(f"✅ 검색 성공!")
                print(f"검색 결과 개수: {len(search_results.get('results', []))}")
                
                if search_results.get('results'):
                    for i, result in enumerate(search_results['results'][:2]):  # 처음 2개만 표시
                        preview = result[:100] + "..." if len(result) > 100 else result
                        print(f"결과 {i+1}: {preview}")
                else:
                    print("⚠️ 검색 결과가 비어있습니다.")
            else:
                error_text = await resp.text()
                print(f"❌ 검색 실패: {resp.status} - {error_text}")

if __name__ == "__main__":
    asyncio.run(test_vector_search())