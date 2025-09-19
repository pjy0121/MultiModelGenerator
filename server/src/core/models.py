from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union
from enum import Enum

class NodeType(str, Enum):
    INPUT = "input-node"
    GENERATION = "generation-node"
    ENSEMBLE = "ensemble-node"
    VALIDATION = "validation-node"
    OUTPUT = "output-node"

class SearchIntensity(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    VERY_HIGH = "very_high"

class RerankInfo(BaseModel):
    """Rerank 설정 정보"""
    provider: str = Field(..., description="rerank 제공자 (openai, google 등)")
    model: str = Field(..., description="rerank 모델명")

class AvailableModel(BaseModel):
    """사용 가능한 LLM 모델"""
    label: str = Field(..., description="모델 이름")
    provider: str = Field(..., description="LLM 제공자")
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
    rerank_enabled: bool = Field(default=False, description="Global rerank setting for all LLM nodes")

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