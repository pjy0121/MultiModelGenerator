import { WorkflowNode, WorkflowEdge, NodeType, ValidationResult } from '../types';

/**
 * project_reference.md 기준 노드 워크플로우 검증
 * 
 * 연결 규칙:
 * 1. input-node: pre-node 없음, 여러 post-node 가능
 * 2. generation-node: input-node → generation-node
 * 3. ensemble-node: 여러 pre-node 허용 → 단일 output  
 * 4. validation-node: 순차적 검증/개선
 * 5. output-node: post-node 없음, 단일 인스턴스
 * 6. 모든 노드는 pre/post 연결 필요 (input은 pre 제외, output은 post 제외)
 */

// 연결 허용 여부 검사 - 실시간 연결 검증용
export function isConnectionAllowed(
  sourceNode: WorkflowNode,
  targetNode: WorkflowNode,
  _nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): { allowed: boolean; reason?: string } {
  const sourceType = sourceNode.data.nodeType;
  const targetType = targetNode.data.nodeType;
  
  // 자기 자신과 연결 금지
  if (sourceNode.id === targetNode.id) {
    return { allowed: false, reason: "자기 자신과 연결할 수 없습니다." };
  }
  
  // 이미 연결된 경우 금지
  const existingConnection = edges.find(edge => 
    edge.source === sourceNode.id && edge.target === targetNode.id
  );
  if (existingConnection) {
    return { allowed: false, reason: "이미 연결되어 있습니다." };
  }
  
  // 현재 타겟 노드의 pre-node 수 계산
  const targetPreNodes = edges.filter(edge => edge.target === targetNode.id);
  
  // 현재 소스 노드의 post-node 수 계산
  const sourcePostNodes = edges.filter(edge => edge.source === sourceNode.id);
  
  // 규칙 1: input-node는 target이 될 수 없음
  if (targetType === NodeType.INPUT) {
    return { allowed: false, reason: "입력 노드는 연결의 대상이 될 수 없습니다." };
  }
  
  // 규칙 2: output-node는 source가 될 수 없음
  if (sourceType === NodeType.OUTPUT) {
    return { allowed: false, reason: "출력 노드는 연결의 시작점이 될 수 없습니다." };
  }
  
  // 규칙 3: ensemble-node가 아닌 노드는 여러 pre-node를 가질 수 없음
  if (targetType !== NodeType.ENSEMBLE && targetPreNodes.length >= 1) {
    return { allowed: false, reason: "앙상블 노드가 아닌 노드는 하나의 입력만 가질 수 있습니다." };
  }
  
  // 규칙 4: input-node가 아닌 노드는 여러 post-node를 가질 수 없음
  if (sourceType !== NodeType.INPUT && sourcePostNodes.length >= 1) {
    return { allowed: false, reason: "입력 노드가 아닌 노드는 하나의 출력만 가질 수 있습니다." };
  }
  
  // 규칙 5: generation-node는 input-node에서만 입력받을 수 있음
  if (targetType === NodeType.GENERATION && sourceType !== NodeType.INPUT) {
    return { allowed: false, reason: "생성 노드는 입력 노드에서만 연결받을 수 있습니다." };
  }
  
  // 규칙 6: 특정 노드 타입 간 연결 허용 규칙
  const allowedConnections: Record<NodeType, NodeType[]> = {
    [NodeType.INPUT]: [NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.OUTPUT],
    [NodeType.GENERATION]: [NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.OUTPUT],
    [NodeType.ENSEMBLE]: [NodeType.VALIDATION, NodeType.ENSEMBLE, NodeType.OUTPUT],
    [NodeType.VALIDATION]: [NodeType.VALIDATION, NodeType.ENSEMBLE, NodeType.OUTPUT],
    [NodeType.OUTPUT]: [] // output은 source가 될 수 없음
  };
  
  if (!allowedConnections[sourceType].includes(targetType)) {
    return { 
      allowed: false, 
      reason: `${sourceType}에서 ${targetType}로의 연결은 허용되지 않습니다.` 
    };
  }
  
  return { allowed: true };
}

