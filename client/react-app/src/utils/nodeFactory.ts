import { NodeType, LLMProvider, SearchIntensity, WorkflowNode, NodeData } from '../types';
import { DEFAULT_PROMPTS, OUTPUT_FORMAT_TEMPLATES } from '../config/defaultPrompts';
import { NODE_CONFIG } from '../config/constants';

/**
 * 워크플로우 노드 생성 헬퍼 함수
 */
export const createWorkflowNode = (nodeType: NodeType, position: { x: number; y: number }): WorkflowNode => {
  const id = `${nodeType}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  const nodeData: NodeData = {
    id,
    nodeType,
    label: NODE_CONFIG.LABELS[nodeType] || "노드",
  };
  
  // input-node와 output-node는 content 필드 추가
  if (nodeType === NodeType.INPUT || nodeType === NodeType.OUTPUT) {
    nodeData.content = '';
  }
  
  // LLM 노드들은 모델 및 검색 설정 필드 추가
  if ([NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(nodeType)) {
    nodeData.model_type = '';
    nodeData.llm_provider = LLMProvider.GOOGLE;
    nodeData.knowledge_base = ''; // 기본값: 없음
    
    // 기본 프롬프트 템플릿 적용
    nodeData.prompt = DEFAULT_PROMPTS[nodeType as keyof typeof DEFAULT_PROMPTS] || '';
    
    // 기본 출력 형식 템플릿 적용
    nodeData.output_format = OUTPUT_FORMAT_TEMPLATES[nodeType as keyof typeof OUTPUT_FORMAT_TEMPLATES] || '';
    
    // 노드 타입에 따른 기본 검색 모드 설정
    if (nodeType === NodeType.VALIDATION) {
      nodeData.search_intensity = SearchIntensity.STANDARD; // validation-node: 표준 검색
    } else {
      nodeData.search_intensity = SearchIntensity.STANDARD; // generation, ensemble: 표준 검색
    }
  }
  
  return {
    id,
    type: 'workflowNode',
    position,
    data: nodeData,
    draggable: true,
    selectable: true,
    deletable: nodeType !== NodeType.OUTPUT // output-node는 삭제 불가
  };
};

/**
 * 초기 노드들 생성 함수
 */
export const createInitialNodes = (): WorkflowNode[] => {
  return [
    createWorkflowNode(NodeType.INPUT, { x: 400, y: 50 }),    // 상단 중앙 (더 위로)
    createWorkflowNode(NodeType.OUTPUT, { x: 400, y: 850 })   // 하단 중앙
  ];
};