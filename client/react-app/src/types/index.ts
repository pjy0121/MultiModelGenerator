import { Node, Edge } from '@xyflow/react';
export enum ModelType {
  PERPLEXITY_SONAR_PRO = "sonar-pro",
  PERPLEXITY_SONAR_MEDIUM = "sonar-medium",
  OPENAI_GPT4 = "gpt-4",
  OPENAI_GPT35 = "gpt-3.5-turbo"
}
export enum LayerType {
  GENERATION = "generation",
  ENSEMBLE = "ensemble", 
  VALIDATION = "validation"
}
export interface WorkflowNodeData extends Record<string, unknown> {
  id: string;
  model_type: ModelType;
  layer: LayerType;
  label: string;
}
export interface PlaceholderNodeData extends Record<string, unknown> {
  layer: LayerType;
  onAddNode: (layer: LayerType) => void;
}
export type WorkflowNode = Node<WorkflowNodeData, 'customNode'>;
export type PlaceholderNode = Node<PlaceholderNodeData, 'placeholderNode'>;
export type AnyWorkflowNode = WorkflowNode | PlaceholderNode;
export type WorkflowEdge = Edge;
export interface KnowledgeBase {
  name: string;
  chunk_count: number;
  path: string;
  exists: boolean;
}
export interface NodeOutput {
  node_id: string;
  model_type: string;
  requirements: string;
  execution_time: number;
}
export interface WorkflowResult {
  success: boolean;
  knowledge_base: string;
  keyword: string;
  final_requirements: string;
  node_outputs: NodeOutput[];
  total_execution_time: number;
  generated_at: string;
}

// ==================== Layer별 프롬프트 시스템 타입들 ====================

export interface LayerPromptRequest {
  layer_type: LayerType;
  prompt: string;
  input_data: string;
  knowledge_base: string;
  nodes: NodeConfig[];
  context_chunks?: string[];
}

export interface LayerPromptResponse {
  success: boolean;
  layer_type: LayerType;
  knowledge_base: string;
  input_data: string;
  layer_prompt: string;
  outputs: NodeOutput[];
  combined_result: string;
  failed_nodes: string[];
  execution_time: number;
  context_chunks_used: string[];
  updated_input: string;
}

export interface ValidationLayerPromptResponse extends LayerPromptResponse {
  filtered_requirements: string[];
  validation_changes: ValidationChange[];
  final_validated_result: string;
  validation_steps: Array<{
    step: number;
    node_id: string;
    model_type: string;
    input: string;
    output: string;
    execution_time: number;
  }>;
}

// ==================== 기존 Layer별 워크플로우 타입들 ====================

export interface LayerExecutionRequest {
  knowledge_base: string;
  input_data: string;
  nodes: NodeConfig[];
  context_chunks?: string[];
}

export interface LayerExecutionResponse {
  success: boolean;
  layer_type: LayerType;
  knowledge_base: string;
  input_data: string;
  outputs: NodeOutput[];
  combined_result: string;
  failed_nodes: string[];
  execution_time: number;
  context_chunks_used: string[];
}

export interface ValidationLayerResponse extends LayerExecutionResponse {
  filtered_requirements: string[];
  validation_changes: ValidationChange[];
}

export interface NodeConfig {
  id: string;
  model_type: ModelType;
  prompt: string;
  layer: LayerType;
  position: { x: number; y: number };
}

// ==================== 기존 단계별 워크플로우 타입들 ====================

export interface SearchContextRequest {
  knowledge_base: string;
  query: string;
  top_k?: number;
}

export interface SearchContextResponse {
  success: boolean;
  knowledge_base: string;
  query: string;
  chunks: string[];
  chunk_count: number;
}

export interface SingleNodeRequest {
  knowledge_base: string;
  input_data: string;
  node_config: {
    id: string;
    model_type: ModelType;
    prompt: string;
    layer: LayerType;
    position: { x: number; y: number };
  };
  context_chunks?: string[];
}

export interface SingleNodeResponse {
  success: boolean;
  node_output: NodeOutput;
  context_chunks_used: string[];
  generated_at: string;
}

export interface EnsembleRequest {
  knowledge_base: string;
  generation_results: string[];
  ensemble_node: {
    id: string;
    model_type: ModelType;
    prompt: string;
    layer: LayerType;
    position: { x: number; y: number };
  };
  context_chunks?: string[];
}

export interface ValidationChange {
  requirement_id: string;
  original: string;
  modified: string;
  change_type: 'added' | 'modified' | 'removed';
  reason: string;
}

export interface ValidationRequest {
  knowledge_base: string;
  input_requirements: string;
  validation_node: {
    id: string;
    model_type: ModelType;
    prompt: string;
    layer: LayerType;
    position: { x: number; y: number };
  };
  context_chunks?: string[];
}

export interface ValidationResponse {
  success: boolean;
  node_output: NodeOutput;
  changes: ValidationChange[];
  context_chunks_used: string[];
  generated_at: string;
}

// 워크플로우 실행 상태 추적을 위한 타입들
export interface WorkflowExecutionStep {
  id: string;
  type: 'search' | 'generation' | 'ensemble' | 'validation';
  status: 'pending' | 'running' | 'completed' | 'error';
  node_id?: string;
  result?: any;
  error?: string;
  start_time?: Date;
  end_time?: Date;
}

export interface WorkflowExecution {
  id: string;
  knowledge_base: string;
  keyword: string;
  status: 'pending' | 'searching' | 'generating' | 'ensembling' | 'validating' | 'completed' | 'error';
  steps: WorkflowExecutionStep[];
  context_chunks?: string[];
  generation_result?: LayerExecutionResponse;
  ensemble_result?: LayerExecutionResponse;
  validation_results?: ValidationLayerResponse[];
  final_result?: string;
  filtered_requirements?: string[];
  created_at: Date;
  completed_at?: Date;
  error?: string;
}