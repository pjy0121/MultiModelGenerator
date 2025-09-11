import { create } from 'zustand';
import { WorkflowNode, PlaceholderNode, WorkflowNodeData, AnyWorkflowNode, LayerType, ModelType, WorkflowExecution, WorkflowExecutionStep, LayerExecutionResponse, ValidationLayerResponse, NodeOutput } from '../types';
import { stepwiseWorkflowAPI, layerWorkflowAPI, layerPromptAPI } from '../services/api';

// 타입 가드 함수 정의
function isWorkflowNode(node: AnyWorkflowNode): node is WorkflowNode {
  return node.type === 'customNode';
}

function isPlaceholderNode(node: AnyWorkflowNode): node is PlaceholderNode {
  return node.type === 'placeholderNode';
}

interface WorkflowState {
  nodes: AnyWorkflowNode[];
  selectedKnowledgeBase: string;
  keyword: string;
  isExecuting: boolean;
  result: any;
  currentViewport: { x: number; y: number; zoom: number } | null;
  
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
  
  // Actions
  setNodes: (nodes: AnyWorkflowNode[]) => void;
  addNode: (layer: LayerType) => void;
  updateNode: (nodeId: string, data: Partial<WorkflowNodeData>) => void;
  removeNode: (nodeId: string) => void;
  setSelectedKnowledgeBase: (kb: string) => void;
  setKeyword: (keyword: string) => void;
  setIsExecuting: (executing: boolean) => void;
  setResult: (result: any) => void;
  updatePlaceholderNodes: () => void;
  
