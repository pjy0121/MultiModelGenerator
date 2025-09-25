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
  StreamChunk
} from '../types';
import { showSuccessMessage } from '../utils/messageUtils';
import { nodeBasedWorkflowAPI } from '../services/api';
import { validateNodeWorkflow, formatValidationErrors } from '../utils/nodeWorkflowValidation';
import { createWorkflowNode, createInitialNodes } from '../utils/nodeFactory';

// ==================== 노드 기반 워크플로우 전용 스토어 ====================
// project_reference.md 기준 - 5가지 노드 타입만 지원

interface NodeWorkflowState {
  // 워크플로우 구성
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  
  // ReactFlow 뷰포트 상태 (중복 제거: viewport만 유지)
  viewport: { x: number; y: number; zoom: number };
  isRestoring: boolean; // 복원 상태 플래그
  
  // 실행 상태
  isExecuting: boolean;
  isStopping: boolean; // 워크플로우 중단 중인 상태
  executionResult: NodeBasedWorkflowResponse | null;
  
  // 노드별 실행 상태 및 스트리밍 출력
  nodeExecutionStates: Record<string, 'idle' | 'executing' | 'completed' | 'error'>;
  nodeStreamingOutputs: Record<string, string>;
  nodeExecutionResults: Record<string, { success: boolean; description?: string; error?: string; execution_time?: number; }>;
  nodeStartOrder: string[]; // 노드 실행 시작 순서 추적
  
  // 검증 상태
  validationResult: ValidationResult | null;
  validationErrors: string[];
  
  // 노드 실행 상태 업데이트
  setNodeExecutionStatus: (nodeId: string, isExecuting: boolean, isCompleted?: boolean) => void;
  
  // 액션들
  addNode: (nodeType: NodeType, position: { x: number; y: number }) => void;
  updateNode: (nodeId: string, updates: Partial<NodeData>) => void;
  removeNode: (nodeId: string) => void;
  addEdge: (edge: WorkflowEdge) => void;
  removeEdge: (edgeId: string) => void;
  
  validateWorkflow: () => boolean;
  getValidationErrors: () => string[];
  
