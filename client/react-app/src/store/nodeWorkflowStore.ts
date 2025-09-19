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
import { DEFAULT_PROMPTS, OUTPUT_FORMAT_TEMPLATES } from '../config/defaultPrompts';

// ==================== 노드 기반 워크플로우 전용 스토어 ====================
// project_reference.md 기준 - 5가지 노드 타입만 지원

interface NodeWorkflowState {
  // 워크플로우 구성
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  
  // ReactFlow 뷰포트 상태
  viewport: { x: number; y: number; zoom: number } | null;
  currentViewport: { x: number; y: number; zoom: number };
  isRestoring: boolean; // 복원 상태 플래그
  
  // 실행 상태
  isExecuting: boolean;
  executionResult: NodeBasedWorkflowResponse | null;
  
  // 전역 Rerank 설정
  globalUseRerank: boolean;
  
  // 노드별 실행 상태 및 스트리밍 출력
  nodeExecutionStates: Record<string, 'idle' | 'executing' | 'completed' | 'error'>;
  nodeStreamingOutputs: Record<string, string>;
  nodeExecutionResults: Record<string, { success: boolean; description?: string; error?: string; execution_time?: number; }>;
  nodeStartOrder: string[]; // 노드 실행 시작 순서 추적
  
  // 검증 상태
  validationResult: ValidationResult | null;
  validationErrors: string[];
  
  // 모델 관리
  availableModels: AvailableModel[];
  knowledgeBases: KnowledgeBase[];
  
  // 노드 실행 상태 업데이트
  setNodeExecutionStatus: (nodeId: string, isExecuting: boolean, isCompleted?: boolean) => void;
  
  // 전역 Rerank 설정 관리
  setGlobalUseRerank: (useRerank: boolean) => void;
  
  // 액션들
  addNode: (nodeType: NodeType, position: { x: number; y: number }) => void;
  updateNode: (nodeId: string, updates: Partial<NodeData>) => void;
  removeNode: (nodeId: string) => void;
  addEdge: (edge: WorkflowEdge) => void;
  removeEdge: (edgeId: string) => void;
  
  validateWorkflow: () => boolean;
  getValidationErrors: () => string[];
  
  executeWorkflowStream: (onStreamUpdate: (data: any) => void) => Promise<void>;
  
  loadKnowledgeBases: () => Promise<void>;
  loadAvailableModels: (provider: LLMProvider) => Promise<void>;
  
  // 뷰포트 상태 관리
  setViewport: (viewport: { x: number; y: number; zoom: number }) => void;
  
  // 노드 위치 업데이트
  updateNodePositions: (nodePositions: { id: string; position: { x: number; y: number } }[]) => void;
  
  // 워크플로우 저장/복원/Import/Export 기능
  saveCurrentWorkflow: () => void;
  restoreWorkflow: () => boolean;
  resetToInitialState: () => void;
  exportToJSON: () => void;
  importFromJSON: (jsonData: string) => boolean;
  setRestoring: (isRestoring: boolean) => void;
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
  
