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
        """검색 모드에 따른 파라미터 반환 (BGE-M3 최적화 기준)
        
        - EXACT (고정밀 검색): 매우 높은 관련성만 필터링
          init: 10개, final: 5개, threshold: 0.25 (cosine similarity 0.75+ = 고품질 매칭)
          사용 예: "NVMe command set ID 0x1C", "PCIe Gen4 x4 specific feature"
          
        - STANDARD (표준 검색): 균형잡힌 품질-수량 [기본값]
          init: 20개, final: 12개, threshold: 0.40 (cosine similarity 0.60+ = 명확한 관련성)
          사용 예: "SMART 속성", "전력 관리 모드", "오류 처리 절차"
          
        - COMPREHENSIVE (포괄 검색): 넓은 컨텍스트 수집, 탐색적 쿼리
          init: 40개, final: 25개, threshold: 0.55 (cosine similarity 0.45+ = 잠재적 관련성)
          사용 예: "전체 열 관리 메커니즘", "프로토콜 전반적 개요"
          
        * ChromaDB cosine distance: 0=identical, 2=opposite (낮을수록 유사)
        * BGE-M3 최적화: 512 tokens chunk, 15% overlap, BAAI/bge-reranker-v2-m3
        * reranker 사용 시: init에서 광범위하게 검색 후 final로 정제
        """
        intensity_map = {
            cls.EXACT: {"init": 10, "final": 5, "threshold": 0.25},         # 0.75+ similarity
            cls.STANDARD: {"init": 20, "final": 12, "threshold": 0.40},     # 0.60+ similarity
            cls.COMPREHENSIVE: {"init": 40, "final": 25, "threshold": 0.55} # 0.45+ similarity
        }
        return intensity_map.get(intensity, intensity_map[cls.STANDARD])
    
    @classmethod
    def from_top_k(cls, top_k: int) -> str:
        """top_k 값을 기반으로 적절한 검색 모드 반환"""
        if top_k <= 12:
            return cls.EXACT
        elif top_k <= 30:
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

class ProtectionRequest(BaseModel):
    """폴더 또는 KB 보호 요청"""
    path: str = Field(..., description="Folder path or KB name to protect")
    password: str = Field(..., description="Password for protection")
    reason: Optional[str] = Field("", description="Optional reason for protection")

class UnprotectionRequest(BaseModel):
    """폴더 또는 KB 보호 해제 요청"""
    path: str = Field(..., description="Folder path or KB name to unprotect")
    password: str = Field(..., description="Password for verification")

class VerifyProtectionRequest(BaseModel):
    """보호 상태 및 비밀번호 검증 요청"""
    path: str = Field(..., description="Folder path or KB name to verify")
    type: str = Field(..., description="Type: 'folder' or 'kb'")
    password: str = Field(..., description="Password to verify")