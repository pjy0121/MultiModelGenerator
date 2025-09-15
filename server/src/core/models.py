from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Import LangChain Pydantic models
from src.langchain_parsers.output_parsers import LayerOutput, NodeOutput as LangChainNodeOutput

# 상수 정의
DEFAULT_TOP_K = 50
DEFAULT_VALIDATION_ROUNDS = 1
MIN_VALIDATION_ROUNDS = 1
MAX_VALIDATION_ROUNDS = 5

class AvailableModel(BaseModel):
    """사용 가능한 모델 정보"""
    model_config = {"protected_namespaces": ()}  # model_ 네임스페이스 보호 해제
    
    index: int = Field(..., description="모델 인덱스")
    value: str = Field(..., description="모델 값")
    label: str = Field(..., description="모델 라벨")
    provider: str = Field(..., description="LLM 제공자")
    disabled: bool = Field(default=False, description="비활성화 여부")
    model_type: str = Field(..., description="모델 타입 (실제 모델 ID)")

class AvailableModelsResponse(BaseModel):
    """사용 가능한 모델 목록 응답"""
    models: List[AvailableModel] = Field(..., description="모델 목록")
    available_providers: List[str] = Field(..., description="사용 가능한 제공자")
    total_count: int = Field(..., description="전체 모델 수")
    available_count: int = Field(..., description="사용 가능한 모델 수")

class LayerType(str, Enum):
    """레이어 타입"""
    GENERATION = "generation"
    ENSEMBLE = "ensemble" 
    VALIDATION = "validation"

class NodeConfig(BaseModel):
    """노드 설정"""
    model_config = {"protected_namespaces": ()}  # model_ 네임스페이스 보호 해제
    
    id: str = Field(..., description="노드 고유 ID")
    model: Optional[str] = Field(None, description="사용할 모델 이름")
    provider: Optional[str] = Field(None, description="LLM 제공자")
    prompt: str = Field(..., description="프롬프트 내용")
    layer: LayerType = Field(..., description="소속 레이어")
    position: Dict[str, float] = Field(default={"x": 0, "y": 0}, description="UI상 위치")

class NodeOutput(BaseModel):
    """노드 출력 결과 - LangChain 호환"""
    model_config = {"protected_namespaces": ()}  # model_ 네임스페이스 보호 해제
    
    node_id: str = Field(..., description="노드 ID")
    model_type: str = Field(..., description="모델 타입")
    requirements: str = Field(..., description="요구사항 표")
    execution_time: float = Field(..., description="실행 시간(초)")
    
    # LangChain 호환 필드 추가
    general_output: Optional[LayerOutput] = Field(None, description="구조화된 레이어 출력")
    forward_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="다음 레이어로 전달할 데이터")

    @classmethod
    def from_langchain_output(cls, langchain_output: LangChainNodeOutput, node_id: str, model_type: str, execution_time: float):
        """LangChain NodeOutput에서 변환"""
        return cls(
            node_id=node_id,
            model_type=model_type,
            requirements=langchain_output.general_output.content,  # content를 requirements로 매핑
            execution_time=execution_time,
            general_output=langchain_output.general_output,
            forward_data=langchain_output.forward_data
        )

# ==================== 새로운 개별 노드 실행 API 모델들 ====================

class SearchRequest(BaseModel):
    """컨텍스트 검색 요청"""
    knowledge_base: str = Field(..., description="사용할 지식 베이스")
    query: str = Field(..., description="검색 쿼리")
    top_k: Optional[int] = Field(DEFAULT_TOP_K, description="반환할 청크 수")

class SearchResponse(BaseModel):
    """컨텍스트 검색 응답"""
    success: bool = Field(..., description="성공 여부")
    knowledge_base: str = Field(..., description="사용된 지식 베이스")
    query: str = Field(..., description="검색 쿼리")
    chunks: List[str] = Field(..., description="검색된 청크들")
    chunk_count: int = Field(..., description="검색된 청크 수")

# ==================== Layer별 프롬프트 시스템 ====================

class LayerPromptRequest(BaseModel):
    layer_type: LayerType
    prompt: str
    layer_input: str
    knowledge_base: str
    top_k: Optional[int] = Field(default=DEFAULT_TOP_K, description="컨텍스트 검색 결과 수")
    nodes: List[Dict[str, Any]] = Field(default=[], description="실행할 노드들")
    context_chunks: Optional[List[str]] = []

class LayerPromptResponse(BaseModel):
    """Layer 실행 응답 - 새로운 구조"""
    success: bool
    layer_type: LayerType
    knowledge_base: str
    layer_input: str
    layer_prompt: str
    node_outputs: Dict[str, Any] = Field(..., description="노드별 general_output과 통합 forward_data")
    execution_time: float
    timestamp: str

class ValidationLayerPromptResponse(LayerPromptResponse):
    filtered_requirements: List[str] = Field(default_factory=list, description="필터링된 요구사항들")
    validation_changes: List[str] = Field(default_factory=list, description="검증 변경사항")
    final_validated_result: str = Field(default="", description="최종 검증된 결과물")
    validation_steps: List[dict] = Field(default_factory=list, description="각 노드별 검증 단계")

# ==================== 기본 응답 모델들 ====================

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    success: bool = False
    error_type: str = Field(..., description="에러 유형")
    error_message: str = Field(..., description="에러 메시지")

class KnowledgeBaseInfo(BaseModel):
    """지식 베이스 정보 모델"""
    name: str = Field(..., description="지식 베이스 이름")
    chunk_count: int = Field(..., description="저장된 청크 수")
    path: str = Field(..., description="저장 경로")
    exists: bool = Field(..., description="존재 여부")

class KnowledgeBaseListResponse(BaseModel):
    """지식 베이스 목록 응답 모델"""
    success: bool = True
    knowledge_bases: List[KnowledgeBaseInfo] = Field(..., description="지식 베이스 목록")
    total_count: int = Field(..., description="전체 지식 베이스 수")

# ==================== 새로운 GET 기반 워크플로우 실행 모델들 ====================

class SimpleWorkflowRequest(BaseModel):
    """단순 GET 요청 기반 워크플로우 실행"""
    knowledge_base: str = Field(..., description="사용할 지식 베이스 이름")
    keyword: str = Field(..., description="검색 키워드")
    search_intensity: str = Field(default="medium", description="검색 강도 (low/medium/high)")
    generation_nodes: int = Field(default=2, description="Generation 레이어 노드 개수")
    ensemble_nodes: int = Field(default=1, description="Ensemble 레이어 노드 개수") 
    validation_nodes: int = Field(default=1, description="Validation 레이어 노드 개수")
    model_name: str = Field(default="gpt-3.5-turbo", description="사용할 LLM 모델명")
    provider: str = Field(default="openai", description="LLM 제공자")

class SimpleWorkflowResponse(BaseModel):
    """단순 워크플로우 실행 결과"""
    success: bool = Field(..., description="실행 성공 여부")
    final_result: str = Field(..., description="최종 마크다운 표 결과")
    execution_summary: Dict[str, Any] = Field(..., description="실행 요약 정보")
    total_execution_time: float = Field(..., description="전체 실행 시간(초)")
