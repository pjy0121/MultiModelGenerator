"""Knowledge base models."""

from pydantic import BaseModel, Field
from typing import List


class KnowledgeBase(BaseModel):
    name: str = Field(..., description="KB name")
    chunk_count: int = Field(..., description="Chunk count")
    created_at: str = Field(..., description="Creation time")


class KnowledgeBaseListResponse(BaseModel):
    knowledge_bases: List[KnowledgeBase] = Field(..., description="KB list")
