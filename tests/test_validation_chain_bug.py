"""
Validation node chain connection bug test
"""
import pytest
import sys
import os

# Add server path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from src.workflow import WorkflowValidator
from src.models import WorkflowDefinition, WorkflowNode, WorkflowEdge, NodeType


class TestValidationNodeChain:
    """Test validation-node chain connection issues"""
    
    def test_validation_to_validation_chain_should_be_allowed(self):
        """Test that validation-node → validation-node chain should be allowed"""
        
        # Create validation-node chain workflow
        nodes = [
            WorkflowNode(
                id="input_1",
                type=NodeType.INPUT,
                content="Test input"
            ),
            WorkflowNode(
                id="gen_1", 
                type=NodeType.GENERATION,
                model_type="gpt-4o-mini",
                llm_provider="openai",
                prompt="Generate requirements: {input_data}"
            ),
            WorkflowNode(
                id="val_1",
                type=NodeType.VALIDATION,
                model_type="gpt-4o-mini", 
                llm_provider="openai",
                prompt="First validation: {input_data}"
            ),
            WorkflowNode(
                id="val_2",
                type=NodeType.VALIDATION,
                model_type="gpt-4o-mini",
                llm_provider="openai", 
                prompt="Second validation: {input_data}"
            ),
            WorkflowNode(
                id="output_1",
                type=NodeType.OUTPUT,
                content=""
            )
        ]
        
        edges = [
            WorkflowEdge(id="e1", source="input_1", target="gen_1"),
            WorkflowEdge(id="e2", source="gen_1", target="val_1"),
            WorkflowEdge(id="e3", source="val_1", target="val_2"),  # validation → validation
            WorkflowEdge(id="e4", source="val_2", target="output_1")
        ]
        
        workflow = WorkflowDefinition(nodes=nodes, edges=edges)
        
        # Validate workflow
        validator = WorkflowValidator()
        result = validator.validate_workflow(workflow)
        
        # Debug: print all validation results
        print(f"\n=== Validation Chain Test ===")
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        print(f"Warnings: {result['warnings']}")
        
        # This should pass - validation chains should be allowed
        assert result['valid'], f"validation-node chain should be valid, but got errors: {result['errors']}"
    
    def test_validation_node_with_multiple_non_context_inputs_should_fail(self):
        """Test that validation-node with multiple non-context inputs should fail (this should reproduce the bug)"""
        
        nodes = [
            WorkflowNode(
                id="input_1",
                type=NodeType.INPUT,
                content="Test input"
            ),
            WorkflowNode(
                id="gen_1", 
                type=NodeType.GENERATION,
                model_type="gpt-4o-mini",
                llm_provider="openai",
                prompt="Generate requirements: {input_data}"
            ),
            WorkflowNode(
                id="gen_2", 
                type=NodeType.GENERATION,
                model_type="gpt-4o-mini",
                llm_provider="openai",
                prompt="Generate alternative: {input_data}"
            ),
            WorkflowNode(
                id="val_1",
                type=NodeType.VALIDATION,
                model_type="gpt-4o-mini", 
                llm_provider="openai",
                prompt="Validate both: {input_data}"
            ),
            WorkflowNode(
                id="output_1",
                type=NodeType.OUTPUT,
                content=""
            )
        ]
        
        edges = [
            WorkflowEdge(id="e1", source="input_1", target="gen_1"),
            WorkflowEdge(id="e2", source="input_1", target="gen_2"),
            WorkflowEdge(id="e3", source="gen_1", target="val_1"),  # gen_1 → validation
            WorkflowEdge(id="e4", source="gen_2", target="val_1"),  # gen_2 → validation (multiple non-context inputs!)
            WorkflowEdge(id="e5", source="val_1", target="output_1")
        ]
        
        workflow = WorkflowDefinition(nodes=nodes, edges=edges)
        
        # Validate workflow
        validator = WorkflowValidator()
        result = validator.validate_workflow(workflow)
        
        print(f"\n=== Multiple Inputs to Validation Test ===")
        print(f"Valid: {result['valid']}")
        print(f"Errors: {result['errors']}")
        print(f"Warnings: {result['warnings']}")
        
        # This should fail - validation-node can't have multiple non-context inputs
        chain_error = any("context-node를 제외한 입력은 최대 1개만" in error for error in result['errors'])
        
        if chain_error:
            print(f"\n✅ Correctly blocked multiple non-context inputs to validation-node")
        else:
            print(f"\n❌ Should have blocked multiple non-context inputs to validation-node!")
        
        assert not result['valid'], "validation-node with multiple non-context inputs should be invalid"
        assert chain_error, "Should get the specific 'context-node를 제외한 입력은 최대 1개만' error"
    
    def test_multiple_validation_node_chain(self):
        """Test longer validation-node chain (3 nodes)"""
        
        nodes = [
            WorkflowNode(
                id="input_1",
                type=NodeType.INPUT,
                content="Test input"
            ),
            WorkflowNode(
                id="gen_1", 
                type=NodeType.GENERATION,
                model_type="gpt-4o-mini",
                llm_provider="openai",
                prompt="Generate requirements: {input_data}"
            ),
            WorkflowNode(
                id="val_1",
                type=NodeType.VALIDATION,
                model_type="gpt-4o-mini", 
                llm_provider="openai",
                prompt="First validation: {input_data}"
            ),
            WorkflowNode(
                id="val_2",
                type=NodeType.VALIDATION,
                model_type="gpt-4o-mini",
                llm_provider="openai", 
                prompt="Second validation: {input_data}"
            ),
            WorkflowNode(
                id="val_3",
                type=NodeType.VALIDATION,
                model_type="gpt-4o-mini",
                llm_provider="openai", 
                prompt="Third validation: {input_data}"
            ),
            WorkflowNode(
                id="output_1",
                type=NodeType.OUTPUT,
                content=""
            )
        ]
        
        edges = [
            WorkflowEdge(id="e1", source="input_1", target="gen_1"),
            WorkflowEdge(id="e2", source="gen_1", target="val_1"),
            WorkflowEdge(id="e3", source="val_1", target="val_2"),  # validation → validation
            WorkflowEdge(id="e4", source="val_2", target="val_3"),  # validation → validation
            WorkflowEdge(id="e5", source="val_3", target="output_1")
        ]
        
        workflow = WorkflowDefinition(nodes=nodes, edges=edges)
        
        # Validate workflow
        validator = WorkflowValidator()
        result = validator.validate_workflow(workflow)
        
        # Should allow longer validation chains
        chain_errors = [error for error in result['errors'] if "context-node를 제외한 입력은 최대 1개만" in error]
        
        assert len(chain_errors) == 0, f"Multiple validation-node chain should be allowed, but got errors: {chain_errors}"