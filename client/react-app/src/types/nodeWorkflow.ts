// ==================== 노드 기반 워크플로우 전용 타입 시스템 ====================
// project_reference.md에 기반한 5가지 노드 타입만 지원

export enum NodeType {
  INPUT = "input-node",
  GENERATION = "generation-node", 
  ENSEMBLE = "ensemble-node",
  VALIDATION = "validation-node",
  OUTPUT = "output-node"
}

export enum LLMProvider {
  OPENAI = "openai",
  GOOGLE = "google"
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
  llm_provider?: LLMProvider; // LLM 제공자
  prompt?: string;            // LLM 노드용 프롬프트
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
  use_rerank?: boolean;       // Rerank 사용 여부
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
  path: string;
  exists: boolean;
}

export interface KnowledgeBaseListResponse {
  knowledge_bases: KnowledgeBase[];
  total_count: number;
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