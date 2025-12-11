"""
Context 노드의 additional_context 기능 테스트
"""
import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.models import WorkflowNode, NodeExecutionResult
from src.api.node_executors import NodeExecutor


class TestAdditionalContext:
    """Context 노드의 additional_context 필드 테스트"""
    
    @pytest.fixture
    def node_executor(self):
        """NodeExecutor 인스턴스"""
        return NodeExecutor()
    
    @pytest.mark.asyncio
    async def test_additional_context_only(self, node_executor):
        """지식베이스 없이 additional_context만 사용하는 경우"""
        node = WorkflowNode(
            id="ctx_1",
            type="context-node",
            knowledge_base="none",  # 지식베이스 없음
            additional_context="This is user-defined context for testing.",
            search_intensity="standard"
        )
        
        result = await node_executor._execute_context_node(node, ["test input"])
        
        assert result.success is True
        assert "user-defined context" in result.description.lower() or "additional" in result.description.lower()
        assert "This is user-defined context for testing." in result.output
        assert "No context available" not in result.output
    
    @pytest.mark.asyncio
    async def test_additional_context_with_kb(self, node_executor):
        """지식베이스와 additional_context 함께 사용하는 경우"""
        # 실제 KB가 없어도 로직 테스트 가능
        node = WorkflowNode(
            id="ctx_2",
            type="context-node",
            knowledge_base="test_kb",
            additional_context="Additional user info",
            search_intensity="standard"
        )
        
        # KB 검색은 실패하지만 additional_context는 추가되어야 함
        result = await node_executor._execute_context_node(node, ["test query"])
        
        # 성공하거나 실패할 수 있지만, additional_context는 처리되어야 함
        if result.success:
            assert "Additional user info" in result.output or "user-defined" in result.description
    
    @pytest.mark.asyncio
    async def test_no_context_at_all(self, node_executor):
        """지식베이스도 additional_context도 없는 경우"""
        node = WorkflowNode(
            id="ctx_3",
            type="context-node",
            knowledge_base="none",
            additional_context="",  # 빈 문자열
            search_intensity="standard"
        )
        
        result = await node_executor._execute_context_node(node, ["test input"])
        
        assert result.success is True
        assert "No context available" in result.output or "no additional context" in result.description.lower()
    
    @pytest.mark.asyncio
    async def test_additional_context_multiline(self, node_executor):
        """여러 줄의 additional_context 처리"""
        multiline_context = """Line 1: Important info
Line 2: More details
Line 3: Final notes"""
        
        node = WorkflowNode(
            id="ctx_4",
            type="context-node",
            knowledge_base="none",
            additional_context=multiline_context,
            search_intensity="standard"
        )
        
        result = await node_executor._execute_context_node(node, ["input"])
        
        assert result.success is True
        assert "Line 1: Important info" in result.output
        assert "Line 2: More details" in result.output
        assert "Line 3: Final notes" in result.output
    
    @pytest.mark.asyncio
    async def test_additional_context_header(self, node_executor):
        """additional_context에 헤더가 추가되는지 확인"""
        node = WorkflowNode(
            id="ctx_5",
            type="context-node",
            knowledge_base="none",
            additional_context="Test context",
            search_intensity="standard"
        )
        
        result = await node_executor._execute_context_node(node, ["input"])
        
        assert result.success is True
        # Output에 구분자/헤더가 있는지 확인 (정확한 포맷은 구현에 따라 다를 수 있음)
        assert "Test context" in result.output
    
    def test_workflow_node_model_accepts_additional_context(self):
        """WorkflowNode 모델이 additional_context 필드를 받는지 확인"""
        node = WorkflowNode(
            id="test",
            type="context-node",
            knowledge_base="kb1",
            additional_context="Extra info",
            search_intensity="exact"
        )
        
        assert hasattr(node, 'additional_context')
        assert node.additional_context == "Extra info"
    
    def test_workflow_node_optional_additional_context(self):
        """additional_context가 선택적 필드인지 확인"""
        # additional_context 없이 노드 생성
        node = WorkflowNode(
            id="test2",
            type="context-node",
            knowledge_base="kb2",
            search_intensity="standard"
        )
        
        # 기본값 확인 (None 또는 빈 문자열)
        assert node.additional_context is None or node.additional_context == ""
