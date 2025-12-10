"""BGE Reranker 테스트"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.services.rerank import ReRanker

async def test_rerank():
    print("=" * 60)
    print("BGE Reranker 테스트")
    print("=" * 60)
    
    # Reranker 초기화
    reranker = ReRanker(provider="internal", model="BAAI/bge-reranker-v2-m3")
    
    # 테스트 데이터
    query = "NVMe SSD의 성능 향상 방법"
    documents = [
        "NVMe는 PCIe 인터페이스를 사용하여 높은 성능을 제공합니다.",
        "오늘 날씨가 좋습니다. 산책하기 좋은 날씨입니다.",
        "SSD의 성능을 최적화하려면 TRIM 명령을 주기적으로 실행해야 합니다.",
        "파이썬은 인기 있는 프로그래밍 언어입니다.",
        "NVMe 드라이버를 최신 버전으로 업데이트하면 성능이 향상됩니다."
    ]
    
    print(f"\n쿼리: {query}")
    print(f"\n원본 문서 순서:")
    for i, doc in enumerate(documents):
        print(f"  {i+1}. {doc}")
    
    # 재정렬 실행
    print(f"\n재정렬 실행 중...")
    reranked = await reranker.rerank_documents(query, documents, top_k_final=3)
    
    print(f"\n재정렬된 문서 (상위 3개):")
    for i, doc in enumerate(reranked):
        print(f"  {i+1}. {doc}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_rerank())
