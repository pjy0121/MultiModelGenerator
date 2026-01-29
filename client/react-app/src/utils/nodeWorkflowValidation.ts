import { WorkflowNode, WorkflowEdge, NodeType, ValidationResult } from '../types';

/**
 * Node workflow validation based on project_reference.md
 *
 * Connection rules:
 * 1. input-node: no pre-node, multiple post-nodes allowed
 * 2. generation-node: input-node → generation-node
 * 3. ensemble-node: multiple pre-nodes allowed → single output
 * 4. validation-node: sequential validation/improvement
 * 5. output-node: no post-node, single instance
 * 6. All nodes require pre/post connections (input excludes pre, output excludes post)
 */

// Check if connection is allowed - for real-time connection validation
export function isConnectionAllowed(
  sourceNode: WorkflowNode,
  targetNode: WorkflowNode,
  _nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): { allowed: boolean; reason?: string } {
  const sourceType = sourceNode.data.nodeType;
  const targetType = targetNode.data.nodeType;

  // Prohibit self-connection
  if (sourceNode.id === targetNode.id) {
    return { allowed: false, reason: "Cannot connect to itself." };
  }

  // Prohibit if already connected
  const existingConnection = edges.find(edge =>
    edge.source === sourceNode.id && edge.target === targetNode.id
  );
  if (existingConnection) {
    return { allowed: false, reason: "Already connected." };
  }

  // Calculate current target node's pre-node count
  const targetPreNodes = edges.filter(edge => edge.target === targetNode.id);

  // Calculate current source node's post-node count
  const sourcePostNodes = edges.filter(edge => edge.source === sourceNode.id);

  // Rule 1: input-node cannot be a target
  if (targetType === NodeType.INPUT) {
    return { allowed: false, reason: "Input node cannot be a connection target." };
  }

  // Rule 2: output-node cannot be a source
  if (sourceType === NodeType.OUTPUT) {
    return { allowed: false, reason: "Output node cannot be a connection source." };
  }

  // Rule 3: Check pre-node count limits
  if (targetType !== NodeType.ENSEMBLE && targetType !== NodeType.OUTPUT && targetPreNodes.length >= 1) {
    // Analyze current pre-nodes
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

    // context-node can have multiple connections (no limit)

    // Node type specific limits
    if (targetType === NodeType.GENERATION || targetType === NodeType.VALIDATION) {
      // generation-node: max 1 input-node + multiple context-nodes allowed
      // validation-node: 1 other node + multiple context-nodes allowed

      // Cannot add more connections if there's already a non-context pre-node
      if (sourceType !== NodeType.CONTEXT && (inputPreNodes.length + otherPreNodes.length) >= 1) {
        return { allowed: false, reason: `${targetType} can only have maximum 1 pre-node excluding context-node.` };
      }

      // generation-node only allows input-node and context-node
      if (targetType === NodeType.GENERATION && sourceType !== NodeType.INPUT && sourceType !== NodeType.CONTEXT) {
        return { allowed: false, reason: "Generation node can only receive connections from input node and context node." };
      }
    } else if (targetType !== NodeType.ENSEMBLE && targetType !== NodeType.OUTPUT) {
      // Other nodes excluding ensemble-node and output-node: only 1 general pre-node excluding context-node
      if (sourceType !== NodeType.CONTEXT && (inputPreNodes.length + otherPreNodes.length) >= 1) {
        return { allowed: false, reason: "Can only have maximum 1 pre-node excluding context-node." };
      }
    }
  }

  // Rule 4: Nodes other than input-node and context-node cannot have multiple post-nodes
  if (sourceType !== NodeType.INPUT && sourceType !== NodeType.CONTEXT && sourcePostNodes.length >= 1) {
    return { allowed: false, reason: "Nodes other than input node and context node can only have one output." };
  }

  // Rule 5: generation-node can only receive input from input-node and context-node
  if (targetType === NodeType.GENERATION && sourceType !== NodeType.INPUT && sourceType !== NodeType.CONTEXT) {
    return { allowed: false, reason: "Generation node can only receive connections from input node and context node." };
  }

  // Rule 6: Connection allowance rules between specific node types
  const allowedConnections: Record<NodeType, NodeType[]> = {
    [NodeType.INPUT]: [NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.CONTEXT, NodeType.OUTPUT],
    [NodeType.GENERATION]: [NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.OUTPUT],
    [NodeType.ENSEMBLE]: [NodeType.VALIDATION, NodeType.ENSEMBLE, NodeType.OUTPUT],
    [NodeType.VALIDATION]: [NodeType.VALIDATION, NodeType.ENSEMBLE, NodeType.OUTPUT],
    [NodeType.CONTEXT]: [NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION, NodeType.CONTEXT, NodeType.OUTPUT], // context can connect to all nodes except input-node
    [NodeType.OUTPUT]: [] // output cannot be a source
  };

  if (!allowedConnections[sourceType].includes(targetType)) {
    return {
      allowed: false,
      reason: `Connection from ${sourceType} to ${targetType} is not allowed.`
    };
  }

  return { allowed: true };
}

