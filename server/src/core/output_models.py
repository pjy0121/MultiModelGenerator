"""
구조화된 출력을 위한 Pydantic 모델들
LangChain의 PydanticOutputParser와 함께 사용
"""
from pydantic import BaseModel, Field
from typing import Optional


class LayerOutput(BaseModel):
    """Layer 실행 결과의 구조화된 출력"""
    general_output: str = Field(
        description="사용자에게 표시될 일반적인 출력 내용",
        default=""
    )
    forward_data: str = Field(
        description="다음 레이어로 전달될 데이터",
        default=""
    )

    class Config:
        # JSON 파싱 시 추가 필드 허용
        extra = "allow"


class GenerationResult(BaseModel):
    """Generation Layer의 결과"""
    requirements: str = Field(description="생성된 요구사항")
    reasoning: Optional[str] = Field(description="생성 근거", default="")
    confidence: Optional[float] = Field(description="신뢰도 (0-1)", default=0.0)


class EnsembleResult(BaseModel):
    """Ensemble Layer의 결과"""
    synthesized_output: str = Field(description="통합된 결과")
    source_analysis: Optional[str] = Field(description="소스 분석", default="")
    quality_score: Optional[float] = Field(description="품질 점수 (0-1)", default=0.0)


class ValidationResult(BaseModel):
    """Validation Layer의 결과"""
    validation_status: str = Field(description="검증 상태 (passed/failed/warning)")
    validated_content: str = Field(description="검증된 최종 내용")
    issues: Optional[str] = Field(description="발견된 문제점", default="")
    suggestions: Optional[str] = Field(description="개선 제안", default="")