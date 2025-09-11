from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ModelType(str, Enum):
    """사용 가능한 모델 타입"""
    PERPLEXITY_SONAR_PRO = "sonar-pro"
    PERPLEXITY_SONAR_MEDIUM = "sonar-medium"
    OPENAI_GPT4 = "gpt-4"
    OPENAI_GPT35 = "gpt-3.5-turbo"

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

class NodeOutput(BaseModel):
    """노드 출력 결과"""
    node_id: str = Field(..., description="노드 ID")
    model_type: str = Field(..., description="모델 타입")
    requirements: str = Field(..., description="요구사항 표")
    execution_time: float = Field(..., description="실행 시간(초)")

# ==================== 새로운 개별 노드 실행 API 모델들 ====================

class SearchRequest(BaseModel):
    """컨텍스트 검색 요청"""
    knowledge_base: str = Field(..., description="사용할 지식베이스")
    query: str = Field(..., description="검색 쿼리")
    top_k: Optional[int] = Field(5, description="반환할 청크 수")

class SearchResponse(BaseModel):
    """컨텍스트 검색 응답"""
    success: bool = Field(..., description="성공 여부")
    knowledge_base: str = Field(..., description="사용된 지식베이스")
    query: str = Field(..., description="검색 쿼리")
    chunks: List[str] = Field(..., description="검색된 청크들")
    chunk_count: int = Field(..., description="검색된 청크 수")

class SingleNodeRequest(BaseModel):
    """단일 노드 실행 요청"""
    knowledge_base: str = Field(..., description="사용할 지식베이스")
    input_data: str = Field(..., description="입력 데이터 (키워드 또는 이전 결과)")
    node_config: NodeConfig = Field(..., description="노드 설정")
    context_chunks: Optional[List[str]] = Field(None, description="컨텍스트 청크들 (선택사항)")

class SingleNodeResponse(BaseModel):
    """단일 노드 실행 응답"""
    success: bool = Field(..., description="성공 여부")
    node_output: NodeOutput = Field(..., description="노드 출력")
    context_chunks_used: List[str] = Field(..., description="사용된 컨텍스트 청크들")
    generated_at: datetime = Field(default_factory=datetime.now, description="생성 시간")

class EnsembleRequest(BaseModel):
    """앙상블 레이어 실행 요청"""
    knowledge_base: str = Field(..., description="사용할 지식베이스")
    generation_results: List[str] = Field(..., description="생성 레이어 결과들")
    ensemble_node: NodeConfig = Field(..., description="앙상블 노드 설정")
    context_chunks: Optional[List[str]] = Field(None, description="컨텍스트 청크들")

class ValidationChange(BaseModel):
    """검증 과정에서의 변경사항"""
    requirement_id: str = Field(..., description="요구사항 ID")
    original: str = Field(..., description="원본 요구사항")
    modified: str = Field(..., description="수정된 요구사항")
    change_type: str = Field(..., description="변경 타입 (added/modified/removed)")
    reason: str = Field(..., description="변경 이유")

class ValidationRequest(BaseModel):
    """검증 레이어 실행 요청"""
    knowledge_base: str = Field(..., description="사용할 지식베이스")
    input_requirements: str = Field(..., description="입력 요구사항")
    validation_node: NodeConfig = Field(..., description="검증 노드 설정")
    context_chunks: Optional[List[str]] = Field(None, description="컨텍스트 청크들")

class ValidationResponse(BaseModel):
    """검증 레이어 실행 응답"""
    success: bool = Field(..., description="성공 여부")
    node_output: NodeOutput = Field(..., description="노드 출력")
    changes: List[ValidationChange] = Field(..., description="변경사항 목록")
    context_chunks_used: List[str] = Field(..., description="사용된 컨텍스트 청크들")
    generated_at: datetime = Field(default_factory=datetime.now, description="생성 시간")

# ==================== Layer별 프롬프트 시스템 ====================

class LayerPromptRequest(BaseModel):
    layer_type: LayerType
    prompt: str
    input_data: str
    knowledge_base: str
    nodes: List[NodeConfig] = Field(default=[], description="실행할 노드들")
    context_chunks: Optional[List[str]] = []

