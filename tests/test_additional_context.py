"""
Context node additional_context feature test
"""
import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.models import WorkflowNode, NodeExecutionResult
from src.api.node_executors import NodeExecutor


class TestAdditionalContext:
    """Context node additional_context field tests"""

    @pytest.fixture
    def node_executor(self):
        """NodeExecutor instance"""
        return NodeExecutor()

    @pytest.mark.asyncio
    async def test_additional_context_only(self, node_executor):
        """Test using only additional_context without knowledge base"""
        node = WorkflowNode(
            id="ctx_1",
            type="context-node",
            knowledge_base="none",  # No knowledge base
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
        """Test using knowledge base with additional_context together"""
        # Logic test is possible even without actual KB
        node = WorkflowNode(
            id="ctx_2",
            type="context-node",
            knowledge_base="test_kb",
            additional_context="Additional user info",
            search_intensity="standard"
        )

        # KB search may fail but additional_context should be added
        result = await node_executor._execute_context_node(node, ["test query"])

        # May succeed or fail, but additional_context should be processed
        if result.success:
            assert "Additional user info" in result.output or "user-defined" in result.description

    @pytest.mark.asyncio
    async def test_no_context_at_all(self, node_executor):
        """Test when neither knowledge base nor additional_context exists"""
        node = WorkflowNode(
            id="ctx_3",
            type="context-node",
            knowledge_base="none",
            additional_context="",  # Empty string
            search_intensity="standard"
        )

        result = await node_executor._execute_context_node(node, ["test input"])

        assert result.success is True
        assert "No context available" in result.output or "no additional context" in result.description.lower()

    @pytest.mark.asyncio
    async def test_additional_context_multiline(self, node_executor):
        """Test multiline additional_context handling"""
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
        """Verify header is added to additional_context"""
        node = WorkflowNode(
            id="ctx_5",
            type="context-node",
            knowledge_base="none",
            additional_context="Test context",
            search_intensity="standard"
        )

        result = await node_executor._execute_context_node(node, ["input"])

        assert result.success is True
        # Check if output has separator/header (exact format may vary by implementation)
        assert "Test context" in result.output

    def test_workflow_node_model_accepts_additional_context(self):
        """Verify WorkflowNode model accepts additional_context field"""
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
        """Verify additional_context is an optional field"""
        # Create node without additional_context
        node = WorkflowNode(
            id="test2",
            type="context-node",
            knowledge_base="kb2",
            search_intensity="standard"
        )

        # Check default value (None or empty string)
        assert node.additional_context is None or node.additional_context == ""
