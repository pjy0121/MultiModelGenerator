#!/usr/bin/env python3
"""
지식베이스 검색 성능 테스트 및 분석
"""

import asyncio
import time
from src.services.vector_store_service import VectorStoreService

async def test_search_performance():
    """지식베이스 검색 성능 테스트"""
    
    service = VectorStoreService()
    
    test_queries = [
        "NVMe SSD performance requirements",
        "storage device security features", 
        "PCIe interface specifications"
    ]
    
    kb_name = "large_nvme_2-2"
    
    print("=== 지식베이스 검색 성능 테스트 ===")
    print(f"지식베이스: {kb_name}")
    print(f"테스트 쿼리: {len(test_queries)}개")
    print("-" * 50)
    
    # 1. 리랭킹 없는 검색 테스트
    print("\n🔍 1. 리랭킹 없는 검색 테스트")
    for i, query in enumerate(test_queries, 1):
        start_time = time.time()
        try:
            results = await service.search(
                kb_name=kb_name,
                query=query,
                search_intensity="medium",
                rerank_info=None
            )
            search_time = time.time() - start_time
            print(f"   쿼리 {i}: {search_time:.2f}초 ({len(results)}개 결과)")
        except Exception as e:
            print(f"   쿼리 {i}: 실패 - {e}")
    
    # 2. 리랭킹 있는 검색 테스트 
    print("\n🔄 2. 리랭킹 있는 검색 테스트")
    rerank_info = {"provider": "openai", "model": "gpt-4o-mini"}
    
    for i, query in enumerate(test_queries, 1):
        start_time = time.time()
        try:
            results = await service.search(
                kb_name=kb_name,
                query=query,
                search_intensity="medium", 
                rerank_info=rerank_info
            )
            search_time = time.time() - start_time
            print(f"   쿼리 {i}: {search_time:.2f}초 ({len(results)}개 결과)")
        except Exception as e:
            print(f"   쿼리 {i}: 실패 - {e}")
    
    # 3. 병렬 검색 테스트
    print("\n⚡ 3. 병렬 검색 테스트 (리랭킹 없음)")
    start_time = time.time()
    
    tasks = []
    for query in test_queries:
        task = service.search(
            kb_name=kb_name,
            query=query,
            search_intensity="medium",
            rerank_info=None
        )
        tasks.append(task)
    
    try:
        results_list = await asyncio.gather(*tasks)
        parallel_time = time.time() - start_time
        print(f"   병렬 실행: {parallel_time:.2f}초 (총 {sum(len(r) for r in results_list)}개 결과)")
    except Exception as e:
        print(f"   병렬 실행 실패: {e}")
    
    # 4. 병렬 검색 테스트 (리랭킹 있음)
    print("\n⚡ 4. 병렬 검색 테스트 (리랭킹 있음)")
    start_time = time.time()
    
    tasks = []
    for query in test_queries:
        task = service.search(
            kb_name=kb_name,
            query=query,
            search_intensity="medium",
            rerank_info=rerank_info
        )
        tasks.append(task)
    
    try:
        results_list = await asyncio.gather(*tasks)
        parallel_time = time.time() - start_time
        print(f"   병렬 실행: {parallel_time:.2f}초 (총 {sum(len(r) for r in results_list)}개 결과)")
    except Exception as e:
        print(f"   병렬 실행 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_search_performance())