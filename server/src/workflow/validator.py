"""
Workflow validation logic based on project_reference.md connection rules
"""

from typing import Dict, List, Set
from ..models import WorkflowDefinition, WorkflowNode, WorkflowEdge, NodeType

class WorkflowValidator:
    """
    Workflow validator
    Validates based on connection rules from project_reference.md
    """
    
    def _format_node_name(self, node_id: str, node_type: NodeType) -> str:
        """Format node name in user-friendly way"""
        # For long IDs, use only last 8 characters
        if len(node_id) > 20:
            short_id = node_id[-8:]
            return f"{node_type.value} (...{short_id})"
        return f"{node_type.value} ({node_id})"
    
    def validate_workflow(self, workflow: WorkflowDefinition) -> Dict[str, any]:
        """
        Validate entire workflow

        Returns:
            Dict: {"valid": bool, "errors": List[str], "warnings": List[str]}
        """
        errors = []
        warnings = []
        
        # Basic structure validation
        if not workflow.nodes:
            errors.append("Workflow has no nodes.")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check for duplicate node IDs
        node_ids = [node.id for node in workflow.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("Duplicate node IDs found.")

        # Edge validation
        self._validate_edges(workflow, errors)

        # Validate connection rules from project_reference.md
        self._validate_connection_rules(workflow, errors, warnings)

        # Validate required nodes exist
        self._validate_required_nodes(workflow, errors)

        # Validate context-node inputs
        self._validate_context_nodes_input(workflow, errors)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_edges(self, workflow: WorkflowDefinition, errors: List[str]):
        """Validate edges"""
        node_ids = {node.id for node in workflow.nodes}
        
        for edge in workflow.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge {edge.id}: Source node '{edge.source}' does not exist")

            if edge.target not in node_ids:
                errors.append(f"Edge {edge.id}: Target node '{edge.target}' does not exist")

            if edge.source == edge.target:
                errors.append(f"Edge {edge.id}: Self-connection is not allowed.")
    
    def _validate_connection_rules(self, workflow: WorkflowDefinition, errors: List[str], warnings: List[str]):
        """Validate connection rules from project_reference.md"""

        # Map pre-node and post-node for each node
        pre_nodes_map = self._build_pre_nodes_map(workflow)
        post_nodes_map = self._build_post_nodes_map(workflow)
        nodes_map = {node.id: node for node in workflow.nodes}
        
        for node in workflow.nodes:
            node_id = node.id
            pre_nodes = pre_nodes_map.get(node_id, [])
            post_nodes = post_nodes_map.get(node_id, [])
            
            # Rule 2: All nodes must have at least one pre-node and post-node
            # Exception: input-node cannot have pre-nodes, output-node cannot have post-nodes
            if node.type == NodeType.INPUT:
                if pre_nodes:
                    errors.append(f"input-node '{node_id}' cannot have pre-nodes.")
                if not post_nodes:
                    errors.append(f"input-node '{node_id}' must have at least one post-node.")

            elif node.type == NodeType.OUTPUT:
                if post_nodes:
                    errors.append(f"output-node '{node_id}' cannot have post-nodes.")
                if not pre_nodes:
                    errors.append(f"output-node '{node_id}' must have at least one pre-node.")
                # output-node allows multiple pre-nodes (acts like ensemble)

            elif node.type == NodeType.CONTEXT:
                # context-node: pre-node is optional (independent knowledge base search), post-node is required
                if not post_nodes:
                    errors.append(f"context-node '{node_id}' must have at least one post-node.")

            else:
                # generation, ensemble, validation nodes
                if not pre_nodes:
                    errors.append(f"Node '{node_id}' must have at least one pre-node.")
                if not post_nodes:
                    errors.append(f"Node '{node_id}' must have at least one post-node.")
            
            # Rule 3: Pre-node count limit rules
            # - output-node, ensemble-node: No limit (multiple context-nodes allowed)
            # - generation-node, validation-node: Max 1 input-node + multiple context-nodes allowed
            # - Other nodes: 1 regular pre-node + multiple context-nodes allowed
            
            context_pre_nodes = []
            input_pre_nodes = []
            other_pre_nodes = []
            
            for pre_node_id in pre_nodes:
                pre_node = nodes_map.get(pre_node_id)
                if pre_node:
                    if pre_node.type == NodeType.CONTEXT:
                        context_pre_nodes.append(pre_node_id)
                    elif pre_node.type == NodeType.INPUT:
                        input_pre_nodes.append(pre_node_id)
                    else:
                        other_pre_nodes.append(pre_node_id)
            
            # Multiple context-nodes are allowed (limit removed)

            # Check pre-node limits by node type
            if node.type == NodeType.GENERATION:
                # generation-node: max 1 input-node + max 1 context-node only
                if len(input_pre_nodes) > 1:
                    node_name = self._format_node_name(node_id, node.type)
                    errors.append(f"{node_name}: Can connect to at most 1 input-node.")
                if len(other_pre_nodes) > 0:
                    node_name = self._format_node_name(node_id, node.type)
                    errors.append(f"{node_name}: Can only receive input from input-node and context-node.")
            elif node.type == NodeType.VALIDATION:
                # validation-node: Can receive input from other LLM nodes, max 1 pre-node excluding context-node
                total_non_context = len(input_pre_nodes) + len(other_pre_nodes)
                if total_non_context > 1:
                    node_name = self._format_node_name(node_id, node.type)
                    errors.append(f"{node_name}: Can have at most 1 input excluding context-nodes.")
            elif node.type != NodeType.ENSEMBLE and node.type != NodeType.OUTPUT:
                # Other nodes (excluding input, context): 1 regular pre-node + max 1 context-node
                total_non_context = len(input_pre_nodes) + len(other_pre_nodes)
                if total_non_context > 1:
                    node_name = self._format_node_name(node_id, node.type)
                    errors.append(f"{node_name}: Can have at most 1 input excluding context-nodes.")
            
            # Rule 4: Only input-node and context-node can connect to multiple post-nodes
            if len(post_nodes) > 1 and node.type != NodeType.INPUT and node.type != NodeType.CONTEXT:
                node_name = self._format_node_name(node_id, node.type)
                errors.append(f"{node_name}: Cannot have multiple outputs (only input-node and context-node allowed).")

            # Validate connection limits by type
            self._validate_node_type_connections(node, pre_nodes, post_nodes, nodes_map, errors)
    
    def _validate_required_nodes(self, workflow: WorkflowDefinition, errors: List[str]):
        """Validate required nodes exist"""

        input_nodes = [node for node in workflow.nodes if node.type == NodeType.INPUT]
        output_nodes = [node for node in workflow.nodes if node.type == NodeType.OUTPUT]

        # Rule 5: Workflow must have one input-node and one output-node connected
        if not input_nodes:
            errors.append("Workflow has no input-node.")

        if not output_nodes:
            errors.append("Workflow has no output-node.")

        if len(output_nodes) > 1:
            errors.append("Only one output-node can exist.")
    
    def _validate_node_type_connections(
        self,
        node: WorkflowNode,
        pre_nodes: List[str],
        post_nodes: List[str],
        nodes_map: Dict[str, WorkflowNode],
        errors: List[str]
    ):
        """Validate connection limits by node type"""

        # generation-node: Can have input-node and context-node as pre-nodes
        if node.type == NodeType.GENERATION:
            allowed_pre_types = {NodeType.INPUT, NodeType.CONTEXT}
            for pre_id in pre_nodes:
                pre_node = nodes_map.get(pre_id)
                if pre_node and pre_node.type not in allowed_pre_types:
                    errors.append(f"generation-node '{node.id}': Only input-node and context-node can be pre-nodes.")

        # ensemble-node: Can have all nodes except output-node as pre-nodes
        if node.type == NodeType.ENSEMBLE:
            for pre_id in pre_nodes:
                pre_node = nodes_map.get(pre_id)
                if pre_node and pre_node.type == NodeType.OUTPUT:
                    errors.append(f"ensemble-node '{node.id}': output-node cannot be a pre-node.")

        # validation-node: Can have input-node, generation-node, ensemble-node, validation-node as pre-nodes
        if node.type == NodeType.VALIDATION:
            allowed_pre_types = {NodeType.INPUT, NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.CONTEXT}
            for pre_id in pre_nodes:
                pre_node = nodes_map.get(pre_id)
                if pre_node and pre_node.type not in allowed_pre_types:
                    errors.append(f"validation-node '{node.id}': {pre_node.type.value} cannot be a pre-node.")

        # context-node: Can have generation-node, ensemble-node, validation-node, context-node, output-node as post-nodes (excluding input-node)
        if node.type == NodeType.CONTEXT:
            allowed_post_types = {NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.CONTEXT, NodeType.OUTPUT}
            for post_id in post_nodes:
                post_node = nodes_map.get(post_id)
                if post_node and post_node.type not in allowed_post_types:
                    errors.append(f"context-node '{node.id}': {post_node.type.value} cannot be a post-node.")
    
    def _build_pre_nodes_map(self, workflow: WorkflowDefinition) -> Dict[str, List[str]]:
        """Map each node's pre-nodes"""
        pre_nodes_map = {}
        
        for node in workflow.nodes:
            pre_nodes_map[node.id] = []
        
        for edge in workflow.edges:
            if edge.target not in pre_nodes_map:
                pre_nodes_map[edge.target] = []
            pre_nodes_map[edge.target].append(edge.source)
        
        return pre_nodes_map
    
    def _build_post_nodes_map(self, workflow: WorkflowDefinition) -> Dict[str, List[str]]:
        """Map each node's post-nodes"""
        post_nodes_map = {}
        
        for node in workflow.nodes:
            post_nodes_map[node.id] = []
        
        for edge in workflow.edges:
            if edge.source not in post_nodes_map:
                post_nodes_map[edge.source] = []
            post_nodes_map[edge.source].append(edge.target)
        
        return post_nodes_map
    
    def _validate_context_nodes_input(self, workflow: WorkflowDefinition, errors: List[str]):
        """Validate context-node inputs - context-node must have input-node as pre-node"""

        # Build dependency graph
        pre_nodes_map = self._build_pre_nodes_map(workflow)
        node_lookup = {node.id: node for node in workflow.nodes}

        # Find context-nodes
        context_nodes = [node for node in workflow.nodes if node.type == NodeType.CONTEXT]

        for context_node in context_nodes:
            pre_node_ids = pre_nodes_map.get(context_node.id, [])

            # context-node must have at least one pre-node
            if not pre_node_ids:
                errors.append(f"context-node '{context_node.id}' must have input-node connected as pre-node.")
                continue

            # At least one pre-node of context-node must be input-node
            has_input_node = False
            for pre_node_id in pre_node_ids:
                pre_node = node_lookup.get(pre_node_id)
                if pre_node and pre_node.type == NodeType.INPUT:
                    has_input_node = True
                    break

            if not has_input_node:
                errors.append(f"context-node '{context_node.id}' must have input-node connected as pre-node.")