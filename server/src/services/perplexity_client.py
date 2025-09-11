from openai import OpenAI
from typing import List
from ..core.config import Config

class PerplexityClient:
    def __init__(self):
        try:
            self.client = OpenAI(
                api_key=Config.PERPLEXITY_API_KEY,
                base_url=Config.PERPLEXITY_BASE_URL
            )
        except Exception as e:
            print(f"⚠️ Perplexity 클라이언트 초기화 오류: {e}")
            print("💡 API 키가 올바른지 확인하거나 OpenAI 라이브러리 버전을 확인하세요.")
            raise
    
    def generate_requirements(self, keyword: str, context_chunks: List[str]) -> str:
        """모델 A: 키워드 기반 요구사항 생성"""
        print(f"🤖 생성 모델: '{keyword}' 요구사항 생성 중...")
        
        context = "\n\n".join(context_chunks)
        
        prompt = f"""
당신은 기술 사양서 분석 전문가입니다.

제공된 사양서 컨텍스트를 바탕으로 '{keyword}'에 대한 상세한 요구사항 목록을 생성해주세요.

**컨텍스트 (사양서 내용):**
{context}

**작업 지침:**
1. 제공된 컨텍스트에만 근거하여 요구사항을 도출하세요
2. 각 요구사항은 구체적이고 측정 가능해야 합니다
3. 'Figure', '그림', '도표', '차트' 등 시각적 자료 참조는 절대 포함하지 마세요
4. 요구사항은 명확하고 이해하기 쉽게 작성하세요
5. 컨텍스트에 없는 내용은 절대 추가하지 마세요
6. 각 요구사항에는 고유한 ID를 부여하세요 (예: {keyword.upper()[:3]}-001)

**출력 포맷:**
다음과 같은 마크다운 표 형식으로 작성하세요:

| ID | 요구사항 (Requirement) | 출처 (Source) | 상세 설명 (Notes) |
|---|---|---|---|
| {keyword.upper()[:3]}-001 | [구체적인 요구사항 내용] | [문서 섹션 번호 또는 페이지] | [추가 설명 또는 "-"] |

**키워드:** {keyword}

**요구사항 표:**
        """
        
        try:
            response = self.client.chat.completions.create(
                model="sonar-pro",
                messages=[
                    {"role": "system", "content": "당신은 정확한 기술 사양서 분석 전문가입니다. 주어진 컨텍스트에만 근거하여 답변하고, 시각적 자료 참조는 절대 포함하지 마세요. 결과는 반드시 마크다운 표 형식으로 출력하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"요구사항 생성 중 오류 발생: {e}")
            return f"오류 발생: {e}"
    
    def validate_requirements(self, requirements: str, context_chunks: List[str], round_number: int) -> str:
        """검증 모델: 요구사항 검증 및 정제"""
        print(f"🔬 검증 모델 {round_number}: 요구사항 검증 및 정제 중...")
        
        context = "\n\n".join(context_chunks)
        
        prompt = f"""
당신은 기술 문서 검증 전문가입니다. (검증 라운드: {round_number})

다음 요구사항 표를 검토하고 검증해주세요:

**원본 사양서 컨텍스트:**
{context}

**검토할 요구사항 표:**
{requirements}

**검증 작업:**
1. 각 요구사항이 원본 사양서 컨텍스트에서 실제로 도출 가능한지 확인
2. 컨텍스트에서 지원되지 않는 요구사항은 제거
3. 'Figure', '그림', '도표', '차트' 등 시각적 자료 참조가 포함된 요구사항은 수정 또는 제거
4. 모호하거나 부정확한 표현을 명확하게 수정
5. 요구사항 ID가 논리적으로 순서대로 되어 있는지 확인
6. 출처(Source) 정보가 정확한지 확인
7. 요구사항이 이해하기 쉽고 일목요연한지 확인
8. 중복된 요구사항이 있다면 통합하거나 제거
9. 요구사항의 완성도와 정확성을 높이세요

**출력 지침:**
- 원래 마크다운 표 형식 유지
- 검증된 요구사항만 포함
- 각 요구사항은 독립적으로 이해 가능해야 함
- 기술적 용어는 정확하게 사용
- ID 번호는 연속적으로 재정렬
- 품질이 향상된 요구사항 표 출력

**검증된 요구사항 표:**
        """
        
        try:
            response = self.client.chat.completions.create(
                model="sonar-pro",
                messages=[
                    {"role": "system", "content": f"당신은 엄격한 기술 문서 검증 전문가입니다 (검증 라운드 {round_number}). 원본 컨텍스트에서 지원되지 않는 내용과 시각적 자료 참조는 반드시 제거하세요. 각 검증 라운드마다 품질을 향상시키세요. 결과는 반드시 마크다운 표 형식으로 출력하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.05,
                max_tokens=2500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"검증 모델 {round_number} 중 오류 발생: {e}")
            return f"검증 라운드 {round_number} 오류 발생: {e}"
    
    def multi_stage_validation(self, keyword: str, context_chunks: List[str], validation_rounds: int = 1) -> str:
        """다단계 검증을 통한 요구사항 생성"""
        print(f"🚀 다단계 검증 시작: {validation_rounds}회 검증")
        print("=" * 50)
        
        # 1단계: 초기 요구사항 생성
        current_requirements = self.generate_requirements(keyword, context_chunks)
        
        if "오류 발생" in current_requirements:
            return current_requirements
        
        print(f"✅ 초기 생성 완료")
        
        # 2단계: 다중 검증 라운드
        for round_num in range(1, validation_rounds + 1):
            print(f"\n🔄 검증 라운드 {round_num}/{validation_rounds}")
            
            validated_requirements = self.validate_requirements(
                current_requirements, 
                context_chunks, 
                round_num
            )
            
            if "오류 발생" in validated_requirements:
                print(f"⚠️ 검증 라운드 {round_num}에서 오류 발생, 이전 결과 사용")
                break
            
            current_requirements = validated_requirements
            print(f"✅ 검증 라운드 {round_num} 완료")
        
        print("\n" + "=" * 50)
        print(f"🎉 {validation_rounds}회 검증 완료!")
        
        return current_requirements
    
    def get_available_models(self) -> List[str]:
        """사용 가능한 Perplexity 모델 목록 조회"""
        try:
            # Perplexity API는 현재 models 엔드포인트를 제공하지 않으므로
            # 알려진 모델 목록을 반환
            return [
                "sonar-pro",
                "sonar-medium", 
                "sonar-small",
                "llama-3.1-sonar-small-128k-online",
                "llama-3.1-sonar-large-128k-online",
                "llama-3.1-sonar-huge-128k-online"
            ]
        except Exception as e:
            print(f"⚠️ 모델 목록 조회 실패: {e}")
            # 기본 모델 목록 반환
            return ["sonar-pro", "sonar-medium"]
