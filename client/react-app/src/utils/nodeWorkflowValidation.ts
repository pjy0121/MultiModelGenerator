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
  
  // 규칙 3: pre-node 개수 제한 검사
  if (targetType !== NodeType.ENSEMBLE && targetType !== NodeType.OUTPUT && targetPreNodes.length >= 1) {
    // 현재 pre-node들 분석
    const contextPreNodes = targetPreNodes.filter(edge => {
      const preNode = _nodes.find(n => n.id === edge.source);
      return preNode?.data.nodeType === NodeType.CONTEXT;
    });
    
    const inputPreNodes = targetPreNodes.filter(edge => {
      const preNode = _nodes.find(n => n.id === edge.source);
      return preNode?.data.nodeType === NodeType.INPUT;
    });
    
    const otherPreNodes = targetPreNodes.filter(edge => {
      const preNode = _nodes.find(n => n.id === edge.source);
      return preNode?.data.nodeType !== NodeType.CONTEXT && preNode?.data.nodeType !== NodeType.INPUT;
    });
    
    // context-node 최대 1개 제한
    if (sourceType === NodeType.CONTEXT && contextPreNodes.length >= 1) {
      return { allowed: false, reason: "context-node는 최대 1개만 연결할 수 있습니다." };
    }
    
    // 노드 타입별 제한
    if (targetType === NodeType.GENERATION || targetType === NodeType.VALIDATION) {
      // generation-node, validation-node: input-node 최대 1개 + context-node 최대 1개
      if (sourceType === NodeType.INPUT && inputPreNodes.length >= 1) {
        return { allowed: false, reason: `${targetType}는 input-node를 최대 1개만 연결받을 수 있습니다.` };
      }
      if (sourceType !== NodeType.INPUT && sourceType !== NodeType.CONTEXT) {
        return { allowed: false, reason: `${targetType}는 input-node와 context-node에서만 연결받을 수 있습니다.` };
      }
    } else {
      // 다른 노드들: context-node 제외하고 일반 pre-node 1개만
      if (sourceType !== NodeType.CONTEXT && (inputPreNodes.length + otherPreNodes.length) >= 1) {
        return { allowed: false, reason: "context-node를 제외한 pre-node는 최대 1개만 연결할 수 있습니다." };
      }
    }
  }
  
  // 규칙 4: input-node와 context-node가 아닌 노드는 여러 post-node를 가질 수 없음
  if (sourceType !== NodeType.INPUT && sourceType !== NodeType.CONTEXT && sourcePostNodes.length >= 1) {
    return { allowed: false, reason: "입력 노드와 컨텍스트 노드가 아닌 노드는 하나의 출력만 가질 수 있습니다." };
  }
  
  // 규칙 5: generation-node는 input-node와 context-node에서만 입력받을 수 있음
  if (targetType === NodeType.GENERATION && sourceType !== NodeType.INPUT && sourceType !== NodeType.CONTEXT) {
    return { allowed: false, reason: "생성 노드는 입력 노드와 컨텍스트 노드에서만 연결받을 수 있습니다." };
  }
  
  // 규칙 6: 특정 노드 타입 간 연결 허용 규칙
  const allowedConnections: Record<NodeType, NodeType[]> = {
    [NodeType.INPUT]: [NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.CONTEXT, NodeType.OUTPUT],
    [NodeType.GENERATION]: [NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.OUTPUT],
    [NodeType.ENSEMBLE]: [NodeType.VALIDATION, NodeType.ENSEMBLE, NodeType.OUTPUT],
    [NodeType.VALIDATION]: [NodeType.VALIDATION, NodeType.ENSEMBLE, NodeType.OUTPUT],
    [NodeType.CONTEXT]: [NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.CONTEXT, NodeType.OUTPUT], // context는 input-node 제외한 모든 노드에 연결 가능
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
    [NodeType.CONTEXT]: 0,
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
        // generation-node: input-node 최대 1개 + context-node 최대 1개, 1개 이상의 post-node
        const genContextPreNodes = preList.filter(preNodeId => {
          const preNode = nodes.find(n => n.id === preNodeId);
          return preNode?.data.nodeType === NodeType.CONTEXT;
        });
        const genInputPreNodes = preList.filter(preNodeId => {
          const preNode = nodes.find(n => n.id === preNodeId);
          return preNode?.data.nodeType === NodeType.INPUT;
        });
        const genOtherPreNodes = preList.filter(preNodeId => {
          const preNode = nodes.find(n => n.id === preNodeId);
          return preNode?.data.nodeType !== NodeType.CONTEXT && preNode?.data.nodeType !== NodeType.INPUT;
        });
        
        if (preList.length === 0) {
          errors.push(`generation-node '${node.data.label}'는 최소 1개의 pre-node가 필요합니다.`);
        }
        if (genContextPreNodes.length > 1) {
          errors.push(`generation-node '${node.data.label}'는 context-node를 최대 1개만 가질 수 있습니다.`);
        }
        if (genInputPreNodes.length > 1) {
          errors.push(`generation-node '${node.data.label}'는 input-node를 최대 1개만 가질 수 있습니다.`);
        }
        if (genOtherPreNodes.length > 0) {
          errors.push(`generation-node '${node.data.label}'는 input-node와 context-node 외의 pre-node는 허용되지 않습니다.`);
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
        // validation-node: input-node, generation-node, ensemble-node, validation-node, context-node로부터 입력 가능
        // context-node는 최대 1개, 다른 노드들은 최대 1개 (context-node 제외)
        const valContextPreNodes = preList.filter(preNodeId => {
          const preNode = nodes.find(n => n.id === preNodeId);
          return preNode?.data.nodeType === NodeType.CONTEXT;
        });
        const valOtherPreNodes = preList.filter(preNodeId => {
          const preNode = nodes.find(n => n.id === preNodeId);
          const nodeType = preNode?.data.nodeType;
          return nodeType !== NodeType.CONTEXT && 
                 nodeType !== NodeType.OUTPUT; // output-node만 제외
        });
        
        if (preList.length === 0) {
          errors.push(`validation-node '${node.data.label}'는 최소 1개의 pre-node가 필요합니다.`);
        }
        if (valContextPreNodes.length > 1) {
          errors.push(`validation-node '${node.data.label}'는 context-node를 최대 1개만 가질 수 있습니다.`);
        }
        if (valOtherPreNodes.length > 1) {
          errors.push(`validation-node '${node.data.label}'는 context-node를 제외한 pre-node를 최대 1개만 가질 수 있습니다.`);
        }
        // output-node로부터의 연결만 금지
        const valOutputPreNodes = preList.filter(preNodeId => {
          const preNode = nodes.find(n => n.id === preNodeId);
          return preNode?.data.nodeType === NodeType.OUTPUT;
        });
        if (valOutputPreNodes.length > 0) {
          errors.push(`validation-node '${node.data.label}'는 output-node로부터 입력을 받을 수 없습니다.`);
        }
        if (postList.length === 0) {
          errors.push(`validation-node '${node.data.label}'는 최소 1개의 post-node가 필요합니다.`);
        }
        break;
        
      case NodeType.OUTPUT:
        // output-node: 여러 pre-node 허용 (ensemble처럼 동작), post-node 없어야 함
        if (preList.length === 0) {
          errors.push(`output-node '${node.data.label}'는 최소 1개의 pre-node가 필요합니다.`);
        }
        if (postList.length > 0) {
          errors.push(`output-node '${node.data.label}'는 post-node를 가질 수 없습니다.`);
        }
        break;
        
      case NodeType.CONTEXT:
        // context-node: pre-node 없어도 됨 (독립적으로 지식 베이스 검색), post-node는 필수
        if (postList.length === 0) {
          errors.push(`context-node '${node.data.label}'는 최소 1개의 post-node가 필요합니다.`);
        }
        break;
    }
  });
  
  // 추가 규칙: pre-node 개수 제한
  // - output-node, ensemble-node: 제한 없음
  // - generation-node, validation-node: input-node 최대 1개 + context-node 최대 1개
  // - 다른 노드들: 일반 pre-node 1개 + context-node 최대 1개
  nodes.forEach(node => {
    const preList = preNodes.get(node.id) || [];
    
    if (node.data.nodeType !== NodeType.ENSEMBLE && node.data.nodeType !== NodeType.INPUT && node.data.nodeType !== NodeType.OUTPUT) {
      // context-node와 다른 pre-node들을 분리
      const contextPreNodes: string[] = [];
      const inputPreNodes: string[] = [];
      const otherPreNodes: string[] = [];
      
      preList.forEach(preNodeId => {
        const preNode = nodes.find(n => n.id === preNodeId);
        if (preNode) {
          if (preNode.data.nodeType === NodeType.CONTEXT) {
            contextPreNodes.push(preNodeId);
          } else if (preNode.data.nodeType === NodeType.INPUT) {
            inputPreNodes.push(preNodeId);
          } else {
            otherPreNodes.push(preNodeId);
          }
        }
      });
      
      // context-node는 최대 1개만 허용
      if (contextPreNodes.length > 1) {
        errors.push(`${node.data.nodeType} '${node.data.label}'는 context-node를 최대 1개만 pre-node로 가질 수 있습니다.`);
      }
      
      // 노드 타입별 추가 제한
      if (node.data.nodeType === NodeType.GENERATION) {
        // generation-node: input-node 최대 1개 + context-node 최대 1개만
        if (inputPreNodes.length > 1) {
          errors.push(`${node.data.nodeType} '${node.data.label}'는 input-node를 최대 1개만 pre-node로 가질 수 있습니다.`);
        }
        if (otherPreNodes.length > 0) {
          errors.push(`${node.data.nodeType} '${node.data.label}'는 input-node와 context-node 외의 pre-node는 허용되지 않습니다.`);
        }
      } else if (node.data.nodeType === NodeType.VALIDATION) {
        // validation-node: 다른 LLM 노드들로부터 입력 가능, context-node 제외한 pre-node 최대 1개
        const totalNonContext = inputPreNodes.length + otherPreNodes.length;
        if (totalNonContext > 1) {
          errors.push(`${node.data.nodeType} '${node.data.label}'는 context-node를 제외한 pre-node를 최대 1개만 가질 수 있습니다.`);
        }
      } else {
        // 다른 노드들: context-node 제외하고 일반 pre-node 1개만
        const totalNonContext = inputPreNodes.length + otherPreNodes.length;
        if (totalNonContext > 1) {
          errors.push(`${node.data.nodeType} '${node.data.label}'는 context-node를 제외한 pre-node를 최대 1개만 가질 수 있습니다.`);
        }
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