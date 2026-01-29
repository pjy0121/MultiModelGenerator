from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from ..config import SEARCH_INTENSITY_CONFIG

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
        """Return list of supported LLM providers"""
        return [cls.OPENAI, cls.GOOGLE, cls.INTERNAL]

    @classmethod
    def get_default_provider(cls) -> str:
        """Return default LLM provider"""
        return cls.GOOGLE

class SearchIntensity(str, Enum):
    EXACT = "exact"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    
    @classmethod
    def get_search_params(cls, intensity: str) -> Dict[str, any]:
        """Return parameters based on search mode (based on BGE-M3 actual similarity distribution)

        Top-K + Similarity Threshold parallel filtering:
        1. init: Initial search count (fetch from ChromaDB)
        2. similarity_threshold: Minimum similarity (cosine similarity 0.0~1.0)
        3. final: Final count after Reranker

        Threshold setting rationale (based on empirical data):
        - BGE-M3 actual similarity range: related documents at 0.2~0.4 level
        - Theoretical recommendations (0.8/0.65/0.5) are too high, filtering out most results
        - Practical values (0.3/0.25/0.2) adjusted to get appropriate search results

        - EXACT (high precision): init=10, final=5, threshold=0.3 (30%+ similarity)
          Use cases: "exact command ID", "specific spec"
          Characteristic: Select only clearly related documents

        - STANDARD (standard search): init=20, final=12, threshold=0.25 (25%+ similarity) [default]
          Use cases: "general features", "standard procedures"
          Characteristic: Include reasonably related documents, optimal for most cases

        - COMPREHENSIVE (broad search): init=40, final=25, threshold=0.2 (20%+ similarity)
          Use cases: "overall mechanisms", "exploratory research"
          Characteristic: Include all documents with any relevance possibility

        * Similarity Threshold: Filter irrelevant results (return at least 1 to prevent empty results)
        * With Reranker: LLM-based reranking of init results to final after threshold
        * Without Reranker: Return only threshold-filtered results
        """
        intensity_map = {
            cls.EXACT: SEARCH_INTENSITY_CONFIG["exact"],
            cls.STANDARD: SEARCH_INTENSITY_CONFIG["standard"],
            cls.COMPREHENSIVE: SEARCH_INTENSITY_CONFIG["comprehensive"]
        }
        return intensity_map.get(intensity, intensity_map[cls.STANDARD])
    
    @classmethod
    def from_top_k(cls, top_k: int) -> str:
        """Return appropriate search mode based on top_k value (criterion: final count)"""
        if top_k <= 12:
            return cls.EXACT
        elif top_k <= 30:
            return cls.STANDARD
        else:
            return cls.COMPREHENSIVE

    @classmethod
    def get_default(cls) -> str:
        """Return default search mode (balanced standard search)"""
        return cls.STANDARD

class RerankInfo(BaseModel):
    """Rerank configuration info"""
    provider: str = Field(..., description="Rerank provider (openai, google, etc.)")
    model: str = Field(..., description="Rerank model name")

class AvailableModel(BaseModel):
    """Available LLM model"""
    label: str = Field(..., description="Model name")
    provider: str = Field(..., description="LLM Provider")
    disabled: bool = Field(default=False, description="Disabled status")
    model_type: str = Field(..., description="Model type (actual model ID)")

class AvailableModelsResponse(BaseModel):
    """Available models list response"""
    models: List[AvailableModel] = Field(..., description="List of available models")

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
    # Rerank settings for context-node (fixed model: BAAI/bge-reranker-v2-m3)
    rerank_provider: Optional[str] = Field(None, description="Rerank enabled for context-node ('none' or 'enabled')")
    rerank_model: Optional[str] = Field(None, description="[DEPRECATED] Rerank model - now uses fixed BAAI/bge-reranker-v2-m3")
    # Additional context for context-node (user-defined content)
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
    """Folder or KB protection request"""
    path: str = Field(..., description="Folder path or KB name to protect")
    password: str = Field(..., description="Password for protection")
    reason: Optional[str] = Field("", description="Optional reason for protection")

class UnprotectionRequest(BaseModel):
    """Folder or KB unprotection request"""
    path: str = Field(..., description="Folder path or KB name to unprotect")
    password: str = Field(..., description="Password for verification")

class VerifyProtectionRequest(BaseModel):
    """Protection status and password verification request"""
    path: str = Field(..., description="Folder path or KB name to verify")
    type: str = Field(..., description="Type: 'folder' or 'kb'")
    password: str = Field(..., description="Password to verify")