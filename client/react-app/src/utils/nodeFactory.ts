import { NodeType, LLMProvider, SearchIntensity, WorkflowNode, NodeData } from '../types';
import { DEFAULT_PROMPTS, OUTPUT_FORMAT_TEMPLATES } from '../config/defaultPrompts';
import { NODE_CONFIG } from '../config/constants';

/**
 * Workflow node creation helper function
 */
export const createWorkflowNode = (nodeType: NodeType, position: { x: number; y: number }): WorkflowNode => {
  const id = `${nodeType}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  const nodeData: NodeData = {
    id,
    nodeType,
    label: NODE_CONFIG.LABELS[nodeType] || "Node",
  };

  // Add content field for input-node and output-node
  if (nodeType === NodeType.INPUT || nodeType === NodeType.OUTPUT) {
    nodeData.content = '';
  }

  // Add model and search settings for LLM nodes
  if ([NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(nodeType)) {
    nodeData.model_type = '';
    nodeData.llm_provider = LLMProvider.GOOGLE;
    nodeData.knowledge_base = ''; // Default: none

    // Apply default prompt template
    nodeData.prompt = DEFAULT_PROMPTS[nodeType as keyof typeof DEFAULT_PROMPTS] || '';

    // Apply default output format template
    nodeData.output_format = OUTPUT_FORMAT_TEMPLATES[nodeType as keyof typeof OUTPUT_FORMAT_TEMPLATES] || '';

    // Set default search mode per node type
    if (nodeType === NodeType.VALIDATION) {
      nodeData.search_intensity = SearchIntensity.STANDARD; // validation-node: standard search
    } else {
      nodeData.search_intensity = SearchIntensity.STANDARD; // generation, ensemble: standard search
    }
  }

  return {
    id,
    type: 'workflowNode',
    position,
    data: nodeData,
    draggable: true,
    selectable: true,
    deletable: nodeType !== NodeType.OUTPUT // output-node cannot be deleted
  };
};

/**
 * Create initial nodes function
 */
export const createInitialNodes = (): WorkflowNode[] => {
  return [
    createWorkflowNode(NodeType.INPUT, { x: 400, y: 50 }),    // Top center (higher)
    createWorkflowNode(NodeType.OUTPUT, { x: 400, y: 850 })   // Bottom center
  ];
};
