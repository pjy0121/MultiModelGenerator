import { create } from 'zustand';
import { WorkflowNode, PlaceholderNode, WorkflowNodeData, AnyWorkflowNode, LayerType, WorkflowExecution, WorkflowExecutionStep, LayerExecutionResponse, ValidationLayerResponse, SearchIntensity, LLMProvider, AvailableModel } from '../types';
import { stepwiseWorkflowAPI, layerPromptAPI, workflowAPI } from '../services/api';
import { DEFAULT_LAYER_PROMPTS, DEFAULT_LAYER_INPUTS } from '../config/defaultPrompts';

// 타입 가드 함수 정의
function isWorkflowNode(node: AnyWorkflowNode): node is WorkflowNode {
  return node.type === 'customNode';
}

function isPlaceholderNode(node: AnyWorkflowNode): node is PlaceholderNode {
  return node.type === 'placeholderNode';
}

// 요구사항에서 검색 키워드 추출 함수
function extractKeywordsFromRequirements(requirements: string): string[] {
  if (!requirements) return [];
  
  const keywords: string[] = [];
  
  try {
    // 개선된 마크다운 테이블 파싱 - 멀티라인 셀 지원
    const tableMatch = requirements.match(/(\|[^|]*\|.*?\|[^|]*\|[^|]*\|)/gs);
    
    if (tableMatch && tableMatch.length > 0) {
      // 각 테이블 행 처리
      tableMatch.forEach(tableSection => {
        // 여러 줄에 걸친 행들을 분리
        const lines = tableSection.split('\n').filter(line => line.trim() && line.includes('|'));
        
        let currentRow = '';
        let pipeCount = 0;
        
        for (const line of lines) {
          // 헤더나 구분선 스킵
          if (line.includes('---') || /^\s*\|\s*(REQ-?\d*|요구사항|Requirement)/i.test(line)) {
            continue;
          }
          
          currentRow += ' ' + line.trim();
          pipeCount = (currentRow.match(/\|/g) || []).length;
          
          // 4개 이상의 파이프가 있으면 완전한 행으로 간주 (ID | 요구사항 | 설명 | 상태)
          if (pipeCount >= 4) {
            const cells = currentRow.split('|').map(cell => cell.trim()).filter(cell => cell);
            
            if (cells.length >= 3) {
              // 두 번째 셀(요구사항)과 세 번째 셀(설명)에서 키워드 추출
              const requirementText = cells[1] || '';
              const descriptionText = cells[2] || '';
              
              // 요구사항 텍스트에서 키워드 추출
              if (requirementText.length > 10) {
                const reqKeywords = extractKeywordsFromText(requirementText);
                keywords.push(...reqKeywords.slice(0, 5));
              }
              
              // 설명 텍스트에서도 중요 키워드 추출 (더 제한적으로)
              if (descriptionText.length > 20) {
                const descKeywords = extractKeywordsFromText(descriptionText);
                keywords.push(...descKeywords.slice(0, 3));
              }
            }
            
            // 현재 행 초기화
            currentRow = '';
            pipeCount = 0;
          }
        }
      });
    } else {
      // 테이블 형식이 아닌 경우 전체 텍스트에서 추출
      return extractKeywordsFromText(requirements);
    }
  } catch (error) {
    // 파싱 오류 시 전체 텍스트에서 추출
    return extractKeywordsFromText(requirements);
  }
  
  // 중복 제거 및 상위 8개 반환 (더 많은 키워드로 검색 강화)
  const uniqueKeywords = Array.from(new Set(keywords)).slice(0, 8);
  return uniqueKeywords;
}

// 텍스트에서 직접 키워드 추출하는 보조 함수
function extractKeywordsFromText(text: string): string[] {
  const keywords: string[] = [];
  
  // 1. 요구사항 ID 패턴 (REQ-001, R1.1, F1 등) - 우선순위 높음
  const reqIds = text.match(/REQ[-_]\d+|R\d+\.\d+|F\d+|[A-Z]+[-_]?\d+/gi) || [];
  keywords.push(...reqIds);
  
  // 2. 기술 용어 및 필드명 추출 (영문)
  const techTerms = text.match(/\b[A-Z][a-z]*[-\s][A-Z][a-z]*(?:[-\s][A-Z][a-z]*)*\b/g) || []; // Device Self-test, Host-Initiated 등
  keywords.push(...techTerms);
  
  // 3. 중요한 영문 단어 (3글자 이상)
  const englishWords = text.match(/\b[A-Za-z]{3,}\b/g) || [];
  const filteredEnglishWords = englishWords.filter(word => 
    !/^(the|and|for|with|when|that|this|from|they|have|will|been|said|each|which|their|time|page|field|shall|controller|command|operation|processing)$/i.test(word)
  );
  keywords.push(...filteredEnglishWords.slice(0, 8));
  
  // 4. 16진수 값 패턴 (1h, 2h, 3h 등)
  const hexValues = text.match(/\b[0-9a-fA-F]+h\b/g) || [];
  keywords.push(...hexValues);
  
  // 5. 한글 기능 동사 (한글 문서인 경우)
  const functionVerbs = text.match(/\b(지원|제공|수행|처리|관리|생성|삭제|수정|조회|검색|저장|로드|전송|수신|연결|설정|구성|실행|종료|시작|중지|확인|검증|승인|거부)\w*/gi) || [];
  keywords.push(...functionVerbs);
  
  // 6. 중요 명사 추출 (한글 3글자 이상)
  const koreanNouns = text.match(/[가-힣]{3,}/g) || [];
  keywords.push(...koreanNouns.filter(noun => !/^(요구사항|기능|시스템|사용자|해야|한다|된다)$/.test(noun)));
  
  // 중복 제거 및 최대 10개 반환
  return Array.from(new Set(keywords)).slice(0, 10);
}

// 검색 강도에 따른 top_k 값 계산 함수
function getTopKByIntensity(intensity: SearchIntensity, type: 'basic' | 'keyword' | 'context'): number {
  const configs = {
    [SearchIntensity.LOW]: {
      basic: 8,      // 기본 검색 - 적은 양
      keyword: 20,   // 키워드별 검색 - 포괄적 (문서 전체 훑기)
      context: 15    // 최종 컨텍스트 - 적은 양
    },
    [SearchIntensity.MEDIUM]: {
      basic: 15,     // 중간 검색량
      keyword: 30,   // 키워드별 검색 - 포괄적 (문서 전체 훑기)
      context: 25    // 최종 컨텍스트
    },
    [SearchIntensity.HIGH]: {
      basic: 25,     // 최대 검색량
      keyword: 40,   // 키워드별 검색 - 매우 포괄적 (문서 전체 훑기)
      context: 35    // 최종 컨텍스트
    }
  };
  
  return configs[intensity][type];
}