  executeWorkflowStream: (onStreamUpdate: (data: StreamChunk) => void) => Promise<void>;
  stopWorkflowExecution: () => void;
  clearAllExecutionResults: () => void;
  
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

export const useNodeWorkflowStore = create<NodeWorkflowState>((set, get) => {
  // 초기 노드들 생성 (연결 없이)
  const initialNodes = createInitialNodes();

  return {
    // 초기 상태 - input-node와 output-node가 기본으로 생성됨 (연결 없음)
    nodes: initialNodes,
    edges: [],
    
    viewport: { x: 0, y: 0, zoom: 1 },
    isRestoring: false, // 복원 상태 초기값
    
    isExecuting: false,
    isStopping: false, // 중단 상태 초기값
    executionResult: null,
    
    validationResult: null,
    validationErrors: [],
    
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
    
    // LLM 노드인 경우 기본 provider와 모델 설정
    if ([NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(nodeType)) {
      const state = get();
      state.updateNode(newNode.id, {
        llm_provider: LLMProvider.GOOGLE,
        model_type: 'gemini-1.5-flash' // 기본 모델 설정
      });
      showSuccessMessage(`${nodeType} 노드가 생성되었습니다. 필요시 편집에서 모델을 변경해주세요.`);
    }
    
    // Context 노드인 경우 기본 검색 강도와 rerank 설정
    if (nodeType === NodeType.CONTEXT) {
      const state = get();
      state.updateNode(newNode.id, {
        search_intensity: SearchIntensity.MEDIUM,
        rerank_provider: LLMProvider.NONE, // 기본값: 재정렬 사용 안 함
        rerank_model: undefined
      });
      message.success(`${nodeType} 노드가 생성되었습니다. 지식 베이스를 선택해주세요.`);
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
      set({ viewport });
    },  updateNodePositions: (nodePositions: { id: string; position: { x: number; y: number } }[]) => {
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
  executeWorkflowStream: async (onStreamUpdate: (data: StreamChunk) => void) => {
    const state = get();
    
    // 실행 전 검증 - 구체적인 에러 메시지 제공
    if (!state.validateWorkflow()) {
      const errors = state.getValidationErrors();
      const detailedMessage = errors.length > 0 
        ? `워크플로우 검증 실패:\n${errors.join('\n')}`
        : '워크플로우 검증 실패. 연결 규칙을 확인해주세요.';
      
      console.error('워크플로우 검증 실패:', errors);
      throw new Error(detailedMessage);
    }

    set({ isExecuting: true, executionResult: null });
    
    try {
      // 서버가 기대하는 WorkflowExecutionRequest 형식으로 변환
      const workflowDefinition = {
        nodes: state.nodes.map(node => {
          const isLlmNode = [NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(node.data.nodeType);
          let finalPrompt = node.data.prompt || '';

          if (isLlmNode && node.data.output_format) {
            const outputFormatInstruction = `\n\n핵심 결과를 반드시 다음과 같은 형태로 만들어 출력 시 가장 앞 부분에 포함시키세요. 이건 절대적으로 지켜야 할 사항입니다.\n\n<output>\n${node.data.output_format}\n</output>`;
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
            rerank_provider: node.data.rerank_provider || null,
            rerank_model: node.data.rerank_model || null,

            output: null,
            executed: false,
            error: null
          };
        }),
        edges: state.edges
      };

      const request = {
        workflow: workflowDefinition,
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
        
        // validation_error 타입 처리
        if (chunk.type === 'validation_error') {
          const validationErrors = chunk.errors || ['알 수 없는 검증 오류'];
          const detailedMessage = `백엔드 워크플로우 검증 실패:\n${validationErrors.map((error: string, index: number) => `${index + 1}. ${error}`).join('\n')}`;
          
          console.error('백엔드 검증 실패:', validationErrors);
          throw new Error(detailedMessage);
        }
        
        // 중단 요청 이벤트 처리
        if (chunk.type === 'stop_requested') {
          console.log('서버에서 중단 요청을 확인했습니다:', chunk.message);
          // 이미 isStopping이 true로 설정되어 있으므로 추가 처리 불필요
        }
        
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
          const nodeResults: Record<string, { success: boolean; description?: string; error?: string; execution_time?: number }> = {};
          if (chunk.results && Array.isArray(chunk.results)) {
            chunk.results.forEach((result: { node_id?: string; success: boolean; description?: string; error?: string; execution_time?: number }) => {
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
            chunk.results.forEach((result: { node_id?: string; success: boolean }) => {
              if (result.node_id) {
                completedStates[result.node_id] = result.success ? 'completed' : 'error';
              }
            });
          }

          // 중단 상태 확인 (상태 업데이트 전에)
          const currentState = get();
          const wasStopping = currentState.isStopping;
          const serverWasStopped = chunk.was_stopped; // 서버에서 전달된 중단 정보
          
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
            isExecuting: false,
            isStopping: false // 워크플로우 완료 시 중단 상태도 정리
          }));
          
          // 중단 요청이 있었다면 여기서 처리 완료
          if (wasStopping || serverWasStopped) {
            message.success('워크플로우가 중단되었습니다. 실행 중이던 노드들의 출력은 모두 완료되었습니다.');
          }
          
          // WorkflowComplete 처리 완료, finally 블록 실행하지 않음
          return;
        } else if (chunk.type === 'error') {
          // 에러 발생 시 실행 중이던 노드만 idle로 되돌리고, 완료된 노드는 유지
          const state = get();
          const updatedStates = { ...state.nodeExecutionStates };
          
          // 실행 중인 노드만 idle로 되돌림
          Object.keys(updatedStates).forEach(nodeId => {
            if (updatedStates[nodeId] === 'executing') {
              updatedStates[nodeId] = 'idle';
            }
          });
          
          set({ 
            isExecuting: false,
            nodeExecutionStates: updatedStates
            // 완료된 노드의 결과와 출력은 유지
          });
        }
      }
      
    } catch (error: unknown) {
      console.error('스트리밍 워크플로우 실행 에러:', error);
      
      // 에러 발생 시 실행 중이던 노드만 idle로 되돌리고, 완료된 노드는 유지
      const state = get();
      const updatedStates = { ...state.nodeExecutionStates };
      
      // 실행 중인 노드만 idle로 되돌림
      Object.keys(updatedStates).forEach(nodeId => {
        if (updatedStates[nodeId] === 'executing') {
          updatedStates[nodeId] = 'idle';
        }
      });
      
      set({ 
        isExecuting: false,
        nodeExecutionStates: updatedStates
        // 완료된 노드의 결과와 출력은 유지
      });
      
      let errorMessage = '알 수 없는 오류가 발생했습니다.';
      if (error instanceof Error && error.message) {
        errorMessage = error.message;
      }
      
      throw new Error(errorMessage);
    } finally {
      // 중단 상태인지 확인 (상태 정리 전에)
      const currentState = get();
      const wasStopping = currentState.isStopping;
      
      // 실행 상태 및 중단 상태 정리
      set({ 
        isExecuting: false,
        isStopping: false
      });
      
      // 중단된 경우 메시지 표시
      if (wasStopping) {
        message.success('워크플로우가 중단되었습니다. 실행 중이던 노드들의 출력은 모두 완료되었습니다.');
      }
    }
  },

  stopWorkflowExecution: async () => {
    // 워크플로우 실행을 수동으로 중단
    const state = get();
    if (!state.isExecuting || state.isStopping) return;
    
    // 중단 상태로 전환
    set({ isStopping: true });
    
    try {
      // 서버에 중단 요청
      const result = await nodeBasedWorkflowAPI.stopWorkflowExecution();
      message.info(result.message || '워크플로우 중단 요청이 전송되었습니다.');
    } catch (error) {
      console.error('워크플로우 중단 요청 실패:', error);
      message.error('워크플로우 중단 요청에 실패했습니다.');
      // 실패 시 중단 상태 해제
      set({ isStopping: false });
    }
  },

  clearAllExecutionResults: () => {
    // 모든 실행 결과를 완전히 초기화 (사용자가 의도적으로 선택)
    const state = get();
    const resetStates: Record<string, 'idle' | 'executing' | 'completed' | 'error'> = {};
    const resetOutputs: Record<string, string> = {};
    const resetResults: Record<string, { success: boolean; description?: string; error?: string; execution_time?: number; }> = {};
    
    state.nodes.forEach(node => {
      resetStates[node.id] = 'idle';
      resetOutputs[node.id] = '';
      resetResults[node.id] = { success: false };
    });
    
    set({ 
      isExecuting: false,
      nodeExecutionStates: resetStates,
      nodeStreamingOutputs: resetOutputs,
      nodeExecutionResults: resetResults,
      nodeStartOrder: [],
      executionResult: null
    });
    
    message.success('모든 실행 결과가 초기화되었습니다.');
  },
  
  // 데이터 로딩
  // 워크플로우 저장/복원/Import/Export 기능 구현
  saveCurrentWorkflow: () => {
    const { nodes, edges, viewport } = get();
    const workflowState = {
      nodes,
      edges,
      viewport, // 현재 뷰포트 상태 저장
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
        // viewport는 이미 위에서 설정됨
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
      // viewport는 이미 위에서 설정됨
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
    const { nodes, edges, viewport } = get();
    const exportData = {
      version: '1.1', // 버전 업데이트
      exportedAt: new Date().toISOString(),
      workflow: {
        nodes,
        edges,
        viewport,
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
        // viewport는 이미 설정됨
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