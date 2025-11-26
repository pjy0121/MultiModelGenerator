// ==================== 노드 기반 워크플로우 전용 타입 시스템 ====================
// project_reference.md에 기반한 6가지 노드 타입 지원

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
  NONE = "none"  // 새로 추가: 재정렬 사용 안 함
}

export enum SearchIntensity {
  VERY_LOW = "very_low",
  LOW = "low",      
  MEDIUM = "medium", 
  HIGH = "high",
  VERY_HIGH = "very_high"
}

// ==================== 노드 기반 워크플로우 핵심 타입들 ====================

export interface NodeBasedConfig {
  id: string;
  node_type: NodeType;
  content?: string;           // input-node, output-node용 텍스트 내용
  model_type?: string;        // LLM 모델 식별자
  llm_provider?: LLMProvider; // LLM Provider
  prompt?: string;            // LLM 노드용 프롬프트
  knowledge_base?: string;    // context-node용 지식베이스
  search_intensity?: SearchIntensity; // context-node용 검색 강도
  rerank_provider?: LLMProvider; // context-node용 rerank LLM Provider
  rerank_model?: string;      // context-node용 rerank 모델
  additional_context?: string; // context-node용 사용자 정의 컨텍스트
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

// 스트림 데이터 타입
export interface StreamChunk {
  type: 'execution_started' | 'node_start' | 'node_streaming' | 'node_complete' | 'workflow_complete' | 'validation_error' | 'stop_requested' | 'error';
  execution_id?: string;  // execution_started 이벤트에서 전달
  node_id?: string;
  content?: string;
  results?: NodeBasedExecutionResult[];
  message?: string;
  errors?: string[];
  warnings?: string[];
}

// 워크플로우 실행 요청 타입
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

// ==================== React Flow 노드 타입들 ====================

export interface NodeData extends Record<string, unknown> {
  id: string;
  nodeType: NodeType;
  label: string;
  content?: string;           // input-node, output-node용
  model_type?: string;        // LLM 노드용
  llm_provider?: LLMProvider; // LLM 노드용
  prompt?: string;            // LLM 노드용 프롬프트
  output_format?: string;     // LLM 노드용 출력 형식
  knowledge_base?: string;    // context-node용 지식베이스
  search_intensity?: SearchIntensity; // context-node용 검색 강도
  rerank_provider?: LLMProvider; // context-node용 rerank LLM Provider
  rerank_model?: string;      // context-node용 rerank 모델
  additional_context?: string; // context-node용 사용자 정의 컨텍스트
  isExecuting?: boolean;      // 실행 상태 표시용
  isCompleted?: boolean;      // 완료 상태 표시용
}

// React Flow용 노드 인터페이스
export interface WorkflowNode {
  id: string;
  type: 'workflowNode';
  position: { x: number; y: number };
  data: NodeData;
  draggable?: boolean;
  selectable?: boolean;
  deletable?: boolean;
}

// ==================== 지식 베이스 관련 타입들 ====================

export interface KnowledgeBase {
  name: string;
  chunk_count: number;
  created_at: string;
}

export interface KnowledgeBaseListResponse {
  knowledge_bases: KnowledgeBase[];
}

// ==================== 워크플로우 검증 관련 타입들 ====================

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

// ==================== 모델 관리 타입들 ====================

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