  // 뷰포트 관련 액션들
  setCurrentViewport: (viewport: { x: number; y: number; zoom: number }) => void;
  saveCurrentWorkflow: () => void;
  restoreWorkflow: () => boolean;
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
      model_type: ModelType.PERPLEXITY_SONAR_PRO,
      layer,
      label: getModelLabel(ModelType.PERPLEXITY_SONAR_PRO)
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

const getModelLabel = (modelType: ModelType): string => {
  switch (modelType) {
    case ModelType.PERPLEXITY_SONAR_PRO:
      return "Sonar Pro";
    case ModelType.PERPLEXITY_SONAR_MEDIUM:
      return "Sonar Medium";
    case ModelType.OPENAI_GPT4:
      return "GPT-4";
    case ModelType.OPENAI_GPT35:
      return "GPT-3.5";
    default:
      return "Unknown";
  }
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
  isExecuting: false,
  result: null,
  currentViewport: null,
  layerPrompts: {
    [LayerType.GENERATION]: `키워드 '{input_data}'에 대한 상세하고 구체적인 요구사항을 생성해주세요.

**컨텍스트 (지식베이스에서 검색된 내용):**
{context}

**입력 데이터:**
{input_data}

**작업 지침:**
1. 제공된 컨텍스트를 바탕으로 구체적이고 측정 가능한 요구사항을 생성하세요
2. 각 요구사항은 명확하고 실행 가능해야 합니다
3. 문서 내에서 해당 요구사항의 근거가 되는 위치를 명시하세요
4. 시각적 자료나 그림에 대한 직접적인 참조는 금지합니다
5. 요구사항 ID는 REQ-001부터 순차적으로 부여하세요

**필수 출력 형식 (마크다운 표):**
| ID | 요구사항 (Requirement) | 문서 내 페이지 번호 또는 섹션 번호 (Page/Section) | 상세 설명 (Notes) |
|---|---|---|---|
| REQ-001 | [구체적인 요구사항 내용] | [페이지 번호 또는 섹션명] | [추가적인 설명이나 조건] |
| REQ-002 | ... | ... | ... |

**주의사항:**
- 반드시 위의 표 형식을 정확히 따라주세요
- 각 요구사항은 한 줄로 간결하게 작성하세요
- 페이지 번호 또는 섹션 번호를 구체적으로 명시하세요`,

    [LayerType.ENSEMBLE]: `다음 여러 모델에서 생성된 요구사항들을 통합하여 하나의 일관되고 완성도 높은 요구사항 표를 만들어주세요.

**입력 결과들 (여러 모델의 요구사항 생성 결과):**
{input_data}

**컨텍스트 (지식베이스에서 검색된 내용):**
{context}

**통합 작업 지침:**
1. **중복 제거**: 동일하거나 유사한 요구사항들을 식별하고 통합하세요
2. **일관성 확보**: 요구사항 ID 체계를 통일하고 일관된 형식으로 정리하세요
3. **품질 향상**: 여러 모델의 결과를 종합하여 더 완성도 높은 요구사항으로 개선하세요
4. **완전성 검토**: 누락된 중요한 요구사항이 있는지 확인하고 추가하세요
5. **우선순위**: 중요도와 우선순위를 고려하여 정렬하세요

**필수 출력 형식 (마크다운 표):**
| ID | 요구사항 (Requirement) | 문서 내 페이지 번호 또는 섹션 번호 (Page/Section) | 상세 설명 (Notes) |
|---|---|---|---|
| REQ-001 | [통합된 요구사항 내용] | [페이지 번호 또는 섹션명] | [통합 과정에서 추가된 설명] |
| REQ-002 | ... | ... | ... |

**통합 과정 요약:**
- 총 요구사항 수: [최종 요구사항 개수]
- 제거된 중복사항: [중복 제거 내용 간략 설명]
- 개선된 사항: [품질 향상 내용 간략 설명]`,

    [LayerType.VALIDATION]: `다음 요구사항 표를 지식베이스 내용을 바탕으로 엄격하게 검증하고 필터링해주세요. 목적은 내용 수정이 아닌 잘못된 요구사항의 완전 제거입니다.

**검증할 요구사항:**
{input_data}

**지식베이스 컨텍스트:**
{context}

**필터링 기준 (반드시 준수):**
1. **지식베이스 일치성**: 제공된 컨텍스트에 명확한 근거가 없는 요구사항은 완전 제거
2. **사실 정확성**: 지식베이스 내용과 모순되거나 잘못된 정보가 포함된 요구사항은 완전 제거
3. **실현 가능성**: 기술적으로 불가능하거나 비현실적인 요구사항은 완전 제거
4. **구체성**: 모호하거나 측정 불가능한 요구사항은 완전 제거
5. **문서 근거**: 문서 내 위치가 부정확하거나 근거가 없는 요구사항은 완전 제거

**작업 지침:**
- 수정하지 말고 완전히 제거만 하세요
- 의심스러운 요구사항은 모두 제거하세요
- 지식베이스에 근거가 명확하지 않으면 제거하세요
- 기준에 완전히 부합하는 요구사항만 통과시키세요

**필수 출력 형식:**

**필터링된 요구사항 목록 (통과):**
| ID | 요구사항 (Requirement) | 문서 내 페이지 번호 또는 섹션 번호 (Page/Section) | 필터링 상태 (Status) |
|---|---|---|---|
| REQ-001 | [통과한 요구사항] | [확인된 페이지 번호 또는 섹션명] | ✅ 통과 |
| REQ-002 | ... | ... | ... |

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
  
  // 새로운 단계별 워크플로우 실행 상태
  currentExecution: null,

  setNodes: (nodes) => set({ nodes }),
  
  // ✅ 현재 뷰포트 설정 (실시간으로 계속 업데이트됨)
  setCurrentViewport: (viewport) => set({ currentViewport: viewport }),
  
  addNode: (layer) => {
    console.log('addNode 호출됨:', layer);
    
    const { nodes } = get();
    const realNodes = nodes.filter(isWorkflowNode).filter(n => n.data.layer === layer);
    
    // 개수 제한 체크
    if (layer === LayerType.GENERATION && realNodes.length >= 3) {
      console.log('Generation Layer 최대 개수 도달');
      return;
    }
    if (layer === LayerType.VALIDATION && realNodes.length >= 5) {
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
    
    setTimeout(() => {
      get().updatePlaceholderNodes();
    }, 0);
  },

  updateNode: (nodeId, data) => {
    const { nodes } = get();
    const updatedNodes = nodes.map((node): AnyWorkflowNode => {
      if (node.id === nodeId && isWorkflowNode(node)) {
        return { 
          ...node, 
          data: { 
            ...node.data, 
            ...data,
            label: data.model_type ? getModelLabel(data.model_type) : node.data.label
          }
        };
      }
      return node;
    });
    set({ nodes: updatedNodes });
  },

  removeNode: (nodeId) => {
    console.log('removeNode 호출됨:', nodeId);
    
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
    
    console.log('updatePlaceholderNodes 호출됨');
    
    const realNodes = nodes.filter(n => !isPlaceholderNode(n));
    const newNodes: AnyWorkflowNode[] = [...realNodes];
    const addNodeFunction = state.addNode;
    
    // Generation Layer placeholder
    const generationNodes = realNodes.filter(isWorkflowNode)
      .filter(n => n.data.layer === LayerType.GENERATION)
      .sort((a, b) => a.position.x - b.position.x);
    
    if (generationNodes.length < 3) {
      const nextPosition = {
        x: LAYER_POSITIONS[LayerType.GENERATION].baseX + (generationNodes.length * LAYER_POSITIONS[LayerType.GENERATION].spacing),
        y: LAYER_POSITIONS[LayerType.GENERATION].baseY
      };
      
      console.log('Generation placeholder 생성:', nextPosition);
      newNodes.push(createPlaceholderNode(LayerType.GENERATION, nextPosition, addNodeFunction));
    }
    
    // Validation Layer placeholder
    const validationNodes = realNodes.filter(isWorkflowNode)
      .filter(n => n.data.layer === LayerType.VALIDATION)
      .sort((a, b) => a.position.x - b.position.x);
    
    if (validationNodes.length < 5) {
      const nextPosition = {
        x: LAYER_POSITIONS[LayerType.VALIDATION].baseX + (validationNodes.length * LAYER_POSITIONS[LayerType.VALIDATION].spacing),
        y: LAYER_POSITIONS[LayerType.VALIDATION].baseY
      };
      
      console.log('Validation placeholder 생성:', nextPosition);
      newNodes.push(createPlaceholderNode(LayerType.VALIDATION, nextPosition, addNodeFunction));
    }
    
    set({ nodes: newNodes });
  },

  // ✅ 현재 워크플로우 상태를 localStorage에 저장 (뷰포트 포함, 지식베이스/키워드 제외)
  saveCurrentWorkflow: () => {
    const { nodes, currentViewport } = get();
    const workflowState = {
      nodes,
      viewport: currentViewport, // ✅ 현재 뷰포트 상태 포함 (x, y, zoom)
      savedAt: new Date().toISOString()
    };
    
    localStorage.setItem(WORKFLOW_SAVE_KEY, JSON.stringify(workflowState));
    console.log('워크플로우 구성이 뷰포트 정보와 함께 저장되었습니다:', {
      viewport: currentViewport,
      nodeCount: nodes.length
    });
  },

  // ✅ 저장된 워크플로우 상태 복원 (뷰포트 포함, 지식베이스/키워드 제외)
  restoreWorkflow: () => {
    try {
      const savedState = localStorage.getItem(WORKFLOW_SAVE_KEY);
      if (savedState) {
        const workflowState = JSON.parse(savedState);
        
        set({ 
          nodes: workflowState.nodes || [],
          currentViewport: workflowState.viewport || null // ✅ 뷰포트 복원 (x, y, zoom)
        });
        
        setTimeout(() => {
          get().updatePlaceholderNodes();
        }, 100);
        
        console.log('워크플로우 구성이 뷰포트 정보와 함께 복원되었습니다:', {
          viewport: workflowState.viewport,
          nodeCount: (workflowState.nodes || []).length,
          savedAt: workflowState.savedAt
        });
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
    const { nodes, selectedKnowledgeBase, keyword, currentViewport } = get();
    const exportData = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      workflow: {
        nodes,
        selectedKnowledgeBase,
        keyword,
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
    const { nodes, selectedKnowledgeBase, keyword, layerPrompts } = get();
    
    if (!selectedKnowledgeBase || !keyword) {
      console.error('지식베이스 또는 키워드가 선택되지 않았습니다.');
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
        top_k: 5
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
      
      // 2. Generation Layer 실행
      const generationResults: string[] = [];
      
      for (const node of generationNodes) {
        const stepId = `gen_${node.id}`;
        get().updateExecutionStep(stepId, { status: 'running', start_time: new Date() });
        
        try {
          const response = await stepwiseWorkflowAPI.executeNode({
            knowledge_base: selectedKnowledgeBase,
            input_data: keyword,
            node_config: {
              id: node.data.id,
              model_type: node.data.model_type,
              prompt: layerPrompts[LayerType.GENERATION],
              layer: node.data.layer,
              position: node.position
            },
            context_chunks: searchResponse.chunks
          });
          
          generationResults.push(response.node_output.requirements);
          
          get().updateExecutionStep(stepId, { 
            status: 'completed', 
            end_time: new Date(),
            result: response 
          });
          
        } catch (error) {
          get().updateExecutionStep(stepId, { 
            status: 'error', 
            end_time: new Date(),
            error: error instanceof Error ? error.message : 'Unknown error'
          });
        }
      }
      
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          generationResults,
          status: 'ensembling'
        } : null
      }));
      
      // 3. Ensemble Layer 실행
      get().updateExecutionStep('ensemble', { status: 'running', start_time: new Date() });
      
      const ensembleResponse = await stepwiseWorkflowAPI.executeEnsemble({
        knowledge_base: selectedKnowledgeBase,
        generation_results: generationResults,
        ensemble_node: {
          id: ensembleNodes[0].data.id,
          model_type: ensembleNodes[0].data.model_type,
          prompt: layerPrompts[LayerType.ENSEMBLE],
          layer: ensembleNodes[0].data.layer,
          position: ensembleNodes[0].position
        },
        context_chunks: searchResponse.chunks
      });
      
      get().updateExecutionStep('ensemble', { 
        status: 'completed', 
        end_time: new Date(),
        result: ensembleResponse 
      });
      
      let currentRequirements = ensembleResponse.node_output.requirements;
      
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          ensembleResult: currentRequirements,
          status: 'validating'
        } : null
      }));
      
      // 4. Validation Layer 실행
      for (const node of validationNodes) {
        const stepId = `val_${node.id}`;
        get().updateExecutionStep(stepId, { status: 'running', start_time: new Date() });
        
        try {
          const response = await stepwiseWorkflowAPI.executeValidation({
            knowledge_base: selectedKnowledgeBase,
            input_requirements: currentRequirements,
            validation_node: {
              id: node.data.id,
              model_type: node.data.model_type,
              prompt: layerPrompts[LayerType.VALIDATION],
              layer: node.data.layer,
              position: node.position
            },
            context_chunks: searchResponse.chunks
          });
          
          currentRequirements = response.node_output.requirements;
          
          get().updateExecutionStep(stepId, { 
            status: 'completed', 
            end_time: new Date(),
            result: response 
          });
          
        } catch (error) {
          get().updateExecutionStep(stepId, { 
            status: 'error', 
            end_time: new Date(),
            error: error instanceof Error ? error.message : 'Unknown error'
          });
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
        result: {
          final_requirements: currentRequirements,
          execution_steps: get().currentExecution?.steps || []
        }
      }));
      
    } catch (error) {
      console.error('워크플로우 실행 중 오류:', error);
      set(state => ({
        currentExecution: state.currentExecution ? {
          ...state.currentExecution,
          status: 'error',
          error: error instanceof Error ? error.message : 'Unknown error'
        } : null,
        isExecuting: false
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
        input_data: state.keyword,
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
        input_data: generationResult,
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
        input_data: ensembleResult,
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
    const { layerPrompts, layerInputs, nodes } = get();
    const prompt = layerPrompts[layer];
    const input = layerInputs[layer];

    if (!prompt.trim()) {
      throw new Error('프롬프트를 입력해주세요.');
    }

    set({ isExecuting: true });

    try {
      // 해당 레이어의 노드들 찾기
      const layerNodes = nodes.filter(node => 
        isWorkflowNode(node) && node.data.layer === layer
      ) as WorkflowNode[];

      if (layerNodes.length === 0) {
        throw new Error(`${layer} 레이어에 노드가 없습니다.`);
      }

      // Layer 프롬프트 API 호출
      const request = {
        layer_type: layer,
        prompt: prompt,
        input_data: input,
        knowledge_base: get().selectedKnowledgeBase,
        nodes: layerNodes.map(node => ({
          id: node.id,
          model_type: node.data.model_type,
          prompt: prompt,
          layer: node.data.layer,
          position: node.position
        })),
        context_chunks: []
      };

      const response = await layerPromptAPI.executeLayerPrompt(request);

      // 결과 저장
      set(state => ({
        layerResults: {
          ...state.layerResults,
          [layer]: response
        },
        isExecuting: false
      }));

      // Layer 간 자동 데이터 흐름 처리
      if (layer === LayerType.GENERATION) {
        // Generation Layer 완료 → Ensemble Layer input 업데이트
        if (response.outputs && response.outputs.length > 0) {
          const combinedGenerationResults = response.outputs
            .map((output: NodeOutput) => `## ${output.model_type}\n${output.requirements}`)
            .join('\n\n');
          
          console.log('Generation Layer 결과를 Ensemble Layer input으로 설정:', combinedGenerationResults.substring(0, 100) + '...');
          
          set(state => ({
            layerInputs: {
              ...state.layerInputs,
              [LayerType.ENSEMBLE]: combinedGenerationResults
            }
          }));
        }
      } else if (layer === LayerType.ENSEMBLE) {
        // Ensemble Layer 완료 → Validation Layer input 업데이트
        if (response.outputs && response.outputs.length > 0) {
          const ensembleResult = response.outputs[0]?.requirements || '';
          
          console.log('Ensemble Layer 결과를 Validation Layer input으로 설정:', ensembleResult.substring(0, 100) + '...');
          
          set(state => ({
            layerInputs: {
              ...state.layerInputs,
              [LayerType.VALIDATION]: ensembleResult
            }
          }));
        }
      } else if (layer === LayerType.VALIDATION) {
        // Validation Layer의 각 노드 완료 → 다음 Validation 노드의 input 업데이트
        if (response.outputs && response.outputs.length > 0) {
          // 마지막 출력 결과를 다시 Validation Layer input으로 설정 (순차 처리용)
          const lastValidationResult = response.outputs[response.outputs.length - 1]?.requirements || '';
          
          console.log('Validation Layer 결과를 다시 Validation Layer input으로 설정:', lastValidationResult.substring(0, 100) + '...');
          
          set(state => ({
            layerInputs: {
              ...state.layerInputs,
              [LayerType.VALIDATION]: lastValidationResult
            }
          }));
        }
      }

      return response;
    } catch (error) {
      console.error(`${layer} Layer 실행 중 오류:`, error);
      set({ isExecuting: false });
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
  }
}));

// 초기 placeholder 노드들 생성
setTimeout(() => {
  useWorkflowStore.getState().updatePlaceholderNodes();
}, 100);
