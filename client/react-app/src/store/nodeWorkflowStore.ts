import { create } from 'zustand';
import { message } from 'antd';
import {
  NodeType,
  LLMProvider,
  SearchIntensity,
  WorkflowNode,
  WorkflowEdge,
  NodeData,
  NodeBasedWorkflowResponse,
  ValidationResult,
  KnowledgeBase,
  AvailableModel
} from '../types';
import { nodeBasedWorkflowAPI, workflowAPI } from '../services/api';
import { validateNodeWorkflow, formatValidationErrors } from '../utils/nodeWorkflowValidation';

// ==================== 노드 기반 워크플로우 전용 스토어 ====================
// project_reference.md 기준 - 5가지 노드 타입만 지원

interface NodeWorkflowState {
  // 워크플로우 구성
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  
  // 실행 설정
  selectedKnowledgeBase: string;
  searchIntensity: SearchIntensity;
  
  // 실행 상태
  isExecuting: boolean;
  executionResult: NodeBasedWorkflowResponse | null;
  
  // 검증 상태
  validationResult: ValidationResult | null;
  validationErrors: string[];
  
  // 모델 관리
  availableModels: AvailableModel[];
  knowledgeBases: KnowledgeBase[];
  
  // 노드 실행 상태 업데이트
  setNodeExecutionStatus: (nodeId: string, isExecuting: boolean, isCompleted?: boolean) => void;
  
  // 액션들
  addNode: (nodeType: NodeType, position: { x: number; y: number }) => void;
  updateNode: (nodeId: string, updates: Partial<NodeData>) => void;
  removeNode: (nodeId: string) => void;
  addEdge: (edge: WorkflowEdge) => void;
  removeEdge: (edgeId: string) => void;
  
  setSelectedKnowledgeBase: (kb: string) => void;
  setSearchIntensity: (intensity: SearchIntensity) => void;
  
  validateWorkflow: () => boolean;
  getValidationErrors: () => string[];
  
  executeWorkflow: () => Promise<NodeBasedWorkflowResponse>;
  
  loadKnowledgeBases: () => Promise<void>;
  loadAvailableModels: (provider: LLMProvider) => Promise<void>;
}