export function validateNodeWorkflow(nodes: WorkflowNode[], edges: WorkflowEdge[]): ValidationResult {
  const errors: string[] = [];
  
  // 노드별 연결 정보 구축
  const preNodes = new Map<string, string[]>();
  const postNodes = new Map<string, string[]>();
  
  // 모든 노드 초기화
  nodes.forEach(node => {
    preNodes.set(node.id, []);
    postNodes.set(node.id, []);
  });
  
  // 엣지로부터 연결 정보 구축
  edges.forEach(edge => {
    const sourcePostList = postNodes.get(edge.source) || [];
    const targetPreList = preNodes.get(edge.target) || [];
    
    postNodes.set(edge.source, [...sourcePostList, edge.target]);
    preNodes.set(edge.target, [...targetPreList, edge.source]);
  });
  
  // 노드별 타입 카운트
  const nodeTypeCounts = {
    [NodeType.INPUT]: 0,
    [NodeType.GENERATION]: 0,
    [NodeType.ENSEMBLE]: 0,
    [NodeType.VALIDATION]: 0,
    [NodeType.OUTPUT]: 0
  };
  
  nodes.forEach(node => {
    nodeTypeCounts[node.data.nodeType]++;
  });
  
  // 규칙 1: input-node는 최소 1개 필요
  if (nodeTypeCounts[NodeType.INPUT] === 0) {
    errors.push('최소 1개의 input-node가 필요합니다.');
  }
  
  // 규칙 2: output-node는 최대 1개만 허용
  if (nodeTypeCounts[NodeType.OUTPUT] > 1) {
    errors.push('output-node는 워크플로우당 1개만 허용됩니다.');
  }
  
  // 각 노드별 연결 규칙 검증
  nodes.forEach(node => {
    const nodeId = node.id;
    const nodeType = node.data.nodeType;
    const preList = preNodes.get(nodeId) || [];
    const postList = postNodes.get(nodeId) || [];
    
    switch (nodeType) {
      case NodeType.INPUT:
        // input-node: pre-node 없어야 함, post-node는 여러 개 가능
        if (preList.length > 0) {
          errors.push(`input-node '${node.data.label}'는 pre-node를 가질 수 없습니다.`);
        }
        if (postList.length === 0) {
          errors.push(`input-node '${node.data.label}'는 최소 1개의 post-node가 필요합니다.`);
        }
        break;
        
      case NodeType.GENERATION:
        // generation-node: 정확히 1개의 pre-node, 1개 이상의 post-node
        if (preList.length !== 1) {
          errors.push(`generation-node '${node.data.label}'는 정확히 1개의 pre-node가 필요합니다.`);
        }
        if (postList.length === 0) {
          errors.push(`generation-node '${node.data.label}'는 최소 1개의 post-node가 필요합니다.`);
        }
        break;
        
      case NodeType.ENSEMBLE:
        // ensemble-node: 여러 pre-node 허용, 1개 이상의 post-node
        if (preList.length === 0) {
          errors.push(`ensemble-node '${node.data.label}'는 최소 1개의 pre-node가 필요합니다.`);
        }
        if (postList.length === 0) {
          errors.push(`ensemble-node '${node.data.label}'는 최소 1개의 post-node가 필요합니다.`);
        }
        break;
        
      case NodeType.VALIDATION:
        // validation-node: 1개의 pre-node, 1개 이상의 post-node (연쇄 가능)
        if (preList.length !== 1) {
          errors.push(`validation-node '${node.data.label}'는 정확히 1개의 pre-node가 필요합니다.`);
        }
        if (postList.length === 0) {
          errors.push(`validation-node '${node.data.label}'는 최소 1개의 post-node가 필요합니다.`);
        }
        break;
        
      case NodeType.OUTPUT:
        // output-node: 1개의 pre-node, post-node 없어야 함
        if (preList.length !== 1) {
          errors.push(`output-node '${node.data.label}'는 정확히 1개의 pre-node가 필요합니다.`);
        }
        if (postList.length > 0) {
          errors.push(`output-node '${node.data.label}'는 post-node를 가질 수 없습니다.`);
        }
        break;
    }
  });
  
  // 추가 규칙: ensemble-node가 아닌 노드는 여러 pre-node를 가질 수 없음
  nodes.forEach(node => {
    if (node.data.nodeType !== NodeType.ENSEMBLE && node.data.nodeType !== NodeType.INPUT) {
      const preList = preNodes.get(node.id) || [];
      if (preList.length > 1) {
        errors.push(`${node.data.nodeType} '${node.data.label}'는 여러 pre-node를 가질 수 없습니다. ensemble-node만 가능합니다.`);
      }
    }
  });
  
  // 추가 규칙: input-node가 아닌 노드는 여러 post-node를 주의깊게 검토
  // (현재는 허용하지만 워닝으로 표시 가능)
  
  return {
    isValid: errors.length === 0,
    errors
  };
}

export function formatValidationErrors(errors: string[]): string[] {
  return errors.map((error, index) => `${index + 1}. ${error}`);
}