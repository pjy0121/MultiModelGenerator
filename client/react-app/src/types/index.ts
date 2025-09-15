import { Node, Edge } from '@xyflow/react';

export enum LayerType {
  GENERATION = "generation",
  ENSEMBLE = "ensemble", 
  VALIDATION = "validation"
}

export enum LLMProvider {
  OPENAI = "openai",
  GOOGLE = "google"
}

export enum SearchIntensity {
  LOW = "low",      // 약: 기본 검색량
  MEDIUM = "medium", // 중: 적당한 검색량  
  HIGH = "high"     // 강: 최대 검색량
}

export interface WorkflowNodeData extends Record<string, unknown> {
  id: string;
  model?: string;
  provider?: string; // LLM Provider 정보 추가
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

// 새로운 모델 관리 시스템 타입들
export interface AvailableModel {
  id: string;
  name: string;
  provider: LLMProvider;
  model_type: string;
  available: boolean;
}

export interface AvailableModelsResponse {
  models: AvailableModel[];
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
  layer_input: string;
  knowledge_base: string;
  top_k: number;  // 더 높은 기본값으로 사용 (50)
  nodes: NodeConfig[];
  context_chunks?: string[];
}

export interface LayerPromptResponse {
  success: boolean;
  layer_type: LayerType;
  knowledge_base: string;
  layer_input: string;
  layer_prompt: string;
  outputs: NodeOutput[];
  combined_result: string;  // 전체 상세 결과 (포괄적인 결과)
  final_result: string;     // 최종 결과만 (핵심 결과)
  failed_nodes: string[];
  execution_time: number;
  context_chunks_used: string[];
  updated_input: string;
}

export interface ValidationLayerPromptResponse extends LayerPromptResponse {
  filtered_requirements: string[];
  validation_changes: string[];  // ValidationChange에서 string으로 간소화
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
  layer_input: string;
  nodes: NodeConfig[];
  context_chunks?: string[];
}

export interface LayerExecutionResponse {
  success: boolean;
  layer_type: LayerType;
  knowledge_base: string;
  layer_input: string;
  layer_prompt: string;
  node_outputs: { [key: string]: string }; // 새로운 구조: { "node1": "general_output", "node2": "general_output", "forward_data": "결합된 forward_data" }
  execution_time: number;
  timestamp: string;
}

export interface ValidationLayerResponse extends LayerExecutionResponse {
  filtered_requirements: string[];
  validation_changes: ValidationChange[];
}

export interface NodeConfig {
  id: string;
  model?: string;
  provider?: string;
  prompt: string;
  layer: LayerType;
  position: { x: number; y: number };
}

// ==================== 기존 단계별 워크플로우 타입들 ====================

export interface SearchContextRequest {
  knowledge_base: string;
  query: string;
  top_k?: number;  // 기본값 50으로 처리됨
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
  layer_input: string;
  node_config: {
    id: string;
    model_type: string;
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
    model_type: string;
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
    model_type: string;
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