// 노드 생성 헬퍼 함수
const createWorkflowNode = (nodeType: NodeType, position: { x: number; y: number }): WorkflowNode => {
  const id = `${nodeType}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  // 노드 타입별 기본 레이블
  const labels = {
    [NodeType.INPUT]: "입력 노드",
    [NodeType.GENERATION]: "생성 노드", 
    [NodeType.ENSEMBLE]: "앙상블 노드",
    [NodeType.VALIDATION]: "검증 노드",
    [NodeType.OUTPUT]: "출력 노드"
  };
  
  const nodeData: NodeData = {
    id,
    nodeType,
    label: labels[nodeType],
  };
  
  // input-node와 output-node는 content 필드 추가
  if (nodeType === NodeType.INPUT || nodeType === NodeType.OUTPUT) {
    nodeData.content = '';
  }
  
  // LLM 노드들은 모델 설정 필드 추가
  if ([NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(nodeType)) {
    nodeData.model_type = '';
    nodeData.llm_provider = LLMProvider.OPENAI;
    nodeData.prompt = '';
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

// 초기 노드 생성 함수
const createInitialNodes = (): WorkflowNode[] => {
  return [
    createWorkflowNode(NodeType.INPUT, { x: 400, y: 50 }),    // 상단 중앙
    createWorkflowNode(NodeType.OUTPUT, { x: 400, y: 550 })   // 하단 중앙
  ];
};

// 초기 엣지 생성 함수 - input-node와 output-node를 연결
const createInitialEdges = (inputNodeId: string, outputNodeId: string): WorkflowEdge[] => {
  return [
    {
      id: `edge_${inputNodeId}_${outputNodeId}_initial`,
      source: inputNodeId,
      target: outputNodeId
    }
  ];
};

export const useNodeWorkflowStore = create<NodeWorkflowState>((set, get) => {
  // 초기 노드들 생성
  const initialNodes = createInitialNodes();
  const inputNode = initialNodes.find(node => node.data.nodeType === NodeType.INPUT)!;
  const outputNode = initialNodes.find(node => node.data.nodeType === NodeType.OUTPUT)!;
  const initialEdges = createInitialEdges(inputNode.id, outputNode.id);

  return {
    // 초기 상태 - input-node와 output-node가 기본으로 생성되고 연결됨
    nodes: initialNodes,
    edges: initialEdges,
    selectedKnowledgeBase: '',
    searchIntensity: SearchIntensity.MEDIUM,
    isExecuting: false,
    executionResult: null,
    validationResult: null,
    validationErrors: [],
    availableModels: [],
    knowledgeBases: [],
  
  // 노드 관리 액션들
  addNode: (nodeType: NodeType, position: { x: number; y: number }) => {
    // output-node는 하나만 존재할 수 있음
    if (nodeType === NodeType.OUTPUT) {
      const state = get();
      const hasOutputNode = state.nodes.some(node => node.data.nodeType === NodeType.OUTPUT);
      if (hasOutputNode) {
        throw new Error('출력 노드는 하나만 존재할 수 있습니다.');
      }
    }
    
    // Input/Output 노드는 고정 위치 사용
    let nodePosition = position;
    if (nodeType === NodeType.INPUT) {
      nodePosition = { x: 400, y: 50 }; // 상단 중앙 고정
    } else if (nodeType === NodeType.OUTPUT) {
      nodePosition = { x: 400, y: 550 }; // 하단 중앙 고정
    }
    
    const newNode = createWorkflowNode(nodeType, nodePosition);
    set(state => ({
      nodes: [...state.nodes, newNode]
    }));
  },
  
  updateNode: (nodeId: string, updates: Partial<NodeData>) => {
    set(state => ({
      nodes: state.nodes.map(node => 
        node.id === nodeId 
          ? { ...node, data: { ...node.data, ...updates } }
          : node
      )
    }));
  },
  
  removeNode: (nodeId: string) => {
    const state = get();
    const nodeToRemove = state.nodes.find(node => node.id === nodeId);
    
    if (!nodeToRemove) return;
    
    // output-node는 삭제 불가
    if (nodeToRemove.data.nodeType === NodeType.OUTPUT) {
      message.error('출력 노드는 삭제할 수 없습니다.');
      throw new Error('출력 노드는 삭제할 수 없습니다.');
    }
    
    // input-node가 마지막 하나인 경우 삭제 불가
    if (nodeToRemove.data.nodeType === NodeType.INPUT) {
      const inputNodes = state.nodes.filter(node => node.data.nodeType === NodeType.INPUT);
      if (inputNodes.length <= 1) {
        message.error('입력 노드는 최소 하나는 존재해야 합니다.');
        throw new Error('입력 노드는 최소 하나는 존재해야 합니다.');
      }
    }
    
    set(state => ({
      nodes: state.nodes.filter(node => node.id !== nodeId),
      edges: state.edges.filter(edge => edge.source !== nodeId && edge.target !== nodeId)
    }));
    
    message.success(`${nodeToRemove.data.nodeType} 노드가 삭제되었습니다.`);
  },
  
  addEdge: (edge: WorkflowEdge) => {
    set(state => ({
      edges: [...state.edges, edge]
    }));
  },
  
  removeEdge: (edgeId: string) => {
    set(state => ({
      edges: state.edges.filter(edge => edge.id !== edgeId)
    }));
  },
  
  // 설정 액션들
  setSelectedKnowledgeBase: (kb: string) => {
    set({ selectedKnowledgeBase: kb });
  },
  
  setSearchIntensity: (intensity: SearchIntensity) => {
    set({ searchIntensity: intensity });
  },
  
  // 노드 실행 상태 업데이트
  setNodeExecutionStatus: (nodeId: string, isExecuting: boolean, isCompleted?: boolean) => {
    set(state => ({
      nodes: state.nodes.map(node => 
        node.id === nodeId 
          ? { 
              ...node, 
              data: { 
                ...node.data, 
                isExecuting,
                isCompleted: isCompleted ?? node.data.isCompleted
              } 
            }
          : node
      )
    }));
  },
  
  // 검증 액션들
  validateWorkflow: () => {
    const { nodes, edges } = get();
    const result = validateNodeWorkflow(nodes, edges);
    const errors = result.isValid ? [] : formatValidationErrors(result.errors);
    
    set({ 
      validationResult: result,
      validationErrors: errors 
    });
    
    return result.isValid;
  },
  
  getValidationErrors: () => {
    return get().validationErrors;
  },
  
  // 워크플로우 실행
  executeWorkflow: async () => {
    const state = get();
    
    // 실행 전 검증
    if (!state.validateWorkflow()) {
      throw new Error('워크플로우 검증 실패. 연결 규칙을 확인해주세요.');
    }

    set({ isExecuting: true, executionResult: null });
    
    try {
      // 서버가 기대하는 WorkflowExecutionRequest 형식으로 변환
      const workflowDefinition = {
        nodes: state.nodes.map(node => ({
          id: node.id,
          type: node.data.nodeType,
          position: node.position,
          content: node.data.content || null,
          model_type: node.data.model_type || null,
          llm_provider: node.data.llm_provider || null,
          prompt: node.data.prompt || null,
          output: null,
          executed: false,
          error: null
        })),
        edges: state.edges
      };

      const request = {
        workflow: workflowDefinition,
        knowledge_base: state.selectedKnowledgeBase || null,
        search_intensity: state.searchIntensity  // 문자열 그대로 전송
      };

      console.log('워크플로우 실행 요청:', request); // 디버깅용 단순화
      
      const result = await nodeBasedWorkflowAPI.executeNodeWorkflow(request);
      
      set({ 
        executionResult: result,
        isExecuting: false 
      });
      
      return result;
      
    } catch (error: any) {
      console.error('워크플로우 실행 에러:', error); // 디버깅용
      
      set({ isExecuting: false });
      
      // 더 자세한 에러 정보 추출
      let errorMessage = '알 수 없는 오류가 발생했습니다.';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      throw new Error(errorMessage);
    }
  },
  
  // 데이터 로딩
  loadKnowledgeBases: async () => {
    try {
      const knowledgeBases = await workflowAPI.getKnowledgeBases();
      console.log('로드된 지식베이스:', knowledgeBases); // 디버깅용
      set({ knowledgeBases });
    } catch (error) {
      console.error('지식 베이스 로딩 실패:', error);
    }
  },
  
  loadAvailableModels: async (provider: LLMProvider) => {
    try {
      const models = await workflowAPI.getProviderModels(provider);
      set({ availableModels: models });
    } catch (error) {
      console.error('모델 목록 로딩 실패:', error);
    }
  }
  };
});