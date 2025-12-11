"""Workflow node and execution models."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from .enums import NodeType


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
    rerank_provider: Optional[str] = Field(None, description="Rerank 사용 여부 for context-node ('none' or 'enabled')")
    rerank_model: Optional[str] = Field(None, description="[DEPRECATED] Rerank model - now uses fixed BAAI/bge-reranker-v2-m3")
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
