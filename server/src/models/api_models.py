"""API request and response models."""

from pydantic import BaseModel, Field
from typing import List, Optional
from .workflow import WorkflowDefinition


class WorkflowExecutionRequest(BaseModel):
    workflow: WorkflowDefinition = Field(..., description="Workflow to execute")


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
