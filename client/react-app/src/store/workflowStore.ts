import { create } from 'zustand';
import { WorkflowNode, PlaceholderNode, WorkflowNodeData, AnyWorkflowNode, LayerType, WorkflowExecution, WorkflowExecutionStep, LayerExecutionResponse, ValidationLayerResponse, NodeOutput, SearchIntensity, LLMProvider, AvailableModel } from '../types';
import { stepwiseWorkflowAPI, layerWorkflowAPI, layerPromptAPI, workflowAPI } from '../services/api';

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
  
  console.log('키워드 추출 대상 요구사항:', requirements.substring(0, 300) + '...');
  
  // 마크다운 테이블에서 요구사항 텍스트 추출
  const tableRows = requirements.match(/\|\s*[^|]*\s*\|\s*([^|]+)\s*\|/g);
  if (!tableRows) {
    console.log('테이블 형식을 찾을 수 없음, 전체 텍스트에서 키워드 추출');
    // 테이블이 없는 경우 전체 텍스트에서 추출
    return extractKeywordsFromText(requirements);
  }
  
  const keywords: string[] = [];
  
  tableRows.forEach(row => {
    // 테이블 행에서 요구사항 내용 추출 (두 번째 컬럼)
    const match = row.match(/\|\s*[^|]*\s*\|\s*([^|]+)\s*\|/);
    if (match && match[1]) {
      const requirement = match[1].trim();
      
      // 너무 짧거나 헤더인 경우 제외
      if (requirement.length > 10 && !requirement.includes('요구사항') && !requirement.includes('---')) {
        // 1. 기본 키워드 추출
        const words = requirement.split(/\s+/)
          .filter(word => word.length > 2)
          .filter(word => !/^(을|를|이|가|의|에|에서|로|으로|와|과|도|만|처럼|해야|해야함|한다|된다)$/.test(word)) // 조사 및 어미 제외
          .slice(0, 4); // 처음 4개 단어
        
        keywords.push(...words);
        
        // 2. 기술 용어 추출 (영문/숫자 포함)
        const techTerms = requirement.match(/[A-Za-z]+\d*|[가-힣]*[A-Za-z]+[가-힣]*|\d+[가-힣]+/g) || [];
        keywords.push(...techTerms.filter(term => term.length > 1));
      }
    }
  });
  
  // 중복 제거 및 상위 8개 반환 (더 많은 키워드로 검색 강화)
  const uniqueKeywords = Array.from(new Set(keywords)).slice(0, 8);
  console.log('테이블에서 추출된 키워드:', uniqueKeywords);
  return uniqueKeywords;
}

// 텍스트에서 직접 키워드 추출하는 보조 함수
function extractKeywordsFromText(text: string): string[] {
  const keywords: string[] = [];
  
  // 1. 요구사항 ID 패턴 (REQ-001, R1.1, F1 등)
  const reqIds = text.match(/REQ[-_]\d+|R\d+\.\d+|F\d+|[A-Z]+\d+/gi) || [];
  keywords.push(...reqIds);
  
  // 2. 기능 동사 추출
  const functionVerbs = text.match(/\b(지원|제공|수행|처리|관리|생성|삭제|수정|조회|검색|저장|로드|전송|수신|연결|설정|구성|실행|종료|시작|중지|확인|검증|승인|거부)\w*/gi) || [];
  keywords.push(...functionVerbs);
  
  // 3. 중요 명사 추출 (길이 3 이상)
  const nouns = text.match(/[가-힣]{3,}|[A-Za-z]{3,}/g) || [];
  keywords.push(...nouns.filter(noun => !/^(요구사항|기능|시스템|사용자|해야|한다|된다)$/.test(noun)));
  
  return Array.from(new Set(keywords)).slice(0, 6);
}

