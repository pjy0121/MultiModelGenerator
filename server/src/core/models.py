from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union
from enum import Enum

class NodeType(str, Enum):
    INPUT = "input-node"
    GENERATION = "generation-node"
    ENSEMBLE = "ensemble-node"
    VALIDATION = "validation-node"
    CONTEXT = "context-node"
    OUTPUT = "output-node"

class LLMProvider(str, Enum):
    OPENAI = "openai"
    GOOGLE = "google"
    INTERNAL = "internal"
    
    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """지원되는 LLM Provider 목록 반환"""
        return [cls.OPENAI, cls.GOOGLE, cls.INTERNAL]
    
    @classmethod
    def get_default_provider(cls) -> str:
        """기본 LLM Provider 반환"""
        return cls.GOOGLE

class SearchIntensity(str, Enum):
    EXACT = "exact"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    
    @classmethod
    def get_search_params(cls, intensity: str) -> Dict[str, int]:
        """검색 모드에 따른 파라미터 반환
        
        - EXACT (정확 검색): 정확한 키워드 매칭 중심, 특정 용어 찾기
          init: 20개 (재정렬 전, ~3%), final: 10개 (재정렬 후, ~1.4%)
          사용 예: "SMART", "NVMe 2.0", "Error Code 0x05"
          
        - STANDARD (표준 검색): 일반적인 균형잡힌 검색, 대부분의 사용 사례 [기본값]
          init: 50개 (재정렬 전, ~7%), final: 30개 (재정렬 후, ~4%)
          사용 예: "SMART 속성 값", "전력 관리 모드", "오류 복구 절차"
          
        - COMPREHENSIVE (포괄 검색): 관련 문맥까지 포괄적 검색, 복잡한 분석
          init: 70개 (재정렬 전, ~10%), final: 40개 (재정렬 후, ~6%)
          사용 예: "PCIe 전력 관리의 모든 상태 전환 방법과 제약사항"
          
        * 600-700개 청크 기준 최적화됨
        """
        intensity_map = {
            cls.EXACT: {"init": 20, "final": 10},
            cls.STANDARD: {"init": 50, "final": 30},
            cls.COMPREHENSIVE: {"init": 70, "final": 40}
        }
        return intensity_map.get(intensity, intensity_map[cls.STANDARD])
    
    @classmethod
    def from_top_k(cls, top_k: int) -> str:
        """top_k 값을 기반으로 적절한 검색 모드 반환"""
        if top_k <= 25:
            return cls.EXACT
        elif top_k <= 55:
            return cls.STANDARD
        else:
            return cls.COMPREHENSIVE
    
    @classmethod
    def get_default(cls) -> str:
        """기본 검색 모드 반환 (균형잡힌 표준 검색)"""
        return cls.STANDARD

class RerankInfo(BaseModel):
    """Rerank 설정 정보"""
    provider: str = Field(..., description="rerank Provider (openai, google 등)")
    model: str = Field(..., description="rerank 모델명")

class AvailableModel(BaseModel):
    """사용 가능한 LLM 모델"""
    label: str = Field(..., description="모델 이름")
    provider: str = Field(..., description="LLM Provider")
    disabled: bool = Field(default=False, description="비활성화 여부")
    model_type: str = Field(..., description="모델 타입 (실제 모델 ID)")

class AvailableModelsResponse(BaseModel):
    """사용 가능한 모델 목록 응답"""
    models: List[AvailableModel] = Field(..., description="사용 가능한 모델 목록")

class WorkflowNode(BaseModel):
    id: str = Field(..., description="Node ID")
    type: NodeType = Field(..., description="Node type")
    position: Dict[str, float] = Field(default={"x": 0, "y": 0})
    content: Optional[str] = Field(None, description="Content for input/output nodes")
    model_type: Optional[str] = Field(None, description="LLM model")
    llm_provider: Optional[str] = Field(None, description="LLM provider")
    prompt: Optional[str] = Field(None, description="Prompt for LLM nodes")
    output_format: Optional[str] = Field(None, description="Expected output format for LLM nodes")
    knowledge_base: Optional[str] = Field(None, description="Knowledge base for context search")
    search_intensity: Optional[str] = Field(None, description="Search intensity for context search")
    # context-node용 rerank 설정 (새로 추가)
    rerank_provider: Optional[str] = Field(None, description="Rerank LLM provider for context-node")
    rerank_model: Optional[str] = Field(None, description="Rerank LLM model for context-node")
    # context-node용 추가 컨텍스트 (사용자 정의 내용)
    additional_context: Optional[str] = Field(None, description="Additional user-defined context for context-node")
    output: Optional[Any] = Field(None, description="Execution result")
    executed: bool = Field(default=False)
    error: Optional[str] = Field(None, description="")

class WorkflowEdge(BaseModel):
    id: str = Field(..., description="Edge ID")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")

class WorkflowDefinition(BaseModel):
    nodes: List[WorkflowNode] = Field(..., description="Node list")
    edges: List[WorkflowEdge] = Field(..., description="Edge list")

class WorkflowExecutionRequest(BaseModel):
    workflow: WorkflowDefinition = Field(..., description="Workflow to execute")

class NodeExecutionResult(BaseModel):
    node_id: str = Field(..., description="Node ID")
    success: bool = Field(..., description="Success")
    description: Optional[str] = Field(None, description="UI description")
    output: Optional[str] = Field(None, description="Output data")
    error: Optional[str] = Field(None, description="Error message")
    execution_time: float = Field(0.0, description="Node execution time in seconds")

class WorkflowExecutionResponse(BaseModel):
    success: bool = Field(..., description="Overall success")
    results: List[NodeExecutionResult] = Field(..., description="Results")
    final_output: Optional[str] = Field(None, description="Final output")
    error: Optional[str] = Field(None, description="Error message")
    total_execution_time: float = Field(0.0, description="Total execution time in seconds")
    execution_order: List[str] = Field(default_factory=list, description="Node execution order")

class ParsedNodeOutput(BaseModel):
    description: str = Field(..., description="UI description")
    output: str = Field(..., description="Next node data")

class KnowledgeBase(BaseModel):
    name: str = Field(..., description="KB name")
    chunk_count: int = Field(..., description="Chunk count")
    created_at: str = Field(..., description="Creation time")

class KnowledgeBaseListResponse(BaseModel):
    knowledge_bases: List[KnowledgeBase] = Field(..., description="KB list")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error detail")
    node_id: Optional[str] = Field(None, description="Error node ID")