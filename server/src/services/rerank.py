from typing import List
from sentence_transformers import CrossEncoder
import asyncio
from concurrent.futures import ThreadPoolExecutor
from ..config import MODEL_REGISTRY

class ReRanker:
    """Document reranking using BGE Reranker"""

    def __init__(self, provider: str, model: str = None):
        """
        Args:
            provider: 'internal' (fixed)
            model: Reranker model name (defaults to MODEL_REGISTRY)
        """
        self.model_name = model or MODEL_REGISTRY["reranker"]["default"]
        self.reranker = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        print(f"🔧 ReRanker initialized: {model}")

    def _lazy_load_model(self):
        """Load model only on first use (lazy loading)"""
        if self.reranker is None:
            print(f"📦 Loading Reranker model: {self.model_name}")
            self.reranker = CrossEncoder(self.model_name, max_length=512)
            print(f"✅ Reranker model loaded")

    async def rerank_documents(self, query: str, documents: List[str], top_k_final: int) -> List[str]:
        """
        Rerank document list by relevance to query using BGE Reranker.

        Args:
            query: Search query
            documents: List of documents to rerank
            top_k_final: Number of documents to return

        Returns:
            Reranked document list (top top_k_final)
        """
        if not documents:
            return []

        print(f"🔄 Reranking {len(documents)} documents using BGE Reranker...")

        try:
            # Load model (only once)
            self._lazy_load_model()

            # Use ThreadPoolExecutor since CrossEncoder is synchronous
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(
                self._executor,
                self._compute_scores,
                query,
                documents
            )

            # Sort by score (descending)
            doc_score_pairs = list(zip(documents, scores))
            doc_score_pairs.sort(key=lambda x: x[1], reverse=True)

            # Select top top_k_final
            reranked_docs = [doc for doc, score in doc_score_pairs[:top_k_final]]

            # Logging
            print(f"✅ Reranking complete. Selected {len(reranked_docs)} final documents.")
            print(f"   Top 3 scores: {[f'{score:.4f}' for _, score in doc_score_pairs[:3]]}")

            return reranked_docs

        except Exception as e:
            print(f"⚠️ Error during reranking: {e}. Returning top documents in original order.")
            import traceback
            traceback.print_exc()
            return documents[:top_k_final]

    def _compute_scores(self, query: str, documents: List[str]) -> List[float]:
        """Compute query-document pair scores with CrossEncoder (synchronous function)"""
        # CrossEncoder.predict() expects input format: [[query, doc1], [query, doc2], ...]
        pairs = [[query, doc] for doc in documents]
        scores = self.reranker.predict(pairs)
        return scores.tolist()

"""
# Test code
async def main():
    reranker = ReRanker()
    query = "What are the new features in NVMe 2.0?"
    documents = [
        "Document 1: NVMe 1.4 is...",
        "Document 2: Zoned Namespace is one of the key features of NVMe 2.0.",
        "Document 3: Information about PCIe 5.0 interface.",
        "Document 4: NVMe 2.0 introduced Endurance Group Management.",
        "Document 5: Description of NVMe-oF (over Fabrics)."
    ]
    reranked = await reranker.rerank_documents(query, documents)
    print("\n[Reranked document order]")
    for doc in reranked:
        print(f"- {doc[:30]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
"""
