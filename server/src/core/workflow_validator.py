"""
Workflow validation logic based on project_reference.md connection rules
"""

from typing import Dict, List, Set
from ..core.models import WorkflowDefinition, WorkflowNode, WorkflowEdge, NodeType

class WorkflowValidator:
    """
    워크플로우 유효성 검증기
    project_reference.md의 연결 조건을 기반으로 검증
    """
    
    def validate_workflow(self, workflow: WorkflowDefinition) -> Dict[str, any]:
        """
        워크플로우 전체 유효성 검증
        
        Returns:
            Dict: {"valid": bool, "errors": List[str], "warnings": List[str]}
        """
        errors = []
        warnings = []
        
        # 기본 구조 검증
        if not workflow.nodes:
            errors.append("워크플로우에 노드가 없습니다.")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # 노드 ID 중복 검사
        node_ids = [node.id for node in workflow.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("중복된 노드 ID가 있습니다.")
        
        # 엣지 유효성 검사
        self._validate_edges(workflow, errors)
        
        # project_reference.md 연결 조건 검증
        self._validate_connection_rules(workflow, errors, warnings)
        
        # 필수 노드 존재 검증
        self._validate_required_nodes(workflow, errors)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_edges(self, workflow: WorkflowDefinition, errors: List[str]):
        """엣지 유효성 검증"""
        node_ids = {node.id for node in workflow.nodes}
        
        for edge in workflow.edges:
            if edge.source not in node_ids:
                errors.append(f"엣지 {edge.id}: 존재하지 않는 소스 노드 '{edge.source}'")
            
            if edge.target not in node_ids:
                errors.append(f"엣지 {edge.id}: 존재하지 않는 타겟 노드 '{edge.target}'")
            
            if edge.source == edge.target:
                errors.append(f"엣지 {edge.id}: 자기 자신으로의 연결은 허용되지 않습니다.")
    
    def _validate_connection_rules(self, workflow: WorkflowDefinition, errors: List[str], warnings: List[str]):
        """project_reference.md 연결 조건 검증"""
        
        # 노드별 pre-node, post-node 맵핑
        pre_nodes_map = self._build_pre_nodes_map(workflow)
        post_nodes_map = self._build_post_nodes_map(workflow)
        nodes_map = {node.id: node for node in workflow.nodes}
        
        for node in workflow.nodes:
            node_id = node.id
            pre_nodes = pre_nodes_map.get(node_id, [])
            post_nodes = post_nodes_map.get(node_id, [])
            
            # 조건 2: 모든 노드에는 최소 하나의 pre-node와 post-node가 있어야 한다
            # 단, input-node에는 pre-node가 존재할 수 없고 output-node에는 post-node가 존재할 수 없다
            if node.type == NodeType.INPUT:
                if pre_nodes:
                    errors.append(f"input-node '{node_id}'에는 pre-node가 존재할 수 없습니다.")
                if not post_nodes:
                    errors.append(f"input-node '{node_id}'에는 최소 하나의 post-node가 있어야 합니다.")
            
            elif node.type == NodeType.OUTPUT:
                if post_nodes:
                    errors.append(f"output-node '{node_id}'에는 post-node가 존재할 수 없습니다.")
                if not pre_nodes:
                    errors.append(f"output-node '{node_id}'에는 최소 하나의 pre-node가 있어야 합니다.")
            
            else:
                # generation, ensemble, validation 노드들
                if not pre_nodes:
                    errors.append(f"노드 '{node_id}'에는 최소 하나의 pre-node가 있어야 합니다.")
                if not post_nodes:
                    errors.append(f"노드 '{node_id}'에는 최소 하나의 post-node가 있어야 합니다.")
            
            # 조건 3: 여러 개의 pre-node와 연결될 수 있는 노드는 ensemble-node뿐이다
            if len(pre_nodes) > 1 and node.type != NodeType.ENSEMBLE:
                errors.append(f"노드 '{node_id}' ({node.type.value}): ensemble-node가 아닌 노드는 여러 개의 pre-node를 가질 수 없습니다.")
            
            # 조건 4: 여러 개의 post-node와 연결될 수 있는 노드는 input-node뿐이다
            if len(post_nodes) > 1 and node.type != NodeType.INPUT:
                errors.append(f"노드 '{node_id}' ({node.type.value}): input-node가 아닌 노드는 여러 개의 post-node를 가질 수 없습니다.")
            
            # 타입별 연결 제한 검증
            self._validate_node_type_connections(node, pre_nodes, post_nodes, nodes_map, errors)
    
    def _validate_required_nodes(self, workflow: WorkflowDefinition, errors: List[str]):
        """필수 노드 존재 검증"""
        
        input_nodes = [node for node in workflow.nodes if node.type == NodeType.INPUT]
        output_nodes = [node for node in workflow.nodes if node.type == NodeType.OUTPUT]
        
        # 조건 5: 최초 워크플로우에 input-node, output-node가 하나씩 연결된 채로 존재해야 한다
        if not input_nodes:
            errors.append("워크플로우에 input-node가 없습니다.")
        
        if not output_nodes:
            errors.append("워크플로우에 output-node가 없습니다.")
        
        if len(output_nodes) > 1:
            errors.append("output-node는 하나만 존재할 수 있습니다.")
    
    def _validate_node_type_connections(
        self, 
        node: WorkflowNode, 
        pre_nodes: List[str], 
        post_nodes: List[str],
        nodes_map: Dict[str, WorkflowNode],
        errors: List[str]
    ):
        """노드 타입별 연결 제한 검증"""
        
        # generation-node: pre-node로 input-node만 올 수 있다
        if node.type == NodeType.GENERATION:
            for pre_id in pre_nodes:
                pre_node = nodes_map.get(pre_id)
                if pre_node and pre_node.type != NodeType.INPUT:
                    errors.append(f"generation-node '{node.id}': pre-node로 input-node만 올 수 있습니다.")
        
        # ensemble-node: pre-node로 output-node를 제외한 모든 노드들이 올 수 있다
        if node.type == NodeType.ENSEMBLE:
            for pre_id in pre_nodes:
                pre_node = nodes_map.get(pre_id)
                if pre_node and pre_node.type == NodeType.OUTPUT:
                    errors.append(f"ensemble-node '{node.id}': pre-node로 output-node는 올 수 없습니다.")
        
        # validation-node: pre-node로 input-node, generation-node, ensemble-node, validation-node가 올 수 있다
        if node.type == NodeType.VALIDATION:
            allowed_pre_types = {NodeType.INPUT, NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION}
            for pre_id in pre_nodes:
                pre_node = nodes_map.get(pre_id)
                if pre_node and pre_node.type not in allowed_pre_types:
                    errors.append(f"validation-node '{node.id}': pre-node로 {pre_node.type.value}는 올 수 없습니다.")
    
    def _build_pre_nodes_map(self, workflow: WorkflowDefinition) -> Dict[str, List[str]]:
        """각 노드의 pre-nodes 맵핑"""
        pre_nodes_map = {}
        
        for node in workflow.nodes:
            pre_nodes_map[node.id] = []
        
        for edge in workflow.edges:
            if edge.target not in pre_nodes_map:
                pre_nodes_map[edge.target] = []
            pre_nodes_map[edge.target].append(edge.source)
        
        return pre_nodes_map
    
    def _build_post_nodes_map(self, workflow: WorkflowDefinition) -> Dict[str, List[str]]:
        """각 노드의 post-nodes 맵핑"""
        post_nodes_map = {}
        
        for node in workflow.nodes:
            post_nodes_map[node.id] = []
        
        for edge in workflow.edges:
            if edge.source not in post_nodes_map:
                post_nodes_map[edge.source] = []
            post_nodes_map[edge.source].append(edge.target)
        
        return post_nodes_map