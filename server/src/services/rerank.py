from typing import List, Dict
from ..core.config import Config
from .llm_factory import LLMFactory
import json

class ReRanker:
    def __init__(self, provider: str = 'google', model: str = 'gemini-1.5-flash-latest'):
        self.llm_factory = LLMFactory()
        # API 요청으로 들어온 provider와 model을 사용
        self.client = self.llm_factory.get_client(provider)
        self.model = model

    async def rerank_documents(self, query: str, documents: List[str], top_k_final: int) -> List[str]:
        """
        LLM을 사용하여 문서 목록을 쿼리와의 관련성 순으로 재정렬합니다.
        """
        if not documents:
            return []

        print(f"🔄 LLM을 사용하여 {len(documents)}개 문서 재정렬 중...")

        # LLM에 전달할 프롬프트 생성
        prompt = self._build_rerank_prompt(query, documents)

        try:
            # LLM 호출
            response = await self.client.generate(self.model, prompt)
            
            # LLM 응답 파싱
            reranked_indices = self._parse_rerank_response(response, len(documents))
            
            # 인덱스를 기반으로 문서 재정렬
            reranked_docs = [documents[i] for i in reranked_indices if i < len(documents)]
            
            # 최종 top_k 만큼 선택
            final_docs = reranked_docs[:top_k_final]
            
            print(f"✅ 재정렬 완료. 최종 {len(final_docs)}개 문서 선택.")
            return final_docs

        except Exception as e:
            print(f"⚠️ 재정렬 중 오류 발생: {e}. 원본 순서대로 상위 문서를 반환합니다.")
            return documents[:top_k_final]

    def _build_rerank_prompt(self, query: str, documents: List[str]) -> str:
        """재정렬을 위한 LLM 프롬프트 구성"""
        
        docs_with_indices = "\n\n".join([f"### 문서 {i+1}\n{doc}" for i, doc in enumerate(documents)])

        return f"""
        당신은 주어진 쿼리와 가장 관련성이 높은 문서를 평가하고 순위를 매기는 전문가입니다.
        아래의 쿼리와 여러 문서가 주어집니다. 각 문서가 쿼리의 질문에 얼마나 잘 답변하는지 또는 쿼리의 핵심 주제와 얼마나 관련이 깊은지 평가해주세요.

        [쿼리]
        {query}

        [문서 목록]
        {docs_with_indices}

        [평가 및 순위 지정]
        1. 각 문서의 내용을 주의 깊게 읽고 쿼리와의 관련성을 평가합니다.
        2. 관련성이 가장 높은 순서대로 **문서의 번호(인덱스)**를 나열해주세요.
        3. 가장 관련성 높은 문서부터 내림차순으로 순위를 매깁니다.
        4. 최종 결과는 반드시 JSON 형식으로만 출력해야 하며, 'reranked_indices' 키에 정수 인덱스 배열(0부터 시작)을 포함해야 합니다.

        [출력 형식 예시]
        {{
          "reranked_indices": [2, 0, 4, 1, 3]
        }}
        """

    def _parse_rerank_response(self, response: str, num_docs: int) -> List[int]:
        """LLM의 재정렬 응답(JSON)을 파싱"""
        try:
            # 마크다운 코드 블록 제거
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            
            data = json.loads(response)
            indices = data.get("reranked_indices", [])
            
            # 인덱스는 1부터 시작하므로 0부터 시작하도록 변환
            # LLM이 1-based index를 반환하는 경향이 있으므로 보정
            if all(isinstance(i, int) and i > 0 for i in indices):
                 indices = [i - 1 for i in indices]

            # 유효성 검사
            valid_indices = [i for i in indices if isinstance(i, int) and 0 <= i < num_docs]
            
            # 중복 제거
            seen = set()
            unique_indices = [i for i in valid_indices if not (i in seen or seen.add(i))]
            
            return unique_indices

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"⚠️ 재정렬 응답 파싱 실패: {e}. 원본 순서로 대체합니다.")
            return list(range(num_docs))

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
