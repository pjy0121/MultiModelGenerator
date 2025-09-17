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
  
  // 노드별 실행 상태 및 스트리밍 출력
  nodeExecutionStates: Record<string, 'idle' | 'executing' | 'completed' | 'error'>;
  nodeStreamingOutputs: Record<string, string>;
  nodeExecutionResults: Record<string, { success: boolean; description?: string; error?: string; execution_time?: number; }>;
  
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
  executeWorkflowStream: (onStreamUpdate: (data: any) => void) => Promise<void>;
  
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
    nodeData.llm_provider = LLMProvider.GOOGLE;
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

export const useNodeWorkflowStore = create<NodeWorkflowState>((set, get) => {
  // 초기 노드들 생성 (연결 없이)
  const initialNodes = createInitialNodes();

  return {
    // 초기 상태 - input-node와 output-node가 기본으로 생성됨 (연결 없음)
    nodes: initialNodes,
    edges: [],
    selectedKnowledgeBase: '',
    searchIntensity: SearchIntensity.MEDIUM,
    isExecuting: false,
    executionResult: null,
    validationResult: null,
    validationErrors: [],
    availableModels: [],
    knowledgeBases: [],
    
    // 노드별 실행 상태 및 출력
    nodeExecutionStates: {},
    nodeStreamingOutputs: {},
    nodeExecutionResults: {},
  
  // 노드 관리 액션들
  addNode: async (nodeType: NodeType, position: { x: number; y: number }) => {
    // output-node는 하나만 존재할 수 있음
    if (nodeType === NodeType.OUTPUT) {
      const state = get();
      const hasOutputNode = state.nodes.some(node => node.data.nodeType === NodeType.OUTPUT);
      if (hasOutputNode) {
        throw new Error('출력 노드는 하나만 존재할 수 있습니다.');
      }
    }
    
    // Output 노드만 고정 위치 사용
    let nodePosition = position;
    if (nodeType === NodeType.OUTPUT) {
      nodePosition = { x: 400, y: 550 }; // 하단 중앙 고정
    }
    
    const newNode = createWorkflowNode(nodeType, nodePosition);
    
    // 먼저 노드를 추가
    set(state => ({
      nodes: [...state.nodes, newNode]
    }));
    
    // LLM 노드인 경우 Google 모델 목록을 로드하고 기본 모델 선택
    if ([NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(nodeType)) {
      try {
        const state = get();
        
        // 모든 provider 모델 목록 로드
        await state.loadAvailableModels(LLMProvider.GOOGLE);
        await state.loadAvailableModels(LLMProvider.OPENAI);
        
        // 모델 로드 완료 후 기본 모델 선택
        const updatedState = get();
        const googleModels = updatedState.availableModels.filter(
          model => model.provider === LLMProvider.GOOGLE
        );
        
        if (googleModels.length > 0) {
          // 기본 모델 우선순위: gemini-2.0-flash-exp > 첫 번째 모델
          const defaultModel = googleModels.find(m => m.value.includes('gemini-2.0-flash')) || googleModels[0];
          
          // 노드에 기본 모델 설정
          state.updateNode(newNode.id, {
            model_type: defaultModel.value
          });
          
          message.success(`${nodeType} 노드가 생성되고 기본 모델(${defaultModel.label})이 선택되었습니다.`);
        }
      } catch (error) {
        console.error('모델 로드 실패:', error);
        message.warning(`${nodeType} 노드가 생성되었지만 모델 로드에 실패했습니다. 수동으로 모델을 선택해주세요.`);
      }
    }
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

  // 워크플로우 스트리밍 실행
  executeWorkflowStream: async (onStreamUpdate: (data: any) => void) => {
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
        search_intensity: state.searchIntensity
      };

      console.log('스트리밍 워크플로우 실행 요청:', request);
      
      // 초기화 - 모든 노드를 idle 상태로 설정
      const initialStates: Record<string, 'idle' | 'executing' | 'completed' | 'error'> = {};
      const initialOutputs: Record<string, string> = {};
      const initialResults: Record<string, { success: boolean; description?: string; error?: string; execution_time?: number; }> = {};
      
      state.nodes.forEach(node => {
        initialStates[node.id] = 'idle';
        initialOutputs[node.id] = '';
        initialResults[node.id] = { success: false };
      });
      
      set({ 
        nodeExecutionStates: initialStates,
        nodeStreamingOutputs: initialOutputs,
        nodeExecutionResults: initialResults
      });
      
      // 스트리밍 실행
      for await (const chunk of nodeBasedWorkflowAPI.executeNodeWorkflowStream(request)) {
        onStreamUpdate(chunk);
        
        // 노드별 상태 업데이트
        if (chunk.type === 'node_start' && chunk.node_id) {
          set(state => ({
            nodeExecutionStates: {
              ...state.nodeExecutionStates,
              [chunk.node_id]: 'executing'
            }
          }));
        } else if (chunk.type === 'stream' && chunk.node_id && chunk.content) {
          // 스트리밍 업데이트를 배치로 처리하여 성능 최적화
          set(state => {
            const currentOutput = state.nodeStreamingOutputs[chunk.node_id] || '';
            const newOutput = currentOutput + chunk.content;
            
            // 불필요한 업데이트 방지
            if (currentOutput === newOutput) return state;
            
            return {
              ...state,
              nodeStreamingOutputs: {
                ...state.nodeStreamingOutputs,
                [chunk.node_id]: newOutput
              }
            };
          });
        } else if (chunk.type === 'node_complete' && chunk.node_id) {
          const status = chunk.success ? 'completed' : 'error';
          set(state => {
            const updatedResults = { ...state.nodeExecutionResults };
            
            // 모든 노드의 완료 결과를 즉시 저장 (성공/실패 상관없이)
            updatedResults[chunk.node_id] = {
              success: chunk.success,
              description: chunk.description || (chunk.success ? '' : chunk.error),
              error: chunk.success ? undefined : chunk.error,
              execution_time: chunk.execution_time
            };
            
            return {
              ...state,
              nodeExecutionStates: {
                ...state.nodeExecutionStates,
                [chunk.node_id]: status
              },
              nodeExecutionResults: updatedResults
            };
          });
        }
        
        // 완료 시 결과 저장
        if (chunk.type === 'complete') {
          // 실제 노드 실행 결과로 nodeExecutionResults 업데이트
          const nodeResults: Record<string, any> = {};
          if (chunk.results && Array.isArray(chunk.results)) {
            chunk.results.forEach((result: any) => {
              if (result.node_id) {
                nodeResults[result.node_id] = {
                  success: result.success,
                  description: result.description, // 실제 노드 실행 결과
                  error: result.error,
                  execution_time: result.execution_time
                };
              }
            });
          }

          // 완료된 모든 노드의 상태를 completed로 설정
          const completedStates: Record<string, 'idle' | 'executing' | 'completed' | 'error'> = {};
          if (chunk.results && Array.isArray(chunk.results)) {
            chunk.results.forEach((result: any) => {
              if (result.node_id) {
                completedStates[result.node_id] = result.success ? 'completed' : 'error';
              }
            });
          }

          set(state => ({ 
            executionResult: {
              success: chunk.success,
              results: chunk.results || [],
              final_output: chunk.final_output,
              total_execution_time: chunk.total_execution_time,
              execution_order: chunk.execution_order || [],
              error: chunk.error
            },
            nodeExecutionResults: {
              ...state.nodeExecutionResults,
              ...nodeResults // 실제 실행 결과로 업데이트
            },
            nodeExecutionStates: {
              ...state.nodeExecutionStates,
              ...completedStates // 완료된 노드 상태 업데이트
            },
            isExecuting: false 
          }));
        } else if (chunk.type === 'error') {
          set({ isExecuting: false });
        }
      }
      
    } catch (error: any) {
      console.error('스트리밍 워크플로우 실행 에러:', error);
      
      set({ isExecuting: false });
      
      let errorMessage = '알 수 없는 오류가 발생했습니다.';
      if (error.message) {
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
      const state = get();
      
      // 기존 모델 중 다른 provider 모델들은 유지하고, 해당 provider 모델만 교체
      const otherProviderModels = state.availableModels.filter(model => model.provider !== provider);
      const updatedModels = [...otherProviderModels, ...models];
      
      set({ availableModels: updatedModels });
    } catch (error) {
      console.error('모델 목록 로딩 실패:', error);
    }
  }
  };
});