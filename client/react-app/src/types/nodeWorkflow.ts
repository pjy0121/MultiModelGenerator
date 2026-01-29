// ==================== Node-based workflow type system ====================
// Based on project_reference.md - Supports 6 node types

export enum NodeType {
  INPUT = "input-node",
  GENERATION = "generation-node",
  ENSEMBLE = "ensemble-node",
  VALIDATION = "validation-node",
  CONTEXT = "context-node",
  OUTPUT = "output-node"
}

export enum LLMProvider {
  OPENAI = "openai",
  GOOGLE = "google",
  INTERNAL = "internal",
  NONE = "none"  // No reranking
}

export enum SearchIntensity {
  EXACT = "exact",
  STANDARD = "standard",
  COMPREHENSIVE = "comprehensive"
}

// ==================== Node-based workflow core types ====================

export interface NodeBasedConfig {
  id: string;
  node_type: NodeType;
  content?: string;           // Text content for input-node, output-node
  model_type?: string;        // LLM model identifier
  llm_provider?: LLMProvider; // LLM Provider
  prompt?: string;            // Prompt for LLM nodes
  knowledge_base?: string;    // Knowledge base for context-node
  search_intensity?: SearchIntensity; // Search intensity for context-node
  rerank_provider?: LLMProvider | 'enabled'; // Rerank usage for context-node (NONE or enabled)
  additional_context?: string; // User-defined context for context-node
  position: { x: number; y: number };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
}

export interface NodeBasedWorkflowRequest {
  knowledge_base: string;
  search_intensity: SearchIntensity;
  nodes: NodeBasedConfig[];
  edges: WorkflowEdge[];
  node_prompts: { [key: string]: string };
  output_format: string;
}

export interface NodeBasedExecutionResult {
  node_id: string;
  success: boolean;
  description?: string;
  output?: string;
  error?: string;
}

// Stream data type
export interface StreamChunk {
  type: 'execution_started' | 'node_start' | 'node_streaming' | 'node_complete' | 'workflow_complete' | 'validation_error' | 'stop_requested' | 'error';
  execution_id?: string;  // Delivered in execution_started event
  node_id?: string;
  content?: string;
  results?: NodeBasedExecutionResult[];
  message?: string;
  errors?: string[];
  warnings?: string[];
}

// Workflow execution request type
export interface WorkflowExecutionRequest {
  workflow: {
    nodes: any[];
    edges: WorkflowEdge[];
  };
}

export interface NodeBasedWorkflowResponse {
  success: boolean;
  results: NodeBasedExecutionResult[];
  final_output?: string;
  total_execution_time: number;
  execution_order: string[];
  error?: string;
}

// ==================== React Flow node types ====================

export interface NodeData extends Record<string, unknown> {
  id: string;
  nodeType: NodeType;
  label: string;
  content?: string;           // For input-node, output-node
  model_type?: string;        // For LLM nodes
  llm_provider?: LLMProvider; // For LLM nodes
  prompt?: string;            // Prompt for LLM nodes
  output_format?: string;     // Output format for LLM nodes
  knowledge_base?: string;    // Knowledge base for context-node
  search_intensity?: SearchIntensity; // Search intensity for context-node
  rerank_provider?: LLMProvider | 'enabled'; // Rerank usage for context-node (NONE or enabled)
  additional_context?: string; // User-defined context for context-node
  isExecuting?: boolean;      // For execution state display
  isCompleted?: boolean;      // For completion state display
}

// Node interface for React Flow
export interface WorkflowNode {
  id: string;
  type: 'workflowNode';
  position: { x: number; y: number };
  data: NodeData;
  draggable?: boolean;
  selectable?: boolean;
  deletable?: boolean;
}

// ==================== Knowledge base related types ====================

export interface KnowledgeBase {
  name: string;
  chunk_count: number;
  created_at: string;
}

export interface KnowledgeBaseListResponse {
  knowledge_bases: KnowledgeBase[];
}

// ==================== Workflow validation related types ====================

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

// ==================== Model management types ====================

export interface AvailableModel {
  value: string;
  label: string;
  provider: string;
  model_type: string;
  disabled: boolean;
}

export interface AvailableModelsResponse {
  models: AvailableModel[];
}
