from typing import List
from sentence_transformers import CrossEncoder
import asyncio
from concurrent.futures import ThreadPoolExecutor
from ..config import MODEL_REGISTRY

class ReRanker:
    """BGE Reranker를 사용한 문서 재정렬"""
    
    def __init__(self, provider: str, model: str = None):
        """
        Args:
            provider: 'internal' (고정)
            model: Reranker model name (defaults to MODEL_REGISTRY)
        """
        self.model_name = model or MODEL_REGISTRY["reranker"]["default"]
        self.reranker = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        print(f"🔧 ReRanker 초기화: {model}")

    def _lazy_load_model(self):
        """모델을 처음 사용할 때만 로드 (지연 로딩)"""
        if self.reranker is None:
            print(f"📦 Reranker 모델 로딩 중: {self.model_name}")
            self.reranker = CrossEncoder(self.model_name, max_length=512)
            print(f"✅ Reranker 모델 로드 완료")

    async def rerank_documents(self, query: str, documents: List[str], top_k_final: int) -> List[str]:
        """
        BGE Reranker를 사용하여 문서 목록을 쿼리와의 관련성 순으로 재정렬합니다.
        
        Args:
            query: 검색 쿼리
            documents: 재정렬할 문서 리스트
            top_k_final: 최종 반환할 문서 개수
            
        Returns:
            재정렬된 문서 리스트 (상위 top_k_final개)
        """
        if not documents:
            return []

        print(f"🔄 BGE Reranker를 사용하여 {len(documents)}개 문서 재정렬 중...")

        try:
            # 모델 로딩 (처음 한 번만)
            self._lazy_load_model()
            
            # CrossEncoder는 동기 함수이므로 ThreadPoolExecutor 사용
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(
                self._executor,
                self._compute_scores,
                query,
                documents
            )
            
            # 점수 기준으로 정렬 (내림차순)
            doc_score_pairs = list(zip(documents, scores))
            doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # 상위 top_k_final 개 선택
            reranked_docs = [doc for doc, score in doc_score_pairs[:top_k_final]]
            
            # 로깅
            print(f"✅ 재정렬 완료. 최종 {len(reranked_docs)}개 문서 선택.")
            print(f"   상위 3개 점수: {[f'{score:.4f}' for _, score in doc_score_pairs[:3]]}")
            
            return reranked_docs

        except Exception as e:
            print(f"⚠️ 재정렬 중 오류 발생: {e}. 원본 순서대로 상위 문서를 반환합니다.")
            import traceback
            traceback.print_exc()
            return documents[:top_k_final]

    def _compute_scores(self, query: str, documents: List[str]) -> List[float]:
        """CrossEncoder로 query-document 쌍의 점수 계산 (동기 함수)"""
        # CrossEncoder.predict()는 [[query, doc1], [query, doc2], ...] 형식 입력
        pairs = [[query, doc] for doc in documents]
        scores = self.reranker.predict(pairs)
        return scores.tolist()

"""
# 테스트용 코드
async def main():
    reranker = ReRanker()
    query = "NVMe 2.0의 새로운 기능은 무엇인가?"
    documents = [
        "문서 1: NVMe 1.4는...",
        "문서 2: Zoned Namespace는 NVMe 2.0의 핵심 기능 중 하나입니다.",
        "문서 3: PCIe 5.0 인터페이스에 대한 내용입니다.",
        "문서 4: NVMe 2.0에서는 Endurance Group Management가 도입되었습니다.",
        "문서 5: NVMe-oF(over Fabrics)에 대한 설명입니다."
    ]
    reranked = await reranker.rerank_documents(query, documents)
    print("\n[재정렬된 문서 순서]")
    for doc in reranked:
        print(f"- {doc[:30]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
"""
