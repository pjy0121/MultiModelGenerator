"""
노드 기반 워크플로우를 위한 기본 프롬프트 템플릿
project_reference.md의 5가지 노드 타입별 프롬프트 정의
"""

# ==================== 노드 타입별 기본 프롬프트 ====================

NODE_PROMPTS = {
    # Generation 노드용 프롬프트
    "generation-node": """
당신은 기술 문서에서 요구사항을 추출하는 전문가입니다.

**입력 문서:**
{input_data}

**참고 컨텍스트:**
{context}

**작업 지시:**
입력된 기술 문서를 분석하여 기능적/비기능적 요구사항을 추출해주세요.
각 요구사항에는 관련 근거와 문서 위치를 포함해야 합니다.

**출력 형식:**
{output_format}

다음 JSON 형식으로 응답해주세요:
{{
    "description": "요구사항 추출 결과 요약",
    "output": "추출된 요구사항들의 상세 내용"
}}
""",

    # Ensemble 노드용 프롬프트  
    "ensemble-node": """
당신은 여러 요구사항 추출 결과를 통합하는 전문가입니다.

**입력 데이터 (여러 Generation 노드 결과):**
{input_data}

**참고 컨텍스트:**
{context}

**작업 지시:**
여러 개의 요구사항 추출 결과를 분석하여 다음을 수행해주세요:
1. 중복된 요구사항 제거
2. 상충하는 요구사항 식별 및 해결
3. 누락된 요구사항 보완
4. 통합된 요구사항 목록 생성

**출력 형식:**
{output_format}

다음 JSON 형식으로 응답해주세요:
{{
    "description": "요구사항 통합 결과 요약",
    "output": "통합된 최종 요구사항 목록"
}}
""",

    # Validation 노드용 프롬프트
    "validation-node": """
당신은 요구사항을 검증하고 개선하는 전문가입니다.

**검증할 요구사항:**
{input_data}

**참고 컨텍스트:**
{context}

**작업 지시:**
제공된 요구사항을 다음 기준으로 검증하고 개선해주세요:
1. 완전성 (Completeness): 모든 필요한 정보가 포함되었는가?
2. 일관성 (Consistency): 상충하는 요구사항이 없는가?
3. 명확성 (Clarity): 모호한 표현이 없는가?
4. 추적가능성 (Traceability): 원본 문서와의 연관성이 명확한가?
5. 검증가능성 (Verifiability): 테스트 가능한 형태인가?

**출력 형식:**
{output_format}

다음 JSON 형식으로 응답해주세요:
{{
    "description": "요구사항 검증 결과 요약",
    "output": "검증되고 개선된 최종 요구사항"
}}
"""
}

# ==================== 출력 형식 템플릿 ====================

OUTPUT_FORMATS = {
    "requirements_json": """
각 요구사항을 다음 JSON 형식으로 작성:
{{
    "requirements": [
        {{
            "id": "REQ-001",
            "type": "functional|non-functional",
            "title": "요구사항 제목",
            "description": "상세 설명",
            "priority": "high|medium|low",
            "source": "원본 문서 위치/페이지",
            "reference": "관련 근거 텍스트"
        }}
    ]
}}
""",
    
    "validation_result": """
검증 결과를 다음 형식으로 작성:
{{
    "validation_summary": {{
        "total_requirements": 숫자,
        "validated_requirements": 숫자,
        "issues_found": 숫자,
        "improvements_made": 숫자
    }},
    "requirements": [
        {{
            "id": "REQ-001",
            "status": "validated|needs_improvement|rejected",
            "title": "요구사항 제목",
            "description": "개선된 설명",
            "validation_notes": "검증 과정에서 발견된 이슈 및 개선사항",
            "source": "원본 문서 위치",
            "reference": "관련 근거"
        }}
    ]
}}
"""
}

# ==================== 유틸리티 함수 ====================

def get_node_prompt(node_type: str, node_id: str = None) -> str:
    """
    노드 타입에 맞는 기본 프롬프트 반환
    
    Args:
        node_type: 노드 타입 (generation-node, ensemble-node, validation-node)
        node_id: 특정 노드 ID (나중에 노드별 커스텀 프롬프트 지원용)
        
    Returns:
        프롬프트 템플릿 문자열
    """
    return NODE_PROMPTS.get(node_type, "")

def get_output_format(format_type: str) -> str:
    """
    출력 형식 템플릿 반환
    
    Args:
        format_type: 출력 형식 타입
        
    Returns:
        출력 형식 템플릿 문자열
    """
    return OUTPUT_FORMATS.get(format_type, "")

def create_node_prompts_dict(nodes: list, output_format: str = "requirements_json") -> dict:
    """
    노드 리스트로부터 node_prompts 딕셔너리 생성
    
    Args:
        nodes: 노드 설정 리스트
        output_format: 사용할 출력 형식
        
    Returns:
        {node_id: prompt_template} 딕셔너리
    """
    node_prompts = {}
    format_template = get_output_format(output_format)
    
    for node in nodes:
        # LLM 노드들만 프롬프트 필요
        if node.get('node_type') in ['generation-node', 'ensemble-node', 'validation-node']:
            base_prompt = get_node_prompt(node.get('node_type'))
            if base_prompt:
                node_prompts[node.get('id')] = base_prompt
    
    return node_prompts