// 검색 강도에 따른 키워드 개수 계산 함수
function getMaxKeywordsByIntensity(intensity: SearchIntensity): number {
  switch (intensity) {
    case SearchIntensity.LOW: return 3;
    case SearchIntensity.MEDIUM: return 5;
    case SearchIntensity.HIGH: return 8;
    default: return 5;
  }
}

interface WorkflowState {
  nodes: AnyWorkflowNode[];
  selectedKnowledgeBase: string;
  keyword: string;
  searchIntensity: SearchIntensity;  // 검색 강도 설정
  isExecuting: boolean;
  result: any;
  currentViewport: { x: number; y: number; zoom: number } | null;
  
  // LLM Provider 선택 관련 상태
  selectedProvider: LLMProvider | null;
  providerModels: AvailableModel[]; // 현재 선택된 Provider의 모델 목록
  
  // 새로운 단계별 워크플로우 실행 상태
  currentExecution: WorkflowExecution | null;
  
  // Layer별 프롬프트 상태
  layerPrompts: {
    [LayerType.GENERATION]: string;
    [LayerType.ENSEMBLE]: string;
    [LayerType.VALIDATION]: string;
  };
  layerInputs: {
    [LayerType.GENERATION]: string;
    [LayerType.ENSEMBLE]: string;
    [LayerType.VALIDATION]: string;
  };
  layerResults: {
    [LayerType.GENERATION]: any;
    [LayerType.ENSEMBLE]: any;
    [LayerType.VALIDATION]: any;
  };
  
  // 현재 실행 중인 Layer 상태
  currentExecutingLayer: LayerType | null;
  
  // Actions
  setNodes: (nodes: AnyWorkflowNode[]) => void;
  addNode: (layer: LayerType) => Promise<void>;
  updateNode: (nodeId: string, data: Partial<WorkflowNodeData>) => void;
  removeNode: (nodeId: string) => void;
  setSelectedKnowledgeBase: (kb: string) => void;
  setKeyword: (keyword: string) => void;
  setSearchIntensity: (intensity: SearchIntensity) => void;  // 검색 강도 설정
  setIsExecuting: (executing: boolean) => void;
  setResult: (result: any) => void;
  updatePlaceholderNodes: () => void;
  initializeDefaultWorkflow: () => Promise<void>;
  
  // LLM Provider 관련 액션들
  getDefaultModelForProvider: (provider: LLMProvider) => string;
  setSelectedProvider: (provider: LLMProvider | null) => Promise<void>;
  loadProviderModels: (provider: LLMProvider) => Promise<AvailableModel[]>;
  updateAllNodesModelByProvider: (provider: LLMProvider) => Promise<void>;
  
  // 뷰포트 관련 액션들
  setCurrentViewport: (viewport: { x: number; y: number; zoom: number }) => void;
  saveCurrentWorkflow: () => void;
  restoreWorkflow: () => Promise<boolean>;
  exportToJSON: () => void;
  
  // 새로운 단계별 워크플로우 액션들
  startStepwiseExecution: () => Promise<void>;
  resetExecution: () => void;
  updateExecutionStep: (stepId: string, update: Partial<WorkflowExecutionStep>) => void;
  
  // Layer 프롬프트 및 입력 관리 액션들
  setLayerPrompt: (layer: LayerType, prompt: string) => void;
  setLayerInput: (layer: LayerType, input: string) => void;
  executeLayerWithPrompt: (layer: LayerType) => Promise<LayerExecutionResponse | ValidationLayerResponse>;
  parseStructuredOutput: (content: string) => { general_output: string; forward_data: string };
  extractStructuredContent: (content: any) => { general_output: string; forward_data: string };
}

// 레이어별 고정 위치 설정
const LAYER_POSITIONS = {
  [LayerType.GENERATION]: { baseX: 100, baseY: 100, spacing: 200 },
  [LayerType.ENSEMBLE]: { baseX: 100, baseY: 300, spacing: 0 },
  [LayerType.VALIDATION]: { baseX: 100, baseY: 500, spacing: 200 }
};

const createDefaultNode = (layer: LayerType, position: { x: number; y: number }): WorkflowNode => {
  const id = `${layer}_${Date.now()}`;
  
  return {
    id,
    type: 'customNode',
    position,
    data: {
      id,
      model: '', // 모델명이 설정되면 업데이트됨
      layer,
      label: "모델 선택 필요" // 모델이 선택되면 업데이트됨
    },
    className: 'nopan',
    draggable: false,
    selectable: true,
    deletable: false
  };
};

const createPlaceholderNode = (
  layer: LayerType, 
  position: { x: number; y: number }, 
  addNodeFunction: (layer: LayerType) => void
): PlaceholderNode => {
  const id = `placeholder_${layer}_${Date.now()}`;
  
  return {
    id,
    type: 'placeholderNode',
    position,
    data: {
      layer,
      onAddNode: addNodeFunction
    },
    className: 'nopan',
    draggable: false,
    selectable: true,
    deletable: false
  };
};

