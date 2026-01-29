"""API request and response models."""

from pydantic import BaseModel, Field
from typing import List, Optional
from .workflow import WorkflowDefinition


class WorkflowExecutionRequest(BaseModel):
    workflow: WorkflowDefinition = Field(..., description="Workflow to execute")


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