// 검색 강도에 따른 top_k 값 계산 함수
function getTopKByIntensity(intensity: SearchIntensity, type: 'basic' | 'keyword' | 'context'): number {
  const configs = {
    [SearchIntensity.LOW]: {
      basic: 5,
      keyword: 10,
      context: 15
    },
    [SearchIntensity.MEDIUM]: {
      basic: 15,
      keyword: 20,
      context: 25
    },
    [SearchIntensity.HIGH]: {
      basic: 25,
      keyword: 30,
      context: 35
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
    generation: string;
    ensemble: string;
    validation: string;
  };
  layerInputs: {
    generation: string;
    ensemble: string;
    validation: string;
  };
  layerResults: {
    generation: any;
    ensemble: any;
    validation: any;
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
  
  // 새로운 Layer별 워크플로우 액션들
  startLayerExecution: () => Promise<void>;
  executeGenerationLayer: (contextChunks: string[]) => Promise<LayerExecutionResponse>;
  executeEnsembleLayer: (generationResult: string, contextChunks: string[]) => Promise<LayerExecutionResponse>;
  executeValidationLayer: (ensembleResult: string, contextChunks: string[]) => Promise<ValidationLayerResponse>;
  
  // Layer 프롬프트 및 입력 관리 액션들
  setLayerPrompt: (layer: LayerType, prompt: string) => void;
  setLayerInput: (layer: LayerType, input: string) => void;
  executeLayerWithPrompt: (layer: LayerType) => Promise<LayerExecutionResponse | ValidationLayerResponse>;
  clearLayerResult: (layer: LayerType) => void;
}

// 레이어별 고정 위치 설정
const LAYER_POSITIONS = {
  [LayerType.GENERATION]: { baseX: 100, baseY: 100, spacing: 200 },
  [LayerType.ENSEMBLE]: { baseX: 100, baseY: 300, spacing: 0 },
  [LayerType.VALIDATION]: { baseX: 100, baseY: 500, spacing: 200 }
};

// ... createDefaultNode, createPlaceholderNode, getDefaultPrompt, getModelLabel 함수들은 기존과 동일 ...

const createDefaultNode = (layer: LayerType, position: { x: number; y: number }): WorkflowNode => {
  const id = `${layer}_${Date.now()}`;
  
  return {
    id,
    type: 'customNode',
    position,
    data: {
      id,
      model_index: 0, // 첫 번째 사용 가능한 모델 (인덱스 기반)
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
  layerPrompts: {
    [LayerType.GENERATION]: `당신은 요구사항 분석 전문가입니다. 원본 문서로부터 키워드 '{layer_input}'에 대한 상세하고 구체적인 요구사항을 최대한 많이 생성해주세요.

**컨텍스트 (지식 베이스에서 검색된 내용):**
{context}

**입력 데이터:**
{layer_input}

**작업 지침:**
1. 제공된 컨텍스트를 바탕으로 구체적이고 측정 가능한 요구사항을 생성하세요
2. 각 요구사항은 명확해야 하며 최대한 상세하게 작성합니다
3. 반드시 컨텍스트 내용 안에서만 요구사항을 도출하세요
4. 컨텍스트에 명시된 내용에서 과하게 변형하지 마세요
5. 문서 내에서 해당 요구사항의 근거가 되는 문장들을 상세하게 명시하세요
6. 문서 내에서 해당 요구사항의 근거를 다시 확인할 수 있는 페이지 번호 또는 섹션 번호(ex) 5.1.8)를 최대한 명시하세요
6. 요구사항 ID는 REQ-001부터 순차적으로 부여하세요
7. 요구사항은 영어로 작성하세요

**필수 출력 형식 (마크다운 표):**
| ID | 요구사항 (Requirement) | 근거(reference) | 상세 설명 (Notes) |
|---|---|---|---|
| REQ-001 | [구체적인 요구사항 내용] | [근거 내용과 위치] | [추가적인 설명이나 조건] |
| REQ-002 | ... | ... | ... |

**주의사항:**
- 반드시 위의 표 형식을 정확히 따라주세요
- 각 요구사항은 두 줄 이내로 간결하게 작성하세요
- 페이지 번호 또는 섹션 번호를 구체적으로 명시하세요`,

    [LayerType.ENSEMBLE]: `당신은 여러 지식을 통합하는 기술의 전문가입니다. 다음 여러 모델에서 생성된 요구사항들을 통합하여 하나의 일관되고 완성도 높은 요구사항 표를 만들어주세요.

**입력 결과들 (여러 모델의 요구사항 생성 결과):**
{layer_input}

**통합 작업 지침:**
1. **중복 제거**: 같은 내용을 담고 있는 요구사항들을 식별하고 중복된 내용이 있다면 구체적인 것을 남기고 덜 구체적인 것을 제거하세요
2. **일관성 확보**: 요구사항 ID 체계를 통일하고 일관된 형식으로 정리하세요
3. **우선순위**: 중요도와 우선순위를 고려하여 정렬하세요
4. **수정 금지**: 내용을 수정하지 말고 항목 제거만 하세요

**1단계: 제거된 항목 분석**
| 제거된 ID | 원래 요구사항 | 제거 사유 |
|---|---|---|
| [원본 ID] | [제거된 요구사항 내용] | [중복/모호함/부정확 등] |

**통합 과정 요약:**
- 총 입력 요구사항 수: [필터링 전 요구사항 개수]
- 최종 통합 요구사항 수: [필터링 후 요구사항 개수] 
- 제거된 항목 수: [제거된 항목 개수]

**2단계: 최종 통합된 요구사항 목록 (핵심 결과)**

| ID | 요구사항 (Requirement) | 근거(reference) | 상세 설명 (Notes) |
|---|---|---|---|
| REQ-001 | [구체적인 요구사항 내용] | [원문 내용과 위치] | [추가적인 설명이나 조건] |
| REQ-002 | ... | ... | ... |`,

    [LayerType.VALIDATION]: `당신은 기술 문서 검증 전문가입니다. 다음 요구사항 표를 지식 베이스 내용을 바탕으로 엄격하게 검증하고 필터링해주세요. 목적은 내용 수정이 아닌 잘못된 요구사항의 완전 제거입니다.

**검증할 요구사항:**
{layer_input}

**지식 베이스 컨텍스트:**
{context}

**필터링 기준 (반드시 준수):**
1. **사실 정확성**: 지식 베이스 내용과 모순되거나 잘못된 정보가 포함된 요구사항은 제거
2. **내용 일치성**: 요구사항의 근거(reference)를 지식 베이스 컨텍스트 내에서 찾을 수 없는 경우 제거
3. **중복 제거**: 같은 내용을 담고 있는 요구사항은 컨텍스트와의 유사성이 높은 것만 남기고 유사성이 낮은 것은 제거
4. **구체성**: 모호하거나 측정 불가능한 요구사항에는 '확인 필요' 표시

**작업 지침:**
- 내용을 수정하지 말고 항목 제거만 하세요
- 필터링 기준에 완전히 부합하는 요구사항만 통과시키세요
- 의심스러운 요구사항에는 모두 '확인 필요' 표시를 하세요
- 출력 시 영어를 한글로 번역해주세요

**필수 출력 형식 (마크다운 표):**
| ID | 요구사항 (Requirement) | 근거(reference) | 상세 설명 (Notes) | 확인 필요
|---|---|---|---|---|
| REQ-001 | [통합된 요구사항 내용] | [원문 내용과 위치] | [통합 과정에서 추가된 설명] | [확인 필요 여부] |
| REQ-002 | ... | ... | ... | ... |

**제거된 요구사항 목록:**
| ID | 요구사항 (Requirement) | 제거 사유 (Reason) |
|---|---|---|
| REQ-XXX | [제거된 요구사항] | [구체적인 제거 사유] |
| REQ-YYY | ... | ... |

**필터링 결과 요약:**
- 전체 요구사항: [총 개수]개
- 통과한 요구사항: [통과 개수]개  
- 제거된 요구사항: [제거 개수]개
- 통과율: [통과율]%`
  },
  layerInputs: {
    [LayerType.GENERATION]: '',
    [LayerType.ENSEMBLE]: '',
    [LayerType.VALIDATION]: ''
  },
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
      console.log('Generation Layer 최대 개수 도달');
      return;
    }
    if (layer === LayerType.VALIDATION && realNodes.length >= 3) {
      console.log('Validation Layer 최대 개수 도달');
      return;
    }
    if (layer === LayerType.ENSEMBLE) {
      console.log('Ensemble Layer는 추가 불가');
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
      console.log('유효하지 않은 노드:', nodeId);
      return;
    }
    
    if (node.data.layer === LayerType.ENSEMBLE) {
      console.log('Ensemble Layer는 제거할 수 없습니다.');
      return;
    }
    
    const layerNodes = nodes.filter(isWorkflowNode)
      .filter(n => n.data.layer === node.data.layer)
      .sort((a, b) => a.position.x - b.position.x);
      
    if (layerNodes.length <= 1) {
      console.log('마지막 노드는 제거할 수 없습니다.');
      return;
    }
    
    // 마지막 노드인지 확인
    const lastNode = layerNodes[layerNodes.length - 1];
    if (lastNode.id !== nodeId) {
      console.log('마지막 노드만 제거할 수 있습니다.');
      return;
    }
    
    const filteredNodes = nodes.filter(n => n.id !== nodeId);
    set({ nodes: filteredNodes });
    
    console.log('마지막 노드 제거 완료:', nodeId);
    
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
    console.log('워크플로우 구성이 뷰포트 정보와 Provider와 함께 저장되었습니다:', {
      viewport: currentViewport,
      selectedProvider,
      nodeCount: nodes.length
    });
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
          console.log(`Provider가 ${currentProvider}에서 ${savedProvider}로 변경되어 노드 모델을 업데이트합니다.`);
          await get().updateAllNodesModelByProvider(savedProvider);
        }
        
        setTimeout(() => {
          get().updatePlaceholderNodes();
        }, 100);
        
        return true;
      } else {
        console.log('저장된 워크플로우가 없습니다.');
        return false;
      }
    } catch (error) {
      console.error('워크플로우 복원 중 오류:', error);
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
    
    console.log('워크플로우가 JSON 파일로 Export되었습니다.');
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
      console.error('지식 베이스 또는 키워드가 선택되지 않았습니다.');
      return;
    }
    
    // 실행할 노드들 분류
    const workflowNodes = nodes.filter(isWorkflowNode);
    const generationNodes = workflowNodes.filter(n => n.data.layer === LayerType.GENERATION);
    const ensembleNodes = workflowNodes.filter(n => n.data.layer === LayerType.ENSEMBLE);
    const validationNodes = workflowNodes.filter(n => n.data.layer === LayerType.VALIDATION);
    
    if (generationNodes.length === 0 || ensembleNodes.length === 0) {
      console.error('Generation 및 Ensemble 노드가 필요합니다.');
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
        
        // Generation Layer는 여러 노드 결과를 합친 전체 결과(combined_result)를 Ensemble로 전달
        if (generationResponse.combined_result) {
          generationResults.push(generationResponse.combined_result);
          console.log('Generation Layer 완료. combined_result 길이:', generationResponse.combined_result.length);
        } else if (generationResponse.outputs && generationResponse.outputs.length > 0) {
          // fallback: 기존 방식
          const combinedResults = generationResponse.outputs
            .map((output: NodeOutput) => `## ${output.model_type}\n${output.requirements}`)
            .join('\n\n');
          generationResults.push(combinedResults);
          console.log('Generation Layer 완료 (fallback). 결합 결과 길이:', combinedResults.length);
        }
        
        get().updateExecutionStep('generation', { 
          status: 'completed', 
          end_time: new Date(),
          result: generationResponse 
        });
        
      } catch (error) {
        get().updateExecutionStep('generation', { 
          status: 'error', 
          end_time: new Date(),
          error: error instanceof Error ? error.message : 'Unknown error'
        });
        throw error; // Generation 실패 시 전체 실행 중단
      }
      
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          generationResults,
          status: 'ensembling'
        } : null,
        currentExecutingLayer: LayerType.ENSEMBLE
      }));
      
      // 3. Ensemble Layer 실행 (새로운 Layer API 사용)
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
        
        // Ensemble의 최종 결과(final_result)를 현재 요구사항으로 설정
        let currentRequirements = '';
        if ('final_result' in ensembleResponse && ensembleResponse.final_result && typeof ensembleResponse.final_result === 'string') {
          currentRequirements = ensembleResponse.final_result;
          console.log('Ensemble Layer final_result 사용:', currentRequirements.substring(0, 100) + '...');
        } else if ('combined_result' in ensembleResponse && ensembleResponse.combined_result && typeof ensembleResponse.combined_result === 'string') {
          currentRequirements = ensembleResponse.combined_result;
          console.log('Ensemble Layer combined_result 사용 (fallback):', currentRequirements.substring(0, 100) + '...');
        } else {
          console.warn('Ensemble Layer에서 유효한 결과를 찾을 수 없습니다.');
          throw new Error('Ensemble Layer 결과가 비어있습니다.');
        }
        
        set(state => ({
          currentExecution: state.currentExecution ? {
            ...state.currentExecution,
            ensembleResult: currentRequirements,
            status: 'validating'
          } : null,
          currentExecutingLayer: LayerType.VALIDATION
        }));
        
        // 4. Validation Layer 실행 (새로운 Layer API 사용)
        for (const node of validationNodes) {
          const stepId = `val_${node.id}`;
          get().updateExecutionStep(stepId, { status: 'running', start_time: new Date() });
          
          try {
            // Validation Layer 프롬프트가 설정되어 있는지 확인
            if (!layerPrompts[LayerType.VALIDATION]) {
              throw new Error('Validation Layer 프롬프트가 설정되지 않았습니다.');
            }
            
            // 현재 요구사항을 Validation Layer input으로 설정
            set(state => ({
              layerInputs: {
                ...state.layerInputs,
                [LayerType.VALIDATION]: currentRequirements
              }
            }));
            
            // 새로운 executeLayerWithPrompt 사용
            const validationResponse = await get().executeLayerWithPrompt(LayerType.VALIDATION);
            
            // Validation 결과로 현재 요구사항 업데이트
            if ('final_result' in validationResponse && validationResponse.final_result && typeof validationResponse.final_result === 'string') {
              currentRequirements = validationResponse.final_result;
              console.log('Validation Layer final_result로 요구사항 업데이트:', currentRequirements.substring(0, 100) + '...');
            } else if ('combined_result' in validationResponse && validationResponse.combined_result && typeof validationResponse.combined_result === 'string') {
              currentRequirements = validationResponse.combined_result;
              console.log('Validation Layer combined_result로 요구사항 업데이트 (fallback):', currentRequirements.substring(0, 100) + '...');
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
            console.warn(`Validation 노드 ${node.id} 실행 실패:`, error);
          }
        }
        
        // 최종 완료
        set(state => ({
          currentExecution: state.currentExecution ? {
            ...state.currentExecution,
            finalResult: currentRequirements,
            status: 'completed'
          } : null,
          isExecuting: false,
          currentExecutingLayer: null,
          result: {
            final_requirements: currentRequirements,
            execution_steps: get().currentExecution?.steps || []
          }
        }));
        
      } catch (error) {
        get().updateExecutionStep('ensemble', { 
          status: 'error', 
          end_time: new Date(),
          error: error instanceof Error ? error.message : 'Unknown error'
        });
        throw error; // Ensemble 실패 시 전체 실행 중단
      }
      
    } catch (error) {
      console.error('워크플로우 실행 중 오류:', error);
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

  // Layer별 워크플로우 액션들
  startLayerExecution: async () => {
    const state = get();
    if (state.isExecuting) return;

    // 새로운 layer 기반 실행 초기화
    set({
      isExecuting: true,
      currentExecution: {
        id: `layer_${Date.now()}`,
        knowledge_base: state.selectedKnowledgeBase,
        keyword: state.keyword,
        status: 'searching',
        steps: [],
        created_at: new Date()
      }
    });
  },

  executeGenerationLayer: async (contextChunks: string[]): Promise<LayerExecutionResponse> => {
    try {
      const state = get();
      const generationNodes = state.nodes
        .filter(isWorkflowNode)
        .filter(node => node.data.layer === LayerType.GENERATION)
        .map(node => ({
          id: node.id,
          model_type: node.data.model_type,
          prompt: state.layerPrompts[LayerType.GENERATION],
          layer: node.data.layer,
          position: node.position
        }));

      const response = await layerWorkflowAPI.executeGenerationLayer({
        knowledge_base: state.selectedKnowledgeBase,
        layer_input: state.keyword,
        nodes: generationNodes,
        context_chunks: contextChunks
      });
      
      // 실행 상태 업데이트
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          status: 'generating',
          steps: [...state.currentExecution.steps, {
            id: 'generation_layer',
            type: 'generation',
            status: 'completed',
            result: response.combined_result,
            start_time: new Date(),
            end_time: new Date()
          }],
          generation_result: response
        } : null
      }));

      return response;
    } catch (error) {
      console.error('Generation Layer 실행 중 오류:', error);
      throw error;
    }
  },

  executeEnsembleLayer: async (generationResult: string, contextChunks: string[]): Promise<LayerExecutionResponse> => {
    try {
      const state = get();
      const ensembleNodes = state.nodes
        .filter(isWorkflowNode)
        .filter(node => node.data.layer === LayerType.ENSEMBLE)
        .map(node => ({
          id: node.id,
          model_type: node.data.model_type,
          prompt: state.layerPrompts[LayerType.ENSEMBLE],
          layer: node.data.layer,
          position: node.position
        }));

      const response = await layerWorkflowAPI.executeEnsembleLayer({
        knowledge_base: state.selectedKnowledgeBase,
        layer_input: generationResult,
        nodes: ensembleNodes,
        context_chunks: contextChunks
      });
      
      // 실행 상태 업데이트
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          status: 'ensembling',
          steps: [...state.currentExecution.steps, {
            id: 'ensemble_layer',
            type: 'ensemble',
            status: 'completed',
            result: response.combined_result,
            start_time: new Date(),
            end_time: new Date()
          }],
          ensemble_result: response
        } : null
      }));

      return response;
    } catch (error) {
      console.error('Ensemble Layer 실행 중 오류:', error);
      throw error;
    }
  },

  executeValidationLayer: async (ensembleResult: string, contextChunks: string[]): Promise<ValidationLayerResponse> => {
    try {
      console.log('🔍 Validation Layer 실행 시작 - 입력 데이터 검증:', {
        ensembleResultLength: ensembleResult.length,
        ensembleResultPreview: ensembleResult.substring(0, 200),
        ensembleResultHasTable: ensembleResult.includes('|'),
        ensembleResultTableLines: ensembleResult.split('\n').filter(line => line.includes('|')).length,
        contextChunksCount: contextChunks.length,
        fullEnsembleResult: ensembleResult // 전체 Ensemble Result 내용
      });
      
      const state = get();
      const validationNodes = state.nodes
        .filter(isWorkflowNode)
        .filter(node => node.data.layer === LayerType.VALIDATION)
        .map(node => ({
          id: node.id,
          model_type: node.data.model_type,
          prompt: state.layerPrompts[LayerType.VALIDATION],
          layer: node.data.layer,
          position: node.position
        }));

      const response = await layerWorkflowAPI.executeValidationLayer({
        knowledge_base: state.selectedKnowledgeBase,
        layer_input: ensembleResult,
        nodes: validationNodes,
        context_chunks: contextChunks
      });
      
      // 실행 상태 업데이트
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          status: 'completed',
          steps: [...state.currentExecution.steps, {
            id: 'validation_layer',
            type: 'validation',
            status: 'completed',
            result: response.combined_result,
            start_time: new Date(),
            end_time: new Date()
          }],
          validation_results: [response],
          final_result: response.combined_result,
          filtered_requirements: response.filtered_requirements,
          completed_at: new Date()
        } : null,
        isExecuting: false
      }));

      return response;
    } catch (error) {
      console.error('Validation Layer 실행 중 오류:', error);
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          status: 'error',
          error: error instanceof Error ? error.message : 'Validation Layer error'
        } : null,
        isExecuting: false
      }));
      throw error;
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

    // 선택된 프로바이더의 사용 가능한 모델 확인
    const providerModels = await get().loadProviderModels(selectedProvider);
    const availableProviderModels = providerModels.filter(m => m.available);
    if (availableProviderModels.length === 0) {
      const providerName = selectedProvider === 'perplexity' ? 'Perplexity' :
                          selectedProvider === 'openai' ? 'OpenAI' :
                          selectedProvider === 'google' ? 'Google AI Studio' : selectedProvider;
      throw new Error(`${providerName}에서 사용 가능한 모델이 없습니다. API 키를 확인해주세요.`);
    }

    // 현재 실행 중인 Layer 상태 설정
    set({ 
      isExecuting: true,
      currentExecutingLayer: layer 
    });

    console.log(`🔄 ${layer} Layer 실행 시작`);

    try {
      // 해당 레이어의 노드들 찾기
      const layerNodes = nodes.filter(node => 
        isWorkflowNode(node) && node.data.layer === layer
      ) as WorkflowNode[];

      if (layerNodes.length === 0) {
        throw new Error(`${layer} 레이어에 노드가 없습니다.`);
      }

      // 모든 Layer에 대해 지식 베이스 컨텍스트 검색 수행
      let contextChunks: string[] = [];
      
      if (selectedKnowledgeBase) {
        try {
          console.log(`${layer} Layer 컨텍스트 검색 시작...`);
          console.log('키워드:', keyword);
          console.log('입력 데이터:', input.substring(0, 200) + '...');
          
          // 1. 기본 키워드로 검색
          const searchResponse = await stepwiseWorkflowAPI.searchContext({
            knowledge_base: selectedKnowledgeBase,
            query: keyword,
            top_k: getTopKByIntensity(searchIntensity, 'basic')  // 검색 강도에 따른 동적 top_k
          });
          contextChunks = searchResponse.chunks || [];
          console.log(`기본 키워드 검색 결과: ${contextChunks.length}개 청크`);

          // 2. Generation/Ensemble Layer의 경우 추가 검색
          if (layer === LayerType.GENERATION || layer === LayerType.ENSEMBLE) {
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
                console.log(`키워드 "${inputKeyword}" 검색 결과: ${newChunks.length}개 청크`);
              }
            }
          }

          // 3. Validation Layer의 경우 요구사항 기반 확장 검색
          if (layer === LayerType.VALIDATION) {
            // 요구사항에서 추출한 키워드로 추가 검색
            const requirementKeywords = extractKeywordsFromRequirements(input);
            console.log('추출된 요구사항 키워드:', requirementKeywords);
            
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
                console.log(`키워드 "${reqKeyword}" 검색 결과: ${newChunks.length}개 청크`);
              }
            }
          }

          // 중복 제거 및 검색 강도에 따른 최종 컨텍스트 제한
          const maxContext = getTopKByIntensity(searchIntensity, 'context');
          contextChunks = Array.from(new Set(contextChunks)).slice(0, maxContext);
          
          console.log(`${layer} Layer - 총 수집된 컨텍스트 청크: ${contextChunks.length}개`);
          console.log('첫 번째 청크 샘플:', contextChunks[0]?.substring(0, 200) + '...');
          
          // 각 청크의 상세 정보 로깅
          contextChunks.forEach((chunk, index) => {
            console.log(`📄 청크 ${index + 1}: ${chunk.substring(0, 100)}...`);
          });

          // 컨텍스트가 충분하지 않은 경우 경고
          if (contextChunks.length < 3) {
            console.warn(`⚠️ ${layer} Layer를 위한 컨텍스트가 부족합니다. 현재: ${contextChunks.length}개`);
          } else {
            console.log(`✅ ${layer} Layer를 위한 충분한 컨텍스트 확보: ${contextChunks.length}개`);
          }
        } catch (error) {
          console.error(`${layer} Layer 컨텍스트 검색 실패:`, error);
          contextChunks = [];
        }
      } else {
        console.warn(`⚠️ ${layer} Layer: 지식 베이스가 선택되지 않아 컨텍스트 검색을 건너뜀`);
      }

      // 클라이언트에서 프롬프트 템플릿 처리
      const context = contextChunks.join('\n\n') || '컨텍스트가 제공되지 않았습니다.';
      const processedPrompt = prompt.replace(/{layer_input}/g, input).replace(/{context}/g, context);

      console.log('프롬프트 처리 완료:', {
        layer: layer,
        layer_input_length: input.length,
        context_chunks_count: contextChunks.length,
        context_length: context.length,
        prompt_preview: processedPrompt.substring(0, 200) + '...'
      });

      // Layer 프롬프트 API 호출
      const { selectedProvider } = get(); // 현재 선택된 provider 가져오기
      
      const request = {
        layer_type: layer,
        prompt: processedPrompt,  // 클라이언트에서 처리된 완성된 프롬프트 사용
        layer_input: input,
        knowledge_base: selectedKnowledgeBase,
        top_k: getTopKByIntensity(searchIntensity, 'basic'),  // 검색 강도에 따른 동적 top_k
        nodes: layerNodes.map(node => {
          console.log(`📤 노드 ${node.id} 전송 정보:`, {
            현재_model: node.data.model,
            provider: selectedProvider
          });
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

      // 결과 저장 및 실행 상태 초기화
      set(state => ({
        layerResults: {
          ...state.layerResults,
          [layer]: response
        },
        isExecuting: false,
        currentExecutingLayer: null
      }));

      console.log(`✅ ${layer} Layer 실행 완료`);

      // Layer 간 자동 데이터 흐름 처리 - Generation → Ensemble은 combined_result 사용
      if (layer === LayerType.GENERATION) {
        // Generation Layer 완료 → Ensemble Layer input 업데이트
        let generationInput = '';
        
        if (response.combined_result && response.combined_result.trim()) {
          // Ensemble Layer는 전체 결과를 비교 분석해야 하므로 combined_result 사용
          generationInput = response.combined_result;
          console.log('Generation Layer combined_result를 Ensemble Layer input으로 설정:', generationInput.substring(0, 100) + '...');
        } else if (response.final_result && response.final_result.trim()) {
          // fallback: final_result 사용
          generationInput = response.final_result;
          console.log('Generation Layer final_result를 Ensemble Layer input으로 설정 (fallback):', generationInput.substring(0, 100) + '...');
        } else if (response.outputs && response.outputs.length > 0) {
          // fallback: 기존 방식
          generationInput = response.outputs
            .map((output: NodeOutput) => `## ${output.model_type}\n${output.requirements}`)
            .join('\n\n');
          console.log('Generation Layer 결과를 Ensemble Layer input으로 설정 (legacy fallback):', generationInput.substring(0, 100) + '...');
        }
        
        if (generationInput) {
          set(state => ({
            layerInputs: {
              ...state.layerInputs,
              [LayerType.ENSEMBLE]: generationInput
            }
          }));
        }
      } else if (layer === LayerType.ENSEMBLE) {
        // Ensemble Layer 완료 → Validation Layer input 업데이트
        // Validation은 최종 정제된 요구사항을 검증해야 하므로 final_result 우선 사용
        let ensembleResult = '';
        
        console.log('Ensemble Layer 결과 분석:', {
          has_final_result: !!response.final_result,
          has_combined_result: !!response.combined_result,
          has_outputs: !!(response.outputs && response.outputs.length > 0),
          final_result_preview: response.final_result?.substring(0, 200),
          combined_result_preview: response.combined_result?.substring(0, 200)
        });
        
        // 제거된 항목 표가 아닌 실제 요구사항 표인지 검증하는 함수 (강화된 제거 테이블 감지)
        const isValidRequirementsTable = (content: string): boolean => {
          if (!content || !content.includes('|')) return false;
          
          console.log('🔍 요구사항 표 유효성 검사 시작:', content.substring(0, 150) + '...');
          
          // 1. 제거된 항목 관련 키워드가 포함되어 있으면 잘못된 표
          const removedKeywords = [
            '제거된', '삭제된', '제외된', '제거 사유', '삭제 사유',
            'removed', 'deleted', 'excluded', 'elimination', 'removal',
            '필터링된', '걸러진', '배제된', '탈락된',
            '부적절한', '불필요한', '중복된'
          ];
          
          const hasRemovedKeywords = removedKeywords.some(keyword => 
            content.toLowerCase().includes(keyword.toLowerCase())
          );
          
          if (hasRemovedKeywords) {
            console.warn('❌ 제거된 항목 표 감지됨 (키워드 매칭):', content.substring(0, 200));
            return false;
          }
          
          // 2. 제거 테이블의 일반적인 패턴 감지
          const removalPatterns = [
            /제거.*표/i,
            /삭제.*표/i,
            /제외.*표/i,
            /필터링.*결과/i,
            /제거.*목록/i,
            /부적절.*요구사항/i,
            /중복.*요구사항/i
          ];
          
          const hasRemovalPattern = removalPatterns.some(pattern => pattern.test(content));
          if (hasRemovalPattern) {
            console.warn('❌ 제거된 항목 표 감지됨 (패턴 매칭):', content.substring(0, 200));
            return false;
          }
          
          // 3. 테이블 내용 분석 - 대부분 행이 제거 관련 내용인지 확인
          const tableRowsForAnalysis = content.split('\n').filter(line => line.includes('|') && line.trim());
          if (tableRowsForAnalysis.length >= 3) {
            const dataRows = tableRowsForAnalysis.slice(2); // 헤더와 구분선 제외
            let removalContentCount = 0;
            
            dataRows.forEach(row => {
              const lowerRow = row.toLowerCase();
              if (removedKeywords.some(keyword => lowerRow.includes(keyword))) {
                removalContentCount++;
              }
            });
            
            // 50% 이상의 행이 제거 관련 내용이면 제거 테이블로 간주
            if (removalContentCount > dataRows.length * 0.5) {
              console.warn('❌ 제거된 항목 표 감지됨 (내용 분석):', {
                totalRows: dataRows.length,
                removalRows: removalContentCount,
                percentage: Math.round((removalContentCount / dataRows.length) * 100)
              });
              return false;
            }
          }
          
          // 4. 테이블 구조 분석
          const lines = content.split('\n').map(line => line.trim()).filter(line => line.length > 0);
          const tableLines = lines.filter(line => line.includes('|'));
          
          if (tableLines.length < 3) {  // 헤더 + 구분선 + 최소 1개 데이터 행
            console.warn('❌ 테이블 줄 수 부족:', tableLines.length);
            return false;
          }
          
          // 5. 마지막 행이 잘렸는지 검사
          const lastTableLine = tableLines[tableLines.length - 1];
          const isLastLineComplete = lastTableLine.endsWith('|') || lastTableLine.split('|').length >= 3;
          
          if (!isLastLineComplete) {
            console.warn('❌ 마지막 테이블 행이 불완전함:', lastTableLine);
            return false;
          }
          
          // 6. 모든 데이터 행이 비슷한 컬럼 수를 가지는지 확인
          const dataLines = tableLines.slice(2); // 헤더와 구분선 제외
          if (dataLines.length > 0) {
            const firstColumnCount = dataLines[0].split('|').length;
            const inconsistentLines = dataLines.filter(line => {
              const columnCount = line.split('|').length;
              return Math.abs(columnCount - firstColumnCount) > 1; // 1개 이상 차이나면 비정상
            });
            
            if (inconsistentLines.length > 0) {
              console.warn('❌ 일관성 없는 컬럼 수를 가진 행들:', inconsistentLines.map(line => line.substring(0, 50)));
              // 불일치가 많으면 잘린 것으로 간주
              if (inconsistentLines.length > dataLines.length * 0.3) { // 30% 이상이 불일치
                return false;
              }
            }
          }
          
          // 7. REQ- 패턴이 포함되어 있는지 확인 (실제 요구사항 표의 특징)
          const hasReqPattern = /REQ-\d+/i.test(content);
          
          console.log('✅ 요구사항 표 검증 결과:', {
            hasReqPattern,
            tableLineCount: tableLines.length,
            isLastLineComplete,
            contentPreview: content.substring(0, 100),
            lastLinePreview: lastTableLine.substring(0, 50)
          });
          
          return hasReqPattern;
        };
        
        // 우선순위별로 검증하며 결과 선택
        if (response.final_result && response.final_result.trim()) {
          if (isValidRequirementsTable(response.final_result)) {
            ensembleResult = response.final_result;
            console.log('✅ Ensemble Layer final_result 검증 통과, Validation Layer input으로 설정:', {
              length: ensembleResult.length,
              preview: ensembleResult.substring(0, 100) + '...',
              hasTable: ensembleResult.includes('|')
            });
          } else {
            console.warn('❌ final_result가 제거된 항목 표임. combined_result 확인 중...');
            if (response.combined_result && response.combined_result.trim() && isValidRequirementsTable(response.combined_result)) {
              ensembleResult = response.combined_result;
              console.log('✅ Ensemble Layer combined_result 검증 통과, Validation Layer input으로 설정 (fallback):', {
                length: ensembleResult.length,
                preview: ensembleResult.substring(0, 100) + '...',
                hasTable: ensembleResult.includes('|')
              });
            }
          }
        } else if (response.combined_result && response.combined_result.trim()) {
          if (isValidRequirementsTable(response.combined_result)) {
            ensembleResult = response.combined_result;
            console.log('✅ Ensemble Layer combined_result 검증 통과, Validation Layer input으로 설정:', {
              length: ensembleResult.length,
              preview: ensembleResult.substring(0, 200) + '...',
              hasTable: ensembleResult.includes('|'),
              tableLines: ensembleResult.split('\n').filter(line => line.includes('|')).length,
              fullContent: ensembleResult // 전체 내용 로깅
            });
          }
        } else if (response.outputs && response.outputs.length > 0) {
          // 마지막 fallback: legacy outputs 사용
          ensembleResult = response.outputs[0]?.requirements || '';
          console.log('⚠️  Ensemble Layer outputs를 Validation Layer input으로 설정 (legacy fallback):', {
            length: ensembleResult.length,
            preview: ensembleResult.substring(0, 100) + '...',
            hasTable: ensembleResult.includes('|')
          });
        }
        
        if (ensembleResult.trim()) {
          console.log('🔄 Validation Layer input 업데이트 실행 중...');
          console.log('📋 전체 Ensemble Result 내용:', {
            fullText: ensembleResult,
            charCount: ensembleResult.length,
            lineCount: ensembleResult.split('\n').length,
            tableLineCount: ensembleResult.split('\n').filter(line => line.includes('|')).length
          });
          
          set(state => {
            const newState = {
              layerInputs: {
                ...state.layerInputs,
                [LayerType.VALIDATION]: ensembleResult
              }
            };
            console.log('✅ Validation Layer input이 업데이트됨:', {
              previousInput: state.layerInputs[LayerType.VALIDATION]?.substring(0, 100),
              newInput: ensembleResult.substring(0, 100),
              inputLength: ensembleResult.length,
              fullNewInput: ensembleResult // 전체 새 입력 로깅
            });
            return newState;
          });
        } else {
          console.error('❌ Ensemble Layer에서 유효한 결과를 찾을 수 없습니다:', {
            final_result: response.final_result,
            combined_result: response.combined_result,
            outputs: response.outputs
          });
        }
      }

      return response;
    } catch (error) {
      console.error(`❌ ${layer} Layer 실행 중 오류:`, error);
      set({ 
        isExecuting: false,
        currentExecutingLayer: null 
      });
      throw error;
    }
  },

  clearLayerResult: (layer: LayerType) => {
    set(state => ({
      layerResults: {
        ...state.layerResults,
        [layer]: null
      }
    }));
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
        return 'gemini-2.5-flash';
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
    
    console.log(`🔄 Provider ${provider}로 노드 업데이트 시작, 기본 모델: ${defaultModelValue}`);
    
    // 이미 로드된 모델 목록 사용 (없으면 다시 로드)
    let availableModels = providerModels;
    if (availableModels.length === 0) {
      console.log(`📡 ${provider} 모델 목록이 없어서 다시 로드...`);
      availableModels = await get().loadProviderModels(provider);
      set({ providerModels: availableModels });
    }
    
    console.log(`📋 ${provider} 사용 가능한 모델들:`, availableModels.map(m => m.id));
    
    // 기본 모델 찾기
    const defaultModel = availableModels.find(model => model.id === defaultModelValue);
    const selectedModel = defaultModel || availableModels[0];
    
    console.log(`🎯 선택된 모델:`, selectedModel ? { id: selectedModel.id, name: selectedModel.name } : 'null');
    
    if (!selectedModel) {
      console.warn(`Provider ${provider}에 사용 가능한 모델이 없습니다.`);
      return;
    }

    const updatedNodes = nodes.map(node => {
      if (isWorkflowNode(node)) {
        console.log(`🔄 노드 ${node.id} 업데이트: ${node.data.model || 'undefined'} → ${selectedModel.id}`);
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
    console.log(`✅ ${nodes.filter(isWorkflowNode).length}개 노드가 ${selectedModel.name}로 업데이트됨`);
  },
}));

// ✅ 기본 워크플로우는 App.tsx에서 useEffect로 초기화됨 (중복 방지)