class LayerPromptResponse(BaseModel):
    success: bool
    layer_type: LayerType
    knowledge_base: str
    input_data: str
    layer_prompt: str
    outputs: List[NodeOutput]
    combined_result: str
    failed_nodes: List[str]
    execution_time: float
    context_chunks_used: List[str]
    updated_input: str  # 다음 Layer나 노드를 위한 업데이트된 input

class ValidationLayerPromptResponse(LayerPromptResponse):
    filtered_requirements: List[str] = Field(default_factory=list, description="필터링된 요구사항들")
    validation_changes: List[ValidationChange] = Field(default_factory=list, description="검증 변경사항")
    final_validated_result: str = Field(default="", description="최종 검증된 결과물")
    validation_steps: List[dict] = Field(default_factory=list, description="각 노드별 검증 단계")

# ==================== 기존 Layer별 워크플로우 타입들 ====================

class LayerExecutionRequest(BaseModel):
    """Layer별 실행 요청"""
    knowledge_base: str = Field(..., description="사용할 지식베이스")
    input_data: str = Field(..., description="입력 데이터 (키워드 또는 이전 Layer 결과)")
    nodes: List[NodeConfig] = Field(..., description="실행할 노드들")
    context_chunks: Optional[List[str]] = Field(None, description="컨텍스트 청크들")

class LayerExecutionResponse(BaseModel):
    """Layer별 실행 응답"""
    success: bool = Field(..., description="성공 여부")
    layer_type: LayerType = Field(..., description="실행된 레이어 타입")
    knowledge_base: str = Field(..., description="사용된 지식베이스")
    input_data: str = Field(..., description="입력 데이터")
    outputs: List[NodeOutput] = Field(..., description="노드별 출력 결과")
    combined_result: str = Field(..., description="레이어 통합 결과")
    failed_nodes: List[str] = Field(default_factory=list, description="실패한 노드 ID들")
    execution_time: float = Field(..., description="총 실행 시간(초)")
    context_chunks_used: List[str] = Field(default_factory=list, description="사용된 컨텍스트 청크들")

class ValidationLayerResponse(LayerExecutionResponse):
    """Validation Layer 전용 응답 (필터링 정보 추가)"""
    filtered_requirements: List[str] = Field(default_factory=list, description="필터링된 요구사항들")
    validation_changes: List[ValidationChange] = Field(default_factory=list, description="각 노드별 검증 변경사항")

# ==================== 기존 통합 워크플로우 API 모델들 ====================

class WorkflowRequest(BaseModel):
    """워크플로우 실행 요청 (기존 API 호환용)"""
    knowledge_base: str = Field(..., description="사용할 지식베이스")
    keyword: str = Field(..., description="키워드")
    workflow_config: WorkflowConfig = Field(..., description="워크플로우 설정")

class WorkflowResponse(BaseModel):
    """워크플로우 실행 응답 (기존 API 호환용)"""
    success: bool = Field(..., description="성공 여부")
    knowledge_base: str = Field(..., description="사용된 지식베이스")
    keyword: str = Field(..., description="키워드")
    final_requirements: str = Field(..., description="최종 요구사항")
    node_outputs: List[NodeOutput] = Field(..., description="노드별 출력")
    total_execution_time: float = Field(..., description="총 실행 시간")
    generated_at: datetime = Field(default_factory=datetime.now, description="생성 시간")

# ==================== 기존 레거시 API 모델들 ====================

class RequirementRequest(BaseModel):
    """요구사항 생성 요청 모델 (레거시)"""
    knowledge_base: str = Field(..., description="사용할 지식베이스 이름")
    keyword: str = Field(..., min_length=1, description="요구사항을 생성할 키워드")
    validation_rounds: int = Field(
        default=1, 
        ge=1, 
        le=5, 
        description="검증 횟수 (1-5회, 기본값: 1)"
    )

class RequirementResponse(BaseModel):
    """요구사항 생성 응답 모델 (레거시)"""
    success: bool = Field(..., description="요청 성공 여부")
    knowledge_base: str = Field(..., description="사용된 지식베이스")
    keyword: str = Field(..., description="요청된 키워드")
    requirements: str = Field(..., description="생성된 요구사항")
    chunks_found: int = Field(..., description="검색된 문서 청크 수")
    validation_rounds: int = Field(..., description="실행된 검증 횟수")
    generated_at: datetime = Field(..., description="생성 시간")

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    success: bool = False
    error_type: str = Field(..., description="에러 유형")
    error_message: str = Field(..., description="에러 메시지")

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
