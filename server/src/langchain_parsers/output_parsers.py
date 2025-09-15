"""
LangChain-based output parsing for structured outputs.
Provides Pydantic models and output parsers for workflow layer execution.
"""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser


class LayerOutput(BaseModel):
    """Pydantic model for layer execution output.
    
    This replaces the general_output dict with structured data.
    Supports different layer types (requirement, ensemble, validation).
    """
    
    content: str = Field(
        description="Main content of the layer output (text, reasoning, etc.)"
    )
    
    # For requirements layer
    requirements: Optional[List[str]] = Field(
        default=None,
        description="List of requirements (for requirement generation layers)"
    )
    
    # For ensemble layer  
    decisions: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of decisions with reasoning (for ensemble layers)"
    )
    
    final_decision: Optional[str] = Field(
        default=None,
        description="Final consensus decision (for ensemble layers)"
    )
    
    # For validation layer
    validation_results: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of validation checks with pass/fail status"
    )
    
    overall_valid: Optional[bool] = Field(
        default=None,
        description="Overall validation result (for validation layers)"
    )
    
    # Common fields
    confidence_score: Optional[float] = Field(
        default=None,
        description="Confidence score for the output (0.0 to 1.0)"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata for the output"
    )


class NodeOutput(BaseModel):
    """Pydantic model for complete node execution output.
    
    This replaces the NodeOutput dataclass with structured Pydantic model.
    Contains both layer output and forward data for next layer.
    """
    
    general_output: LayerOutput = Field(
        description="Structured output from the layer execution"
    )
    
    forward_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Data to forward to the next layer in the workflow"
    )
    
    execution_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Metadata about the execution (timing, model used, etc.)"
    )


class LayerOutputParser:
    """Factory for creating layer-specific output parsers."""
    
    @staticmethod
    def get_requirements_parser() -> PydanticOutputParser:
        """Get parser for requirements generation layer."""
        return PydanticOutputParser(pydantic_object=LayerOutput)
    
    @staticmethod
    def get_ensemble_parser() -> PydanticOutputParser:
        """Get parser for ensemble decision layer."""
        return PydanticOutputParser(pydantic_object=LayerOutput)
    
    @staticmethod
    def get_validation_parser() -> PydanticOutputParser:
        """Get parser for validation layer."""
        return PydanticOutputParser(pydantic_object=LayerOutput)
    
    @staticmethod
    def get_node_parser() -> PydanticOutputParser:
        """Get parser for complete node output."""
        return PydanticOutputParser(pydantic_object=NodeOutput)


# Prompt templates for different layer types
REQUIREMENTS_PROMPT_TEMPLATE = """
다음 컨텍스트와 입력을 기반으로 요구사항을 생성하세요.

컨텍스트:
{context}

입력 데이터:
{input_data}

노드 프롬프트:
{node_prompt}

다음 형식으로 응답하세요:
1. 요구사항 분석 설명
2. 구체적인 요구사항 목록
3. 신뢰도 점수 (0.0-1.0)

{format_instructions}
"""

ENSEMBLE_PROMPT_TEMPLATE = """
여러 관점을 고려하여 최종 의사결정을 내리세요.

이전 결정들:
{previous_decisions}

컨텍스트:
{context}

입력 데이터:
{input_data}

노드 프롬프트:
{node_prompt}

다음 형식으로 응답하세요:
1. 분석 과정 설명
2. 각 관점별 의사결정과 근거
3. 최종 합의된 결정
4. 신뢰도 점수

{format_instructions}
"""

VALIDATION_PROMPT_TEMPLATE = """
주어진 요구사항이나 결정을 검증 기준에 따라 검증하세요.

검증할 항목들:
{items_to_validate}

검증 기준:
{criteria}

컨텍스트:
{context}

노드 프롬프트:
{node_prompt}

다음 형식으로 응답하세요:
1. 검증 과정 설명
2. 각 기준별 검증 결과 (통과/실패)
3. 전체 검증 결과 (true/false)
4. 신뢰도 점수

{format_instructions}
"""


def get_layer_prompt_template(layer_type: str) -> str:
    """Get the appropriate prompt template for a layer type."""
    templates = {
        'requirement': REQUIREMENTS_PROMPT_TEMPLATE,
        'ensemble': ENSEMBLE_PROMPT_TEMPLATE,
        'validation': VALIDATION_PROMPT_TEMPLATE
    }
    
    return templates.get(layer_type, REQUIREMENTS_PROMPT_TEMPLATE)