const WORKFLOW_SAVE_KEY = 'saved_workflow_state';

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  nodes: [
    createDefaultNode(LayerType.GENERATION, { 
      x: LAYER_POSITIONS[LayerType.GENERATION].baseX, 
      y: LAYER_POSITIONS[LayerType.GENERATION].baseY 
    }),
    createDefaultNode(LayerType.ENSEMBLE, { 
      x: LAYER_POSITIONS[LayerType.ENSEMBLE].baseX, 
      y: LAYER_POSITIONS[LayerType.ENSEMBLE].baseY 
    }),
    createDefaultNode(LayerType.VALIDATION, { 
      x: LAYER_POSITIONS[LayerType.VALIDATION].baseX, 
      y: LAYER_POSITIONS[LayerType.VALIDATION].baseY 
    })
  ],
  selectedKnowledgeBase: '',
  keyword: '',
  searchIntensity: SearchIntensity.MEDIUM,
  isExecuting: false,
  result: null,
  currentViewport: null,
  
  // LLM Provider 관련 초기 상태
  selectedProvider: LLMProvider.GOOGLE,
  providerModels: [], // 현재 선택된 Provider의 모델 목록
  layerPrompts: DEFAULT_LAYER_PROMPTS,
  layerInputs: DEFAULT_LAYER_INPUTS,
  layerResults: {
    [LayerType.GENERATION]: null,
    [LayerType.ENSEMBLE]: null,
    [LayerType.VALIDATION]: null
  },
  
  // 현재 실행 중인 Layer 상태
  currentExecutingLayer: null,
  
  // 새로운 단계별 워크플로우 실행 상태
  currentExecution: null,

  setNodes: (nodes) => set({ nodes }),
  
  // ✅ 현재 뷰포트 설정 (실시간으로 계속 업데이트됨)
  setCurrentViewport: (viewport) => set({ currentViewport: viewport }),
  
  addNode: async (layer) => {    
    const { nodes } = get();
    const realNodes = nodes.filter(isWorkflowNode).filter(n => n.data.layer === layer);
    
    // 개수 제한 체크
    if (layer === LayerType.GENERATION && realNodes.length >= 5) {
      return;
    }
    if (layer === LayerType.VALIDATION && realNodes.length >= 3) {
      return;
    }
    if (layer === LayerType.ENSEMBLE) {
      return;
    }
    
    // 고정 위치 계산
    const layerConfig = LAYER_POSITIONS[layer];
    const newPosition = {
      x: layerConfig.baseX + (realNodes.length * layerConfig.spacing),
      y: layerConfig.baseY
    };
    
    const newNode = createDefaultNode(layer, newPosition);
    const nonPlaceholderNodes = nodes.filter(n => !isPlaceholderNode(n));
    set({ nodes: [...nonPlaceholderNodes, newNode] });
    
    // 현재 provider의 기본 모델로 설정
    const provider = get().selectedProvider;
    if (provider) {
      const defaultModel = get().getDefaultModelForProvider(provider);
      if (defaultModel) {
        get().updateNode(newNode.id, {
          model: defaultModel,
          label: defaultModel
        });
      }
    }
    
    setTimeout(() => {
      get().updatePlaceholderNodes();
    }, 0);
  },

  updateNode: (nodeId, data) => {
    const { nodes } = get();
    const updatedNodes = nodes.map((node): AnyWorkflowNode => {
      if (node.id === nodeId && isWorkflowNode(node)) {
        // 라벨 결정: 전달받은 라벨이 있으면 사용, 없으면 기존 라벨 유지
        let newLabel = data.label || node.data.label;
        
        return { 
          ...node, 
          data: { 
            ...node.data, 
            ...data,
            label: newLabel
          }
        };
      }
      return node;
    });
    set({ nodes: updatedNodes });
  },

  removeNode: (nodeId) => {    
    const { nodes } = get();
    const node = nodes.find(n => n.id === nodeId);
    
    if (!node || !isWorkflowNode(node)) {
      return;
    }
    
    if (node.data.layer === LayerType.ENSEMBLE) {
      return;
    }
    
    const layerNodes = nodes.filter(isWorkflowNode)
      .filter(n => n.data.layer === node.data.layer)
      .sort((a, b) => a.position.x - b.position.x);
      
    if (layerNodes.length <= 1) {
      return;
    }
    
    // 마지막 노드인지 확인
    const lastNode = layerNodes[layerNodes.length - 1];
    if (lastNode.id !== nodeId) {
      return;
    }
    
    const filteredNodes = nodes.filter(n => n.id !== nodeId);
    set({ nodes: filteredNodes });
    
    setTimeout(() => {
      get().updatePlaceholderNodes();
    }, 0);
  },

  updatePlaceholderNodes: () => {
    const state = get();
    const { nodes } = state;
        
    const realNodes = nodes.filter(n => !isPlaceholderNode(n));
    const newNodes: AnyWorkflowNode[] = [...realNodes];
    const addNodeFunction = state.addNode;
    
    // Generation Layer placeholder
    const generationNodes = realNodes.filter(isWorkflowNode)
      .filter(n => n.data.layer === LayerType.GENERATION)
      .sort((a, b) => a.position.x - b.position.x);
    
    if (generationNodes.length < 5) {
      const nextPosition = {
        x: LAYER_POSITIONS[LayerType.GENERATION].baseX + (generationNodes.length * LAYER_POSITIONS[LayerType.GENERATION].spacing),
        y: LAYER_POSITIONS[LayerType.GENERATION].baseY
      };
      
      newNodes.push(createPlaceholderNode(LayerType.GENERATION, nextPosition, addNodeFunction));
    }
    
    // Validation Layer placeholder
    const validationNodes = realNodes.filter(isWorkflowNode)
      .filter(n => n.data.layer === LayerType.VALIDATION)
      .sort((a, b) => a.position.x - b.position.x);
    
    if (validationNodes.length < 3) {
      const nextPosition = {
        x: LAYER_POSITIONS[LayerType.VALIDATION].baseX + (validationNodes.length * LAYER_POSITIONS[LayerType.VALIDATION].spacing),
        y: LAYER_POSITIONS[LayerType.VALIDATION].baseY
      };
      
      newNodes.push(createPlaceholderNode(LayerType.VALIDATION, nextPosition, addNodeFunction));
    }
    
    set({ nodes: newNodes });
  },

  // ✅ 현재 워크플로우 상태를 localStorage에 저장 (뷰포트, Provider 포함, 지식 베이스/키워드 제외)
  saveCurrentWorkflow: () => {
    const { nodes, currentViewport, selectedProvider } = get();
    const workflowState = {
      nodes,
      viewport: currentViewport, // ✅ 현재 뷰포트 상태 포함 (x, y, zoom)
      selectedProvider, // ✅ 현재 선택된 Provider 포함
      savedAt: new Date().toISOString()
    };
    
    localStorage.setItem(WORKFLOW_SAVE_KEY, JSON.stringify(workflowState));
  },

  // ✅ 저장된 워크플로우 상태 복원 (뷰포트, Provider 포함, 지식 베이스/키워드 제외)
  restoreWorkflow: async () => {
    try {
      const savedState = localStorage.getItem(WORKFLOW_SAVE_KEY);
      if (savedState) {
        const workflowState = JSON.parse(savedState);
        const { selectedProvider: currentProvider } = get();
        
        set({ 
          nodes: workflowState.nodes || [],
          currentViewport: workflowState.viewport || null // ✅ 뷰포트 복원 (x, y, zoom)
        });
        
        // 저장된 Provider가 있으면 사용, 없으면 기본 Provider 사용
        const savedProvider = workflowState.selectedProvider || LLMProvider.GOOGLE;
        const providerChanged = currentProvider !== savedProvider;
        
        // Provider 설정
        set({ selectedProvider: savedProvider });
        
        // Provider의 모델 목록 로드
        const providerModels = await get().loadProviderModels(savedProvider);
        set({ providerModels });
        
        // Provider가 변경된 경우에만 노드들을 기본 모델로 업데이트
        if (providerChanged && providerModels.length > 0) {
          await get().updateAllNodesModelByProvider(savedProvider);
        }
        
        setTimeout(() => {
          get().updatePlaceholderNodes();
        }, 100);
        
        return true;
      }
      return false;
    } catch (error) {
      return false;
    }
  },

  // JSON 파일로 Export (다운로드)
  exportToJSON: () => {
    const { nodes, selectedKnowledgeBase, keyword, searchIntensity, currentViewport } = get();
    const exportData = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      workflow: {
        nodes,
        selectedKnowledgeBase,
        keyword,
        searchIntensity,  // 검색 강도도 Export에 포함
        viewport: currentViewport // ✅ Export 시에도 뷰포트 포함
      }
    };

    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `workflow_export_${new Date().getTime()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },

  setSelectedKnowledgeBase: (kb) => set({ selectedKnowledgeBase: kb }),
  setKeyword: (keyword) => set(state => ({ 
    keyword,
    layerInputs: {
      ...state.layerInputs,
      [LayerType.GENERATION]: keyword  // Generation Layer의 input을 키워드로 자동 설정
    }
  })),
  setSearchIntensity: (intensity) => set({ searchIntensity: intensity }),
  setIsExecuting: (executing) => set({ isExecuting: executing }),
  setResult: (result) => set({ result }),
  
  // 새로운 단계별 워크플로우 메서드들
  resetExecution: () => set({ currentExecution: null }),
  
  updateExecutionStep: (stepId, update) => {
    const { currentExecution } = get();
    if (!currentExecution) return;
    
    const updatedSteps = currentExecution.steps.map(step => 
      step.id === stepId ? { ...step, ...update } : step
    );
    
    set({
      currentExecution: {
        ...currentExecution,
        steps: updatedSteps
      }
    });
  },
  
  startStepwiseExecution: async () => {
    const { nodes, selectedKnowledgeBase, keyword, layerPrompts, searchIntensity } = get();
    
    if (!selectedKnowledgeBase || !keyword) {
      return;
    }
    
    // 실행할 노드들 분류
    const workflowNodes = nodes.filter(isWorkflowNode);
    const generationNodes = workflowNodes.filter(n => n.data.layer === LayerType.GENERATION);
    const ensembleNodes = workflowNodes.filter(n => n.data.layer === LayerType.ENSEMBLE);
    const validationNodes = workflowNodes.filter(n => n.data.layer === LayerType.VALIDATION);
    
    if (generationNodes.length === 0 || ensembleNodes.length === 0) {
      return;
    }
    
    // 실행 상태 초기화
    const executionId = `exec_${Date.now()}`;
    const steps: WorkflowExecutionStep[] = [
      { id: 'search', type: 'search', status: 'pending' },
      ...generationNodes.map(node => ({
        id: `gen_${node.id}`,
        type: 'generation' as const,
        status: 'pending' as const,
        node_id: node.id
      })),
      { id: 'ensemble', type: 'ensemble' as const, status: 'pending' as const, node_id: ensembleNodes[0].id },
      ...validationNodes.map(node => ({
        id: `val_${node.id}`,
        type: 'validation' as const,
        status: 'pending' as const,
        node_id: node.id
      }))
    ];
    
    const state = get();
    set({
      currentExecution: {
        id: executionId,
        knowledge_base: state.selectedKnowledgeBase,
        keyword: state.keyword,
        status: 'searching',
        steps,
        context_chunks: [],
        created_at: new Date()
      },
      isExecuting: true
    });
    
    try {
      // 1. 컨텍스트 검색
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          status: 'searching'
        } : null
      }));
      
      get().updateExecutionStep('search', { status: 'running', start_time: new Date() });
      
      const searchResponse = await stepwiseWorkflowAPI.searchContext({
        knowledge_base: selectedKnowledgeBase,
        query: keyword,
        top_k: getTopKByIntensity(searchIntensity, 'basic')  // 검색 강도에 따른 동적 top_k
      });
      
      get().updateExecutionStep('search', { 
        status: 'completed', 
        end_time: new Date(),
        result: searchResponse 
      });
      
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          contextChunks: searchResponse.chunks,
          status: 'generating'
        } : null
      }));
      
      // 2. Generation Layer 실행 (새로운 Layer API 사용)
      const generationResults: string[] = [];
      
      // Generation Layer input 설정 (키워드 기반)
      set(state => ({
        layerInputs: {
          ...state.layerInputs,
          [LayerType.GENERATION]: keyword
        },
        currentExecutingLayer: LayerType.GENERATION
      }));
      
      // Generation Layer 프롬프트가 설정되어 있는지 확인
      if (!layerPrompts[LayerType.GENERATION]) {
        throw new Error('Generation Layer 프롬프트가 설정되지 않았습니다.');
      }
      
      get().updateExecutionStep('generation', { status: 'running', start_time: new Date() });
      
      try {
        // 새로운 executeLayerWithPrompt 사용
        const generationResponse = await get().executeLayerWithPrompt(LayerType.GENERATION);
        
        // Generation Layer는 여러 노드 결과를 합친 전체 결과(forward_data)를 Ensemble로 전달
        if (generationResponse.node_outputs?.forward_data) {
          generationResults.push(generationResponse.node_outputs.forward_data);
          
          // Generation Layer 완료 → Ensemble Layer input 즉시 설정
          set(state => ({
            currentExecution: state.currentExecution ? {
              ...state.currentExecution,
              generationResults: [...generationResults]
            } : null,
            layerInputs: {
              ...state.layerInputs,
              [LayerType.ENSEMBLE]: generationResponse.node_outputs.forward_data
            }
          }));
        } else {
          console.warn('⚠️ Generation Layer에서 forward_data를 찾을 수 없습니다.');
        }
        
        get().updateExecutionStep('generation', { 
          status: 'completed', 
          end_time: new Date(),
          result: generationResponse 
        });
        
        console.log('✅ Generation Layer 완료 - Ensemble Layer 시작 준비');
        
      } catch (error) {
        get().updateExecutionStep('generation', { 
          status: 'error', 
          end_time: new Date(),
          error: error instanceof Error ? error.message : 'Unknown error'
        });
        
        // Generation Layer 실패 시 전체 워크플로우 중단하고 사용자에게 알림
        set(state => ({
          currentExecution: state.currentExecution ? {
            ...state.currentExecution,
            status: 'error',
            error: `Generation Layer 실행 실패: ${error instanceof Error ? error.message : 'Unknown error'}`
          } : null,
          isExecuting: false,
          currentExecutingLayer: null
        }));
        
        console.error('Generation Layer 실행 실패로 워크플로우 중단:', error);
        return; // Generation 실패 시 전체 실행 중단
      }
      
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          status: 'ensembling'
        } : null,
        currentExecutingLayer: LayerType.ENSEMBLE
      }));
      
      // 3. Ensemble Layer 실행 (새로운 Layer API 사용)
      console.log('🚀 Ensemble Layer 시작');
      get().updateExecutionStep('ensemble', { status: 'running', start_time: new Date() });
      
      // Ensemble Layer 프롬프트가 설정되어 있는지 확인
      if (!layerPrompts[LayerType.ENSEMBLE]) {
        throw new Error('Ensemble Layer 프롬프트가 설정되지 않았습니다.');
      }
      
      try {
        // Generation Layer의 결과가 이미 layerInputs[ENSEMBLE]에 설정되어 있음
        const ensembleResponse = await get().executeLayerWithPrompt(LayerType.ENSEMBLE);
        
        get().updateExecutionStep('ensemble', { 
          status: 'completed', 
          end_time: new Date(),
          result: ensembleResponse 
        });
        
        console.log('✅ Ensemble Layer 완료 - Validation Layer 시작 준비');
        
        // Ensemble의 forward_data를 Validation Layer로 전달
        let finalRequirements = '';
        if (ensembleResponse.node_outputs?.forward_data && ensembleResponse.node_outputs.forward_data.trim()) {
          finalRequirements = ensembleResponse.node_outputs.forward_data;
          
          // Ensemble Layer 완료 → Validation Layer input 즉시 설정
          set(state => ({
            layerInputs: {
              ...state.layerInputs,
              [LayerType.VALIDATION]: finalRequirements
            }
          }));
        } else {
          console.warn('⚠️ Ensemble Layer에서 forward_data를 찾을 수 없습니다.');
          // 빈 결과라도 계속 진행
          finalRequirements = '';
        }
        
      } catch (error) {
        get().updateExecutionStep('ensemble', { 
          status: 'error', 
          end_time: new Date(),
          error: error instanceof Error ? error.message : 'Unknown error'
        });
        
        // Ensemble Layer 실패 시 전체 워크플로우 중단하고 사용자에게 알림
        set(state => ({
          currentExecution: state.currentExecution ? {
            ...state.currentExecution,
            status: 'error',
            error: `Ensemble Layer 실행 실패: ${error instanceof Error ? error.message : 'Unknown error'}`
          } : null,
          isExecuting: false,
          currentExecutingLayer: null
        }));
        
        console.error('Ensemble Layer 실행 실패로 워크플로우 중단:', error);
        return; // Ensemble 실패 시 전체 실행 중단
      }
      
      // 4. Validation Layer 실행 (Ensemble 성공 후)
      let finalRequirements = get().layerInputs[LayerType.VALIDATION] || '';
      
      if (validationNodes.length > 0) {
        console.log('🚀 Validation Layer 시작');
        // Validation Layer들을 순차적으로 실행
        for (const node of validationNodes) {
          const stepId = `val_${node.id}`;
          get().updateExecutionStep(stepId, { status: 'running', start_time: new Date() });
          
          try {
            // Validation Layer 프롬프트가 설정되어 있는지 확인
            if (!layerPrompts[LayerType.VALIDATION]) {
              throw new Error('Validation Layer 프롬프트가 설정되지 않았습니다.');
            }
            
            // Validation Layer 실행 (executeLayerWithPrompt에서 자동으로 데이터 흐름 처리됨)
            const validationResponse = await get().executeLayerWithPrompt(LayerType.VALIDATION);
            
            // Validation 결과로 현재 요구사항 업데이트 (node_outputs.forward_data 사용)
            if (validationResponse.node_outputs?.forward_data && validationResponse.node_outputs.forward_data.trim()) {
              finalRequirements = validationResponse.node_outputs.forward_data;
            } else {
              console.warn('⚠️ Validation Layer에서 forward_data를 찾을 수 없습니다.');
            }
            
            get().updateExecutionStep(stepId, { 
              status: 'completed', 
              end_time: new Date(),
              result: validationResponse 
            });
            
          } catch (error) {
            get().updateExecutionStep(stepId, { 
              status: 'error', 
              end_time: new Date(),
              error: error instanceof Error ? error.message : 'Unknown error'
            });
            console.warn(`Validation 노드 ${node.id} 실행 실패, 계속 진행:`, error);
            // Validation 오류는 계속 진행 (선택적 단계)
          }
        }
      }
      
      // 5. 최종 완료 - 모든 Layer 실행 완료
      console.log('🎉 전체 워크플로우 실행 완료');
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          finalResult: finalRequirements,
          status: 'completed'
        } : null,
        isExecuting: false,
        currentExecutingLayer: null,
        result: {
          final_requirements: finalRequirements,
          execution_steps: get().currentExecution?.steps || []
        }
      }));
      
    } catch (error) {
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          status: 'error',
          error: error instanceof Error ? error.message : 'Unknown error'
        } : null,
        isExecuting: false,
        currentExecutingLayer: null
      }));
    }
  },

  // Layer 프롬프트 및 입력 관리 액션들
  setLayerPrompt: (layer: LayerType, prompt: string) => {
    set(state => ({
      layerPrompts: {
        ...state.layerPrompts,
        [layer]: prompt
      }
    }));
  },

  setLayerInput: (layer: LayerType, input: string) => {
    set(state => ({
      layerInputs: {
        ...state.layerInputs,
        [layer]: input
      }
    }));
  },

  executeLayerWithPrompt: async (layer: LayerType): Promise<LayerExecutionResponse | ValidationLayerResponse> => {
    const { layerPrompts, layerInputs, nodes, selectedKnowledgeBase, keyword, searchIntensity, selectedProvider } = get();
    const prompt = layerPrompts[layer];
    const input = layerInputs[layer];

    if (!prompt.trim()) {
      throw new Error('프롬프트를 입력해주세요.');
    }

    // LLM Provider 선택 검증
    if (!selectedProvider) {
      throw new Error('LLM Provider를 선택해주세요.');
    }

    // 현재 실행 중인 Layer 상태 설정
    set({ 
      isExecuting: true,
      currentExecutingLayer: layer 
    });

    try {
      // 해당 레이어의 노드들 찾기
      const layerNodes = nodes.filter(node => 
        isWorkflowNode(node) && node.data.layer === layer
      ) as WorkflowNode[];

      if (layerNodes.length === 0) {
        throw new Error(`${layer} 레이어에 노드가 없습니다.`);
      }

      // Ensemble Layer는 지식 베이스 검색을 skip (context를 사용하지 않음)
      let contextChunks: string[] = [];
      
      if (selectedKnowledgeBase && layer !== LayerType.ENSEMBLE) {
        try {
          // 1. 기본 키워드로 검색
          const searchResponse = await stepwiseWorkflowAPI.searchContext({
            knowledge_base: selectedKnowledgeBase,
            query: keyword,
            top_k: getTopKByIntensity(searchIntensity, 'basic')  // 검색 강도에 따른 동적 top_k
          });
          contextChunks = searchResponse.chunks || [];

          // 2. Generation Layer의 경우 추가 검색
          if (layer === LayerType.GENERATION) {
            // 입력 데이터에서 키워드 추출하여 추가 검색
            const inputKeywords = input.split(/\s+/).filter(word => word.length > 2).slice(0, 3);
            for (const inputKeyword of inputKeywords) {
              if (inputKeyword.trim()) {
                const additionalResponse = await stepwiseWorkflowAPI.searchContext({
                  knowledge_base: selectedKnowledgeBase,
                  query: inputKeyword,
                  top_k: 3
                });
                const newChunks = additionalResponse.chunks || [];
                contextChunks = [...contextChunks, ...newChunks];
              }
            }
          }

          // 3. Validation Layer의 경우 요구사항 기반 확장 검색
          if (layer === LayerType.VALIDATION) {
            // 요구사항에서 추출한 키워드로 추가 검색
            const requirementKeywords = extractKeywordsFromRequirements(input);
            
            const maxKeywords = getMaxKeywordsByIntensity(searchIntensity);
            for (const reqKeyword of requirementKeywords.slice(0, maxKeywords)) { // 검색 강도에 따른 키워드 개수
              if (reqKeyword.trim()) {
                const additionalResponse = await stepwiseWorkflowAPI.searchContext({
                  knowledge_base: selectedKnowledgeBase,
                  query: reqKeyword,
                  top_k: getTopKByIntensity(searchIntensity, 'keyword')  // 검색 강도에 따른 동적 top_k
                });
                const newChunks = additionalResponse.chunks || [];
                contextChunks = [...contextChunks, ...newChunks];
              }
            }
          }

          // 중복 제거 및 검색 강도에 따른 최종 컨텍스트 제한
          const maxContext = getTopKByIntensity(searchIntensity, 'context');
          contextChunks = Array.from(new Set(contextChunks)).slice(0, maxContext);
          
        } catch (error) {
          contextChunks = [];
        }
      }

      // 클라이언트에서 프롬프트 템플릿 처리
      const context = contextChunks.join('\n\n') || '컨텍스트가 제공되지 않았습니다.';
      const processedPrompt = prompt.replace(/{layer_input}/g, input).replace(/{context}/g, context);

      // Layer 프롬프트 API 호출
      const { selectedProvider } = get(); // 현재 선택된 provider 가져오기
      
      const request = {
        layer_type: layer,
        prompt: processedPrompt,  // 클라이언트에서 처리된 완성된 프롬프트 사용
        layer_input: input,
        knowledge_base: selectedKnowledgeBase,
        top_k: getTopKByIntensity(searchIntensity, 'basic'),  // 검색 강도에 따른 동적 top_k
        nodes: layerNodes.map(node => {
          return {
            id: node.id,
            model: node.data.model, // 현재 노드의 모델 이름
            provider: selectedProvider || undefined, // LLMProvider를 string으로 변환
            prompt: processedPrompt,  // 완성된 프롬프트 사용
            layer: node.data.layer,
            position: node.position
          };
        }),
        context_chunks: contextChunks
      };

      const response = await layerPromptAPI.executeLayerPrompt(request);

      // Layer 간 자동 데이터 흐름 처리 및 결과 저장을 동시에 처리
      const isStepwiseExecution = get().currentExecution !== null;
      console.log(`🔄 ${layer} Layer 완료 - 전체 워크플로우 실행 중: ${isStepwiseExecution}`);
      
      if (layer === LayerType.GENERATION) {
        // Generation Layer 완료 → Ensemble Layer input 업데이트
        // 규칙: 서버에서 제공하는 forward_data 사용 (이미 모든 노드 결과가 append됨)
        const nextLayerInput = response.node_outputs?.forward_data || '';
        
        // layerResults와 layerInputs를 동시에 업데이트
        set(state => ({
          layerResults: {
            ...state.layerResults,
            [layer]: response
          },
          layerInputs: nextLayerInput.trim() ? {
            ...state.layerInputs,
            [LayerType.ENSEMBLE]: nextLayerInput
          } : state.layerInputs,
          // 전체 워크플로우 실행 중이 아닐 때만 isExecuting과 currentExecutingLayer를 false/null로 설정
          isExecuting: isStepwiseExecution,
          currentExecutingLayer: isStepwiseExecution ? state.currentExecutingLayer : null
        }));
      } else if (layer === LayerType.ENSEMBLE) {
        // Ensemble Layer 완료 → Validation Layer input 업데이트
        // 새로운 구조: node_outputs.forward_data 사용
        const ensembleResult = response.node_outputs?.forward_data || '';
        
        // layerResults와 layerInputs를 동시에 업데이트
        set(state => ({
          layerResults: {
            ...state.layerResults,
            [layer]: response
          },
          layerInputs: ensembleResult.trim() ? {
            ...state.layerInputs,
            [LayerType.VALIDATION]: ensembleResult
          } : state.layerInputs,
          // 전체 워크플로우 실행 중이 아닐 때만 isExecuting과 currentExecutingLayer를 false/null로 설정
          isExecuting: isStepwiseExecution,
          currentExecutingLayer: isStepwiseExecution ? state.currentExecutingLayer : null
        }));
        
        if (!ensembleResult.trim()) {
          console.warn('⚠️ Ensemble Layer에서 forward_data가 비어있습니다.');
        }
          console.log('� Ensemble final_result를 Validation Layer input으로 설정:', ensembleResult.substring(0, 100) + '...');
        // 제거됨
        // 제거됨
        // 제거됨
        // 제거됨
      } else if (layer === LayerType.VALIDATION) {
        // 규칙: Validation Layer 노드 실행 후 해당 노드의 forward_data가 다음 Validation 노드의 layer_input으로 업데이트
        // 새로운 구조: node_outputs.forward_data 사용
        const validationResult = response.node_outputs?.forward_data || '';
        
        // layerResults와 layerInputs를 동시에 업데이트
        set(state => ({
          layerResults: {
            ...state.layerResults,
            [layer]: response
          },
          layerInputs: validationResult.trim() ? {
            ...state.layerInputs,
            [LayerType.VALIDATION]: validationResult
          } : state.layerInputs,
          // 전체 워크플로우 실행 중이 아닐 때만 isExecuting과 currentExecutingLayer를 false/null로 설정
          isExecuting: isStepwiseExecution,
          ...(isStepwiseExecution ? {} : { currentExecutingLayer: null })
        }));
      } else {
        // Validation Layer 및 다른 Layer들은 기본 처리
        set(state => ({
          layerResults: {
            ...state.layerResults,
            [layer]: response
          },
          // 전체 워크플로우 실행 중이 아닐 때만 isExecuting과 currentExecutingLayer를 false/null로 설정
          isExecuting: isStepwiseExecution,
          currentExecutingLayer: isStepwiseExecution ? state.currentExecutingLayer : null
        }));
      }

      return response;
    } catch (error) {
      console.error(`❌ ${layer} Layer 실행 중 오류:`, error);
      
      // 전체 워크플로우 실행 중이 아닐 때만 isExecuting과 currentExecutingLayer를 false/null로 설정
      const isStepwiseExecution = get().currentExecution !== null;
      set({ 
        isExecuting: isStepwiseExecution,
        currentExecutingLayer: isStepwiseExecution ? get().currentExecutingLayer : null
      });
      throw error;
    }
  },

  // 기본 워크플로우 초기화 (모델 정보 포함)
  initializeDefaultWorkflow: async () => {
    try {
      // 1. 기본 provider를 Google로 설정
      const defaultProvider = LLMProvider.GOOGLE;
      set({ selectedProvider: defaultProvider });
      
      // 2. Provider의 모델 목록 로드
      const providerModels = await get().loadProviderModels(defaultProvider);
      set({ providerModels });
      
      if (providerModels.length === 0) {
        console.warn(`⚠️ ${defaultProvider} 프로바이더에서 사용 가능한 모델이 없습니다.`);
        return;
      }
      
      // 3. 기본 모델 선택
      const defaultModelValue = get().getDefaultModelForProvider(defaultProvider);
      const defaultModel = providerModels.find(model => model.id === defaultModelValue);
      const selectedModel = defaultModel || providerModels[0];
      
      // 4. 모든 워크플로우 노드에 기본 모델 적용
      const { nodes } = get();
      const workflowNodes = nodes.filter(isWorkflowNode);
      
      const updatedNodes = workflowNodes.map(node => {
        return {
          ...node,
          data: {
            ...node.data,
            model: selectedModel.id,
            label: selectedModel.name
          }
        };
      });
      
      // 5. 플레이스홀더 노드들도 유지
      const placeholderNodes = nodes.filter(isPlaceholderNode);
      const allNodes = [...updatedNodes, ...placeholderNodes];
      
      set({ nodes: allNodes });
      
      // 6. placeholder 노드들 업데이트
      setTimeout(() => {
        get().updatePlaceholderNodes();
      }, 100);
      
    } catch (error) {
      console.error('❌ 기본 워크플로우 초기화 실패:', error);
    }
  },

  // Helper function to get default model for provider
  getDefaultModelForProvider: (provider: LLMProvider): string => {
    switch (provider) {
      case LLMProvider.PERPLEXITY:
        return 'sonar-pro';
      case LLMProvider.GOOGLE:
        return 'gemini-2.0-flash';
      case LLMProvider.OPENAI:
        return 'gpt-4-turbo';
      default:
        return 'gpt-4-turbo';
    }
  },

  // LLM Provider 관련 액션들
  setSelectedProvider: async (provider: LLMProvider | null) => {
    const prevProvider = get().selectedProvider;
    set({ selectedProvider: provider });
    
    if (provider && provider !== prevProvider) {
      // Provider가 변경된 경우 모델 목록을 미리 로드하고 상태에 저장
      const models = await get().loadProviderModels(provider);
      set({ providerModels: models });
      
      // 모든 노드의 모델을 해당 Provider의 기본 모델로 변경
      await get().updateAllNodesModelByProvider(provider);
    } else if (!provider) {
      set({ providerModels: [] });
    }
  },

  loadProviderModels: async (provider: LLMProvider): Promise<AvailableModel[]> => {
    try {
      const models = await workflowAPI.getProviderModels(provider);
      return models;
    } catch (error) {
      console.error(`${provider} 모델 목록 로드 실패:`, error);
      return [];
    }
  },

  updateAllNodesModelByProvider: async (provider: LLMProvider) => {
    const { nodes, providerModels } = get();
    const defaultModelValue = get().getDefaultModelForProvider(provider);
    
    // Provider 변경 시 모든 노드를 해당 provider의 기본 모델로 업데이트
    
    // 이미 로드된 모델 목록 사용 (없으면 다시 로드)
    let availableModels = providerModels;
    if (availableModels.length === 0) {
      // Provider 모델 목록이 없으면 다시 로드
      availableModels = await get().loadProviderModels(provider);
      set({ providerModels: availableModels });
    }
    
    // 사용 가능한 모델 목록 확인
    
    // 기본 모델 찾기
    const defaultModel = availableModels.find(model => model.id === defaultModelValue);
    const selectedModel = defaultModel || availableModels[0];
    
    // 기본 모델 선택 완료
    
    if (!selectedModel) {
      console.warn(`Provider ${provider}에 사용 가능한 모델이 없습니다.`);
      return;
    }

    const updatedNodes = nodes.map(node => {
      if (isWorkflowNode(node)) {
        // 노드 모델 업데이트
        return {
          ...node,
          data: {
            ...node.data,
            model: selectedModel.id,
            label: selectedModel.name
          }
        };
      }
      return node;
    });
    
    set({ nodes: updatedNodes });
    // 노드 모델 업데이트 완료
  },

  // 구조화된 출력 파싱 함수 - 모든 Layer에서 사용하는 통합된 파싱 로직
  extractStructuredContent: (content: any): { general_output: string; forward_data: string } => {
    // 이미 올바른 구조의 객체인 경우
    if (content && typeof content === 'object' && (content.general_output || content.forward_data)) {
      return {
        general_output: content.general_output || "",
        forward_data: content.forward_data || ""
      };
    }

    // 문자열인 경우 파싱 시도
    if (typeof content === 'string') {
      return get().parseStructuredOutput(content);
    }

    // 객체이지만 다른 구조인 경우 문자열로 변환 후 파싱
    if (content && typeof content === 'object') {
      const jsonString = JSON.stringify(content);
      return get().parseStructuredOutput(jsonString);
    }

    // 기본값 반환
    return { general_output: String(content || ""), forward_data: "" };
  },

  parseStructuredOutput: (content: string): { general_output: string; forward_data: string } => {
    if (!content || !content.trim()) {
      return { general_output: "", forward_data: "" };
    }

    try {
      // 0. 이미 파싱된 객체인지 확인
      if (typeof content === 'object') {
        const obj = content as any;
        const general_output = obj.general_output || "";
        const forward_data = obj.forward_data || "";
        return { general_output, forward_data };
      }

      // 1. 강화된 JSON 코드 블록 추출 - 다양한 패턴을 모두 시도
      const codeBlockPatterns = [
        // ```json으로 시작하는 블록 (대소문자 구분 없음) - 우선순위 1
        /```(?:json|JSON)\s*([\s\S]*?)\s*```/gi,
        // ``` 일반 코드 블록 - 우선순위 2  
        /```\s*([\s\S]*?)\s*```/gi,
        // 백틱 하나로 감싼 경우 - 우선순위 3
        /`([^`]*?)`/gi
      ];
      
      for (const pattern of codeBlockPatterns) {
        pattern.lastIndex = 0;
        const matches = Array.from(content.matchAll(pattern));
        
        for (const match of matches) {
          let jsonStr = match[1].trim();
          
          // 빈 문자열 스킵
          if (!jsonStr) continue;
          
          try {
            // JSON 문자열 정리 - 매우 강력한 정리
            jsonStr = jsonStr
              .replace(/^\s*json\s*/i, '') // 시작 부분의 "json" 키워드 제거
              .replace(/\s*json\s*$/i, '') // 끝 부분의 "json" 키워드 제거
              .replace(/^\s*[\r\n]+/gm, '') // 시작 공백/줄바꿈 제거
              .replace(/[\r\n]+\s*$/gm, '') // 끝 공백/줄바꿈 제거
              .replace(/\\\\\\/g, '\\') // 삼중 백슬래시를 단일 백슬래시로
              .replace(/\\\\/g, '\\') // 이중 백슬래시를 단일 백슬래시로
              .trim();
            
            // "json" 단어가 단독으로 있는 라인 제거
            jsonStr = jsonStr.replace(/^\s*json\s*$/gmi, '');
            
            // JSON 객체의 시작과 끝을 정확히 찾기
            const firstBrace = jsonStr.indexOf('{');
            const lastBrace = jsonStr.lastIndexOf('}');
            
            if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
              jsonStr = jsonStr.substring(firstBrace, lastBrace + 1);
              
              // 마지막 콤마 제거 (잘못된 JSON 수정)
              jsonStr = jsonStr.replace(/,(\s*[}\]])/g, '$1');
              
              const parsed = JSON.parse(jsonStr);
              
              // general_output과 forward_data가 있는지 확인  
              if (parsed.general_output !== undefined || parsed.forward_data !== undefined) {
                let general_output = parsed.general_output || parsed.generalOutput || "";
                let forward_data = parsed.forward_data || "";
                
                // \\n을 실제 줄바꿈으로 변환하고 이스케이프된 따옴표 처리
                if (typeof general_output === 'string') {
                  general_output = general_output
                    .replace(/\\n/g, "\n")
                    .replace(/\\"/g, '"')
                    .replace(/\\\\/g, '\\'); // 백슬래시 정리
                }
                if (typeof forward_data === 'string') {
                  forward_data = forward_data
                    .replace(/\\n/g, "\n")
                    .replace(/\\"/g, '"')
                    .replace(/\\\\/g, '\\'); // 백슬래시 정리
                }
                
                return { general_output, forward_data };
              }
            }
          } catch (jsonError) {
            continue; // 다음 패턴 시도
          }
        }
      }
      
      // 2. 전체 내용이 JSON인지 확인 (중괄호로 시작하고 끝나는 경우)
      let trimmedContent = content.trim();
      
      // "json" 키워드가 있으면 제거하고 추가 정리
      trimmedContent = trimmedContent
        .replace(/^\s*json\s*/i, '') // 시작 부분의 "json" 키워드 제거
        .replace(/\s*json\s*$/i, '') // 끝 부분의 "json" 키워드 제거
        .replace(/^\s*json\s*$/gmi, '') // "json" 단어가 단독으로 있는 라인 제거
        .replace(/\\\\\\/g, '\\') // 삼중 백슬래시 정리
        .replace(/\\\\/g, '\\') // 이중 백슬래시 정리
        .trim();
      
      if (trimmedContent.startsWith('{') && trimmedContent.endsWith('}')) {
        try {
          // 마지막 콤마 제거
          trimmedContent = trimmedContent.replace(/,(\s*[}\]])/g, '$1');
          
          const parsed = JSON.parse(trimmedContent);
          
          let general_output = parsed.general_output || parsed.generalOutput || "";
          let forward_data = parsed.forward_data || "";
          
          // \\n을 실제 줄바꿈으로 변환하고 이스케이프된 따옴표 처리
          if (typeof general_output === 'string') {
            general_output = general_output
              .replace(/\\n/g, "\n")
              .replace(/\\"/g, '"')
              .replace(/\\\\/g, '\\');
          }
          if (typeof forward_data === 'string') {
            forward_data = forward_data
              .replace(/\\n/g, "\n")
              .replace(/\\"/g, '"')
              .replace(/\\\\/g, '\\');
          }
          
          return { general_output, forward_data };
        } catch (jsonError) {
          // JSON 파싱 실패
        }
      }
      
      // 3. 정규식으로 키-값 쌍 직접 추출 (더 강력한 패턴)
      // 멀티라인 및 이스케이프된 문자를 고려한 정규식
      const generalOutputMatch = content.match(/"general_output"\s*:\s*"((?:[^"\\]|\\[\s\S])*)"/s);
      const forwardDataMatch = content.match(/"forward_data"\s*:\s*"((?:[^"\\]|\\[\s\S])*)"/s);
      
      if (generalOutputMatch || forwardDataMatch) {
        let general_output = generalOutputMatch ? 
          generalOutputMatch[1]
            .replace(/\\n/g, "\n")
            .replace(/\\"/g, '"')
            .replace(/\\\\/g, '\\') : "";
        let forward_data = forwardDataMatch ? 
          forwardDataMatch[1]
            .replace(/\\n/g, "\n")
            .replace(/\\"/g, '"')
            .replace(/\\\\/g, '\\') : "";
        
        return { general_output, forward_data };
      }
      
      // 4. 아주 관대한 JSON 파싱 시도 - 중괄호 사이의 모든 내용
      const braceMatch = content.match(/\{[\s\S]*\}/);
      if (braceMatch) {
        try {
          let jsonContent = braceMatch[0];
          
          // 모든 가능한 수정 시도
          jsonContent = jsonContent
            .replace(/,(\s*[}\]])/g, '$1') // 마지막 콤마 제거
            .replace(/\\\\\\/g, '\\') // 삼중 백슬래시 정리
            .replace(/([^\\])\\([^"\\nrtbf/])/g, '$1\\\\$2'); // 잘못된 이스케이프 수정
          
          const parsed = JSON.parse(jsonContent);
          
          if (parsed.general_output !== undefined || parsed.forward_data !== undefined) {
            let general_output = parsed.general_output || "";
            let forward_data = parsed.forward_data || "";
            
            if (typeof general_output === 'string') {
              general_output = general_output
                .replace(/\\n/g, "\n")
                .replace(/\\"/g, '"')
                .replace(/\\\\/g, '\\');
            }
            if (typeof forward_data === 'string') {
              forward_data = forward_data
                .replace(/\\n/g, "\n")
                .replace(/\\"/g, '"')
                .replace(/\\\\/g, '\\');
            }
            
            return { general_output, forward_data };
          }
        } catch (jsonError) {
          // 마지막 시도도 실패
        }
      }
      
      // 5. 모든 파싱 실패시 전체 내용을 general_output으로 처리
      return { general_output: content, forward_data: "" };
      
    } catch (error) {
      return { general_output: content, forward_data: "" };
    }
  },
}));

// ✅ 기본 워크플로우는 App.tsx에서 useEffect로 초기화됨 (중복 방지)
