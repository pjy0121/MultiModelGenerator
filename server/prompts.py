"""기본 프롬프트 템플릿들"""

DEFAULT_PROMPTS = {
    "generation": """
키워드 '{keyword}'에 대한 요구사항을 생성해주세요.

**컨텍스트:**
{context}

**입력 데이터:**
{input_data}

**지침:**
1. 마크다운 표 형식으로 출력
2. 시각적 자료 참조 금지
3. 구체적이고 측정 가능한 요구사항

**출력 형식:**
| ID | 요구사항 (Requirement) | 출처 (Source) | 상세 설명 (Notes) |
|---|---|---|---|
| REQ-001 | ... | ... | ... |
""",
    
    "ensemble": """
다음 여러 결과들을 통합하여 하나의 일관된 요구사항 표를 만들어주세요.

**입력 결과들:**
{input_data}

**컨텍스트:**
{context}

**지침:**
1. 중복 제거 및 통합
2. 일관된 ID 체계 적용
3. 마크다운 표 형식 유지
4. 품질 높은 요구사항만 선별

**통합된 요구사항 표:**
""",
    
    "validation": """
다음 요구사항 표를 검증하고 개선해주세요.

**검증할 요구사항:**
{input_data}

**컨텍스트:**
{context}

**검증 기준:**
1. 원본 컨텍스트와의 일치성
2. 요구사항의 명확성
3. 측정 가능성
4. 완결성

**검증된 요구사항 표:**
"""
}

def get_default_prompt(layer_type: str) -> str:
    """레이어 타입별 기본 프롬프트 반환"""
    return DEFAULT_PROMPTS.get(layer_type, DEFAULT_PROMPTS["generation"])