export function validateNodeWorkflow(nodes: WorkflowNode[], edges: WorkflowEdge[]): ValidationResult {
  const errors: string[] = [];

  // Build connection info per node
  const preNodes = new Map<string, string[]>();
  const postNodes = new Map<string, string[]>();

  // Initialize all nodes
  nodes.forEach(node => {
    preNodes.set(node.id, []);
    postNodes.set(node.id, []);
  });

  // Build connection info from edges
  edges.forEach(edge => {
    const sourcePostList = postNodes.get(edge.source) || [];
    const targetPreList = preNodes.get(edge.target) || [];

    postNodes.set(edge.source, [...sourcePostList, edge.target]);
    preNodes.set(edge.target, [...targetPreList, edge.source]);
  });

  // Count node types
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

  // Rule 1: At least 1 input-node required
  if (nodeTypeCounts[NodeType.INPUT] === 0) {
    errors.push('At least 1 input-node is required.');
  }

  // Rule 2: Maximum 1 output-node allowed
  if (nodeTypeCounts[NodeType.OUTPUT] > 1) {
    errors.push('Only 1 output-node is allowed per workflow.');
  }

  // Validate connection rules per node
  nodes.forEach(node => {
    const nodeId = node.id;
    const nodeType = node.data.nodeType;
    const preList = preNodes.get(nodeId) || [];
    const postList = postNodes.get(nodeId) || [];

    switch (nodeType) {
      case NodeType.INPUT:
        // input-node: no pre-node allowed, multiple post-nodes allowed
        if (preList.length > 0) {
          errors.push(`input-node '${node.data.label}' cannot have pre-nodes.`);
        }
        if (postList.length === 0) {
          errors.push(`input-node '${node.data.label}' requires at least 1 post-node.`);
        }
        break;

      case NodeType.GENERATION:
        // generation-node: max 1 input-node + max 1 context-node, 1+ post-nodes
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
          errors.push(`generation-node '${node.data.label}' requires at least 1 pre-node.`);
        }
        // context-node can have multiple (no limit)
        if (genInputPreNodes.length > 1) {
          errors.push(`generation-node '${node.data.label}' can have maximum 1 input-node.`);
        }
        if (genOtherPreNodes.length > 0) {
          errors.push(`generation-node '${node.data.label}' only allows input-node and context-node as pre-nodes.`);
        }
        if (postList.length === 0) {
          errors.push(`generation-node '${node.data.label}' requires at least 1 post-node.`);
        }
        break;

      case NodeType.ENSEMBLE:
        // ensemble-node: multiple pre-nodes allowed, 1+ post-nodes
        if (preList.length === 0) {
          errors.push(`ensemble-node '${node.data.label}' requires at least 1 pre-node.`);
        }
        if (postList.length === 0) {
          errors.push(`ensemble-node '${node.data.label}' requires at least 1 post-node.`);
        }
        break;

      case NodeType.VALIDATION:
        // validation-node: can receive input from input-node, generation-node, ensemble-node, validation-node, context-node
        // max 1 context-node, max 1 for other nodes (excluding context-node)
        const valContextPreNodes = preList.filter(preNodeId => {
          const preNode = nodes.find(n => n.id === preNodeId);
          return preNode?.data.nodeType === NodeType.CONTEXT;
        });
        const valOtherPreNodes = preList.filter(preNodeId => {
          const preNode = nodes.find(n => n.id === preNodeId);
          const nodeType = preNode?.data.nodeType;
          return nodeType !== NodeType.CONTEXT &&
                 nodeType !== NodeType.OUTPUT; // only exclude output-node
        });

        if (preList.length === 0) {
          errors.push(`validation-node '${node.data.label}' requires at least 1 pre-node.`);
        }
        // context-node can have multiple (no limit)
        if (valOtherPreNodes.length > 1) {
          errors.push(`validation-node '${node.data.label}' can have maximum 1 pre-node excluding context-node.`);
        }
        // Only prohibit connection from output-node
        const valOutputPreNodes = preList.filter(preNodeId => {
          const preNode = nodes.find(n => n.id === preNodeId);
          return preNode?.data.nodeType === NodeType.OUTPUT;
        });
        if (valOutputPreNodes.length > 0) {
          errors.push(`validation-node '${node.data.label}' cannot receive input from output-node.`);
        }
        if (postList.length === 0) {
          errors.push(`validation-node '${node.data.label}' requires at least 1 post-node.`);
        }
        break;

      case NodeType.OUTPUT:
        // output-node: multiple pre-nodes allowed (behaves like ensemble), no post-node allowed
        if (preList.length === 0) {
          errors.push(`output-node '${node.data.label}' requires at least 1 pre-node.`);
        }
        if (postList.length > 0) {
          errors.push(`output-node '${node.data.label}' cannot have post-nodes.`);
        }
        break;

      case NodeType.CONTEXT:
        // context-node: pre-node not required (can independently search knowledge base), post-node is required
        if (postList.length === 0) {
          errors.push(`context-node '${node.data.label}' requires at least 1 post-node.`);
        }
        break;
    }
  });

  // Additional rule: pre-node count limits
  // - output-node, ensemble-node: no limit
  // - generation-node, validation-node: max 1 input-node + max 1 context-node
  // - other nodes: 1 general pre-node + max 1 context-node
  nodes.forEach(node => {
    const preList = preNodes.get(node.id) || [];

    if (node.data.nodeType !== NodeType.ENSEMBLE && node.data.nodeType !== NodeType.INPUT && node.data.nodeType !== NodeType.OUTPUT) {
      // Separate context-node from other pre-nodes
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

      // context-node can have multiple (no limit)

      // Additional limits per node type
      if (node.data.nodeType === NodeType.GENERATION) {
        // generation-node: max 1 input-node + max 1 context-node only
        if (inputPreNodes.length > 1) {
          errors.push(`${node.data.nodeType} '${node.data.label}' can have maximum 1 input-node as pre-node.`);
        }
        if (otherPreNodes.length > 0) {
          errors.push(`${node.data.nodeType} '${node.data.label}' only allows input-node and context-node as pre-nodes.`);
        }
      } else if (node.data.nodeType === NodeType.VALIDATION) {
        // validation-node: can receive input from other LLM nodes, max 1 pre-node excluding context-node
        const totalNonContext = inputPreNodes.length + otherPreNodes.length;
        if (totalNonContext > 1) {
          errors.push(`${node.data.nodeType} '${node.data.label}' can have maximum 1 pre-node excluding context-node.`);
        }
      } else {
        // Other nodes: only 1 general pre-node excluding context-node
        const totalNonContext = inputPreNodes.length + otherPreNodes.length;
        if (totalNonContext > 1) {
          errors.push(`${node.data.nodeType} '${node.data.label}' can have maximum 1 pre-node excluding context-node.`);
        }
      }
    }
  });

  // Additional rule: Nodes other than input-node should be carefully reviewed for multiple post-nodes
  // (Currently allowed but can show as warning)

  return {
    isValid: errors.length === 0,
    errors
  };
}

export function formatValidationErrors(errors: string[]): string[] {
  return errors.map((error, index) => `${index + 1}. ${error}`);
}
