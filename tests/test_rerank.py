"""BGE Reranker test"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.services.rerank import ReRanker

async def test_rerank():
    print("=" * 60)
    print("BGE Reranker Test")
    print("=" * 60)

    # Initialize Reranker
    reranker = ReRanker(provider="internal", model="BAAI/bge-reranker-v2-m3")

    # Test data
    query = "How to improve NVMe SSD performance"
    documents = [
        "NVMe uses PCIe interface to provide high performance.",
        "The weather is nice today. Great day for a walk.",
        "To optimize SSD performance, TRIM command should be run periodically.",
        "Python is a popular programming language.",
        "Updating NVMe drivers to the latest version improves performance."
    ]

    print(f"\nQuery: {query}")
    print(f"\nOriginal document order:")
    for i, doc in enumerate(documents):
        print(f"  {i+1}. {doc}")

    # Execute reranking
    print(f"\nExecuting reranking...")
    reranked = await reranker.rerank_documents(query, documents, top_k_final=3)

    print(f"\nReranked documents (top 3):")
    for i, doc in enumerate(reranked):
        print(f"  {i+1}. {doc}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_rerank())
