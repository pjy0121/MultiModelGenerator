import { Node, Edge } from '@xyflow/react';
export enum ModelType {
  PERPLEXITY_SONAR_PRO = "perplexity-sonar-pro",
  PERPLEXITY_SONAR_MEDIUM = "perplexity-sonar-medium",
  OPENAI_GPT4 = "openai-gpt-4",
  OPENAI_GPT35 = "openai-gpt-3.5-turbo"
}
export enum LayerType {
  GENERATION = "generation",
  ENSEMBLE = "ensemble", 
  VALIDATION = "validation"
}
export interface WorkflowNodeData extends Record<string, unknown> {
  id: string;
  model_type: ModelType;
  prompt: string;
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