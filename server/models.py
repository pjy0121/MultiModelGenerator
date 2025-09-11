from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ModelType(str, Enum):
    """사용 가능한 모델 타입"""
    PERPLEXITY_SONAR_PRO = "perplexity-sonar-pro"
    PERPLEXITY_SONAR_MEDIUM = "perplexity-sonar-medium"
    OPENAI_GPT4 = "openai-gpt-4"
    OPENAI_GPT35 = "openai-gpt-3.5-turbo"

class LayerType(str, Enum):
    """레이어 타입"""
    GENERATION = "generation"
    ENSEMBLE = "ensemble" 
    VALIDATION = "validation"

class NodeConfig(BaseModel):
    """노드 설정"""
    id: str = Field(..., description="노드 고유 ID")
    model_type: ModelType = Field(..., description="사용할 모델 타입")
    prompt: str = Field(..., description="프롬프트 내용")
    layer: LayerType = Field(..., description="소속 레이어")
    position: Dict[str, float] = Field(default={"x": 0, "y": 0}, description="UI상 위치")

class WorkflowConfig(BaseModel):
    """워크플로우 전체 설정"""
    generation_nodes: List[NodeConfig] = Field(..., description="생성 레이어 노드들")
    ensemble_node: NodeConfig = Field(..., description="앙상블 레이어 노드")
    validation_nodes: List[NodeConfig] = Field(..., description="검증 레이어 노드들")

class WorkflowRequest(BaseModel):
    """워크플로우 실행 요청"""
    knowledge_base: str = Field(..., description="사용할 지식베이스")
    keyword: str = Field(..., description="키워드")
    workflow_config: WorkflowConfig = Field(..., description="워크플로우 설정")

class NodeOutput(BaseModel):
    """노드 출력 결과"""
    node_id: str = Field(..., description="노드 ID")
    model_type: str = Field(..., description="모델 타입")
    requirements: str = Field(..., description="요구사항 표")
    execution_time: float = Field(..., description="실행 시간(초)")

class WorkflowResponse(BaseModel):
    """워크플로우 실행 응답"""
    success: bool = Field(..., description="성공 여부")
    knowledge_base: str = Field(..., description="사용된 지식베이스")
    keyword: str = Field(..., description="키워드")
    final_requirements: str = Field(..., description="최종 요구사항")
    node_outputs: List[NodeOutput] = Field(..., description="각 노드 출력")
    total_execution_time: float = Field(..., description="총 실행 시간")
    generated_at: datetime = Field(..., description="생성 시간")

class RequirementRequest(BaseModel):
    """요구사항 생성 요청 모델"""
    knowledge_base: str = Field(..., description="사용할 지식베이스 이름")
    keyword: str = Field(..., min_length=1, description="요구사항을 생성할 키워드")
    validation_rounds: int = Field(
        default=1, 
        ge=1, 
        le=5, 
        description="검증 횟수 (1-5회, 기본값: 1)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "knowledge_base": "security_spec",
                "keyword": "인증",
                "validation_rounds": 2
            }
        }

class RequirementResponse(BaseModel):
    """요구사항 생성 응답 모델"""
    success: bool = Field(..., description="요청 성공 여부")
    knowledge_base: str = Field(..., description="사용된 지식베이스")
    keyword: str = Field(..., description="요청된 키워드")
    requirements: str = Field(..., description="생성된 요구사항")
    chunks_found: int = Field(..., description="검색된 문서 청크 수")
    validation_rounds: int = Field(..., description="실행된 검증 횟수")
    generated_at: datetime = Field(..., description="생성 시간")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "knowledge_base": "security_spec",
                "keyword": "인증",
                "requirements": "| ID | 요구사항 (Requirement) | 출처 (Source) | 상세 설명 (Notes) |\n|---|---|---|---|",
                "chunks_found": 5,
                "validation_rounds": 2,
                "generated_at": "2025-09-10T03:24:00"
            }
        }

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    success: bool = False
    error_type: str = Field(..., description="에러 유형")
    error_message: str = Field(..., description="에러 메시지")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error_type": "KNOWLEDGE_BASE_NOT_FOUND",
                "error_message": "지식베이스 'test_spec'을 찾을 수 없습니다."
            }
        }

class KnowledgeBaseInfo(BaseModel):
    """지식베이스 정보 모델"""
    name: str = Field(..., description="지식베이스 이름")
    chunk_count: int = Field(..., description="저장된 청크 수")
    path: str = Field(..., description="저장 경로")
    exists: bool = Field(..., description="존재 여부")

class KnowledgeBaseListResponse(BaseModel):
    """지식베이스 목록 응답 모델"""
    success: bool = True
    knowledge_bases: List[KnowledgeBaseInfo] = Field(..., description="지식베이스 목록")
    total_count: int = Field(..., description="전체 지식베이스 수")