  // LLM 노드들은 모델 및 검색 설정 필드 추가
  if ([NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(nodeType)) {
    nodeData.model_type = '';
    nodeData.llm_provider = LLMProvider.GOOGLE;
    nodeData.knowledge_base = ''; // 기본값: 없음
    
    // 기본 프롬프트 템플릿 적용
    nodeData.prompt = DEFAULT_PROMPTS[nodeType as keyof typeof DEFAULT_PROMPTS] || '';
    
    // 기본 출력 형식 템플릿 적용
    nodeData.output_format = OUTPUT_FORMAT_TEMPLATES[nodeType as keyof typeof OUTPUT_FORMAT_TEMPLATES] || '';
    
    // 노드 타입에 따른 기본 검색 강도 설정
    if (nodeType === NodeType.VALIDATION) {
      nodeData.search_intensity = SearchIntensity.VERY_LOW; // validation-node: 매우 낮음
    } else {
      nodeData.search_intensity = SearchIntensity.MEDIUM; // generation, ensemble: 보통
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

// 초기 노드 생성 함수
const createInitialNodes = (): WorkflowNode[] => {
  return [
    createWorkflowNode(NodeType.INPUT, { x: 400, y: 100 }),    // 상단 중앙 (더 위로)
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
    
    viewport: null,
    currentViewport: { x: 0, y: 0, zoom: 1 },
    isRestoring: false, // 복원 상태 초기값
    
    isExecuting: false,
    executionResult: null,
    
    // 전역 Rerank 설정 (로컬 스토리지에서 로드, 기본값: false)
    globalUseRerank: (() => {
      try {
        const saved = localStorage.getItem('globalUseRerank');
        return saved ? JSON.parse(saved) : false;
      } catch {
        return false;
      }
    })(),
    
    validationResult: null,
    validationErrors: [],
    availableModels: [],
    knowledgeBases: [],
    
    // 노드별 실행 상태 및 출력
    nodeExecutionStates: {},
    nodeStreamingOutputs: {},
    nodeExecutionResults: {},
    nodeStartOrder: [], // 노드 실행 시작 순서

    setRestoring: (isRestoring: boolean) => set({ isRestoring }),
  
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
    set(_ => ({
      nodes: get().nodes.concat(newNode)
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
  
  updateNode: (nodeId, updates) => {
    set(state => ({
      nodes: state.nodes.map(node =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...updates } }
          : node
      ),
    }));
  },

  removeNode: (nodeId) => {
    const nodeToRemove = get().nodes.find(n => n.id === nodeId);
    
    if (!nodeToRemove) return;
    
    // output-node는 삭제 불가
    if (nodeToRemove.data.nodeType === NodeType.OUTPUT) {
      message.error('출력 노드는 삭제할 수 없습니다.');
      throw new Error('출력 노드는 삭제할 수 없습니다.');
    }
    
    // input-node가 마지막 하나인 경우 삭제 불가
    if (nodeToRemove.data.nodeType === NodeType.INPUT) {
      const inputNodes = get().nodes.filter(node => node.data.nodeType === NodeType.INPUT);
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
  
  setViewport: (viewport: { x: number; y: number; zoom: number }) => {
    set({ 
      viewport,
      currentViewport: viewport // 실시간으로 현재 뷰포트도 업데이트
    });
  },
  
  updateNodePositions: (nodePositions: { id: string; position: { x: number; y: number } }[]) => {
    set(state => ({
      nodes: state.nodes.map(node => {
        const positionUpdate = nodePositions.find(np => np.id === node.id);
        if (positionUpdate) {
          return {
            ...node,
            position: positionUpdate.position
          };
        }
        return node;
      })
    }));
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

  // 전역 Rerank 설정 관리
  setGlobalUseRerank: (useRerank: boolean) => {
    set({ globalUseRerank: useRerank });
    // 로컬 스토리지에 저장
    try {
      localStorage.setItem('globalUseRerank', JSON.stringify(useRerank));
    } catch (error) {
      console.error('Rerank 설정 저장 실패:', error);
    }
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
  
  // 워크플로우 스트리밍 실행 (유일한 실행 방법)
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
        nodes: state.nodes.map(node => {
          const isLlmNode = [NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(node.data.nodeType);
          let finalPrompt = node.data.prompt || '';

          if (isLlmNode && node.data.output_format) {
            const outputFormatInstruction = `\n\n핵심 결과를 반드시 다음과 같은 형태로 만들어 출력에 포함시키세요. 이건 절대적으로 지켜야 할 사항입니다.\n<output>\n${node.data.output_format}\n</output>`;
            finalPrompt += outputFormatInstruction;
          }

          return {
            id: node.id,
            type: node.data.nodeType,
            position: node.position,
            content: node.data.content || null,
            model_type: node.data.model_type || null,
            llm_provider: node.data.llm_provider || null,
            prompt: finalPrompt,
            knowledge_base: node.data.knowledge_base || null,
            search_intensity: node.data.search_intensity || null,

            output: null,
            executed: false,
            error: null
          };
        }),
        edges: state.edges
      };

      const request = {
        workflow: workflowDefinition,
        use_rerank: state.globalUseRerank,
      };
      
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
        nodeExecutionResults: initialResults,
        nodeStartOrder: [] // 스트리밍 실행 시작 시 초기화
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
            },
            nodeStartOrder: state.nodeStartOrder.includes(chunk.node_id) 
              ? state.nodeStartOrder 
              : [...state.nodeStartOrder, chunk.node_id]
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
  },
  
  // 워크플로우 저장/복원/Import/Export 기능 구현
  saveCurrentWorkflow: () => {
    const { nodes, edges, currentViewport } = get();
    const workflowState = {
      nodes,
      edges,
      viewport: currentViewport, // 현재 뷰포트 상태 저장
      savedAt: new Date().toISOString(),
      version: '1.1' // 버전 업데이트
    };
    
    try {
      localStorage.setItem('node_workflow_state', JSON.stringify(workflowState));
    } catch (error) {
      console.error('워크플로우 저장 실패:', error);
      message.error('워크플로우 저장에 실패했습니다.');
    }
  },
  
  restoreWorkflow: () => {
    try {
      const savedState = localStorage.getItem('node_workflow_state');
      if (!savedState) return false;
      
      const workflowState = JSON.parse(savedState);
      const savedViewport = workflowState.viewport || { x: 0, y: 0, zoom: 1 };
      
      set({
        nodes: workflowState.nodes || [],
        edges: workflowState.edges || [],
        viewport: savedViewport,
        currentViewport: savedViewport, // currentViewport도 동일하게 설정
        // 실행 관련 상태는 초기화
        isExecuting: false,
        executionResult: null,
        nodeExecutionStates: {},
        nodeStreamingOutputs: {},
        nodeExecutionResults: {},
        validationResult: null,
        validationErrors: [],
        isRestoring: true, // 복원 시작
      });

      // 복원 완료 후 isRestoring을 false로 설정
      setTimeout(() => set({ isRestoring: false }), 100);

      return true;
      
    } catch (error) {
      console.error('워크플로우 복원 실패:', error);
      message.error('워크플로우 복원에 실패했습니다.');
      set({ isRestoring: false }); // 에러 시 복원 상태 해제
      return false;
    }
  },
  
  resetToInitialState: () => {
    const initialNodes = createInitialNodes();
    const initialViewport = { x: 0, y: 0, zoom: 1 }; // 노드들이 중앙에 보이도록 조정
    set({
      nodes: initialNodes,
      edges: [],
      viewport: initialViewport,
      currentViewport: initialViewport, // currentViewport도 초기화
      // 실행 관련 상태 초기화
      isExecuting: false,
      executionResult: null,
      nodeExecutionStates: {},
      nodeStreamingOutputs: {},
      nodeExecutionResults: {},
      validationResult: null,
      validationErrors: []
    });
  },
  
  exportToJSON: () => {
    const { nodes, edges, currentViewport } = get();
    const exportData = {
      version: '1.1', // 버전 업데이트
      exportedAt: new Date().toISOString(),
      workflow: {
        nodes,
        edges,
        viewport: currentViewport,
      }
    };
    
    try {
      const jsonString = JSON.stringify(exportData, null, 2);
      const blob = new Blob([jsonString], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `workflow_${new Date().toISOString()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('워크플로우를 파일로 내보냈습니다.');
    } catch (error) {
      console.error('워크플로우 내보내기 실패:', error);
      message.error('워크플로우 내보내기에 실패했습니다.');
    }
  },
  
  importFromJSON: (jsonData: string) => {
    try {
      const workflowData = JSON.parse(jsonData);
      
      // 노드와 엣지 데이터 추출
      let nodes = workflowData.nodes || workflowData.workflow?.nodes || [];
      let edges = workflowData.edges || workflowData.workflow?.edges || [];
      const viewport = workflowData.viewport || workflowData.workflow?.viewport || { x: 0, y: 0, zoom: 1 };
      
      // 노드 데이터 검증 및 정규화
      if (!Array.isArray(nodes)) {
        throw new Error('JSON 데이터에 노드 정보가 없습니다.');
      }
      if (!Array.isArray(edges)) {
        throw new Error('JSON 데이터에 엣지 정보가 없습니다.');
      }
      
      // 워크플로우 상태 업데이트
      set({
        nodes,
        edges,
        viewport,
        currentViewport: viewport,
        // 실행 관련 상태는 초기화
        isExecuting: false,
        executionResult: null,
        nodeExecutionStates: {},
        nodeStreamingOutputs: {},
        nodeExecutionResults: {},
        validationResult: null,
        validationErrors: [],
        isRestoring: true, // 복원 시작
      });

      // 복원 완료 후 isRestoring을 false로 설정
      setTimeout(() => set({ isRestoring: false }), 100);

      return true;
      
    } catch (error) {
      console.error('JSON 파싱 오류:', error);
      message.error('유효하지 않은 JSON 형식입니다.');
      return false;
    }
  }
  };
});