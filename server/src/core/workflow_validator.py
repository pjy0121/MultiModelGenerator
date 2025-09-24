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
    
    def _format_node_name(self, node_id: str, node_type: NodeType) -> str:
        """노드 이름을 사용자 친화적으로 포맷팅"""
        # 긴 ID의 경우 마지막 8자리만 사용
        if len(node_id) > 20:
            short_id = node_id[-8:]
            return f"{node_type.value} (...{short_id})"
        return f"{node_type.value} ({node_id})"
    
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
                # output-node는 여러 pre-node를 허용 (ensemble처럼 동작)
            
            elif node.type == NodeType.CONTEXT:
                # context-node: pre-node는 없어도 됨 (독립적 지식 베이스 검색), post-node는 필수
                if not post_nodes:
                    errors.append(f"context-node '{node_id}'에는 최소 하나의 post-node가 있어야 합니다.")
            
            else:
                # generation, ensemble, validation 노드들
                if not pre_nodes:
                    errors.append(f"노드 '{node_id}'에는 최소 하나의 pre-node가 있어야 합니다.")
                if not post_nodes:
                    errors.append(f"노드 '{node_id}'에는 최소 하나의 post-node가 있어야 합니다.")
            
            # 조건 3: pre-node 개수 제한 규칙
            # - output-node, ensemble-node: 제한 없음
            # - generation-node, validation-node: input-node 최대 1개 + context-node 최대 1개
            # - 다른 노드들: 일반 pre-node 1개 + context-node 최대 1개
            
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
            
            # context-node는 모든 노드에서 최대 1개만 허용
            if len(context_pre_nodes) > 1:
                node_name = self._format_node_name(node_id, node.type)
                errors.append(f"{node_name}: context-node는 최대 1개만 연결할 수 있습니다.")
            
            # 노드 타입별 pre-node 제한 검사
            if node.type == NodeType.GENERATION:
                # generation-node: input-node 최대 1개 + context-node 최대 1개만
                if len(input_pre_nodes) > 1:
                    node_name = self._format_node_name(node_id, node.type)
                    errors.append(f"{node_name}: input-node는 최대 1개만 연결할 수 있습니다.")
                if len(other_pre_nodes) > 0:
                    node_name = self._format_node_name(node_id, node.type)
                    errors.append(f"{node_name}: input-node와 context-node에서만 입력받을 수 있습니다.")
            elif node.type == NodeType.VALIDATION:
                # validation-node: 다른 LLM 노드들로부터 입력 가능, context-node 제외한 pre-node 최대 1개
                total_non_context = len(input_pre_nodes) + len(other_pre_nodes)
                if total_non_context > 1:
                    node_name = self._format_node_name(node_id, node.type)
                    errors.append(f"{node_name}: context-node를 제외한 입력은 최대 1개만 가능합니다.")
            elif node.type != NodeType.ENSEMBLE and node.type != NodeType.OUTPUT:
                # 다른 노드들 (input, context 제외): 일반 pre-node 1개 + context-node 최대 1개
                total_non_context = len(input_pre_nodes) + len(other_pre_nodes)
                if total_non_context > 1:
                    node_name = self._format_node_name(node_id, node.type)
                    errors.append(f"{node_name}: context-node를 제외한 입력은 최대 1개만 가능합니다.")
            
            # 조건 4: 여러 개의 post-node와 연결될 수 있는 노드는 input-node와 context-node뿐이다
            if len(post_nodes) > 1 and node.type != NodeType.INPUT and node.type != NodeType.CONTEXT:
                node_name = self._format_node_name(node_id, node.type)
                errors.append(f"{node_name}: 여러 출력을 가질 수 없습니다 (input-node와 context-node만 가능).")
            
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
        
        # generation-node: pre-node로 input-node와 context-node가 올 수 있다
        if node.type == NodeType.GENERATION:
            allowed_pre_types = {NodeType.INPUT, NodeType.CONTEXT}
            for pre_id in pre_nodes:
                pre_node = nodes_map.get(pre_id)
                if pre_node and pre_node.type not in allowed_pre_types:
                    errors.append(f"generation-node '{node.id}': pre-node로 input-node와 context-node만 올 수 있습니다.")
        
        # ensemble-node: pre-node로 output-node를 제외한 모든 노드들이 올 수 있다
        if node.type == NodeType.ENSEMBLE:
            for pre_id in pre_nodes:
                pre_node = nodes_map.get(pre_id)
                if pre_node and pre_node.type == NodeType.OUTPUT:
                    errors.append(f"ensemble-node '{node.id}': pre-node로 output-node는 올 수 없습니다.")
        
        # validation-node: pre-node로 input-node, generation-node, ensemble-node, validation-node가 올 수 있다
        if node.type == NodeType.VALIDATION:
            allowed_pre_types = {NodeType.INPUT, NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.CONTEXT}
            for pre_id in pre_nodes:
                pre_node = nodes_map.get(pre_id)
                if pre_node and pre_node.type not in allowed_pre_types:
                    errors.append(f"validation-node '{node.id}': pre-node로 {pre_node.type.value}는 올 수 없습니다.")
        
        # context-node: post-node로 generation-node, ensemble-node, validation-node, context-node, output-node가 올 수 있다 (input-node 제외)
        if node.type == NodeType.CONTEXT:
            allowed_post_types = {NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.CONTEXT, NodeType.OUTPUT}
            for post_id in post_nodes:
                post_node = nodes_map.get(post_id)
                if post_node and post_node.type not in allowed_post_types:
                    errors.append(f"context-node '{node.id}': post-node로 {post_node.type.value}는 올 수 없습니다.")
    
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