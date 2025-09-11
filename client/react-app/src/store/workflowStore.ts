import { create } from 'zustand';
import { WorkflowNode, PlaceholderNode, WorkflowNodeData, AnyWorkflowNode, LayerType, ModelType } from '../types';

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
  currentViewport: { x: number; y: number; zoom: number } | null; // ✅ 현재 뷰포트 상태 추가
  
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
  
  // ✅ 뷰포트 관련 액션들
  setCurrentViewport: (viewport: { x: number; y: number; zoom: number }) => void;
  saveCurrentWorkflow: () => void;
  restoreWorkflow: () => boolean;
  exportToJSON: () => void;
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
      prompt: getDefaultPrompt(layer),
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

const getDefaultPrompt = (layer: LayerType): string => {
  switch (layer) {
    case LayerType.GENERATION:
      return `키워드 '{keyword}'에 대한 요구사항을 생성해주세요.

**컨텍스트:**
{context}

**입력 데이터:**
{input_data}

**지침:**
1. 마크다운 표 형식으로 출력
2. 시각적 자료 참조 금지
3. 구체적이고 측정 가능한 요구사항

**출력 형식:**
| ID | 요구사항 (Requirement) | 출처 (Source) | 상세 설명 (Notes) |
|---|---|---|---|
| REQ-001 | ... | ... | ... |`;
    
    case LayerType.ENSEMBLE:
      return `다음 여러 결과들을 통합하여 하나의 일관된 요구사항 표를 만들어주세요.

**입력 결과들:**
{input_data}

**컨텍스트:**
{context}

**지침:**
1. 중복 제거 및 통합
2. 일관된 ID 체계 적용
3. 마크다운 표 형식 유지
4. 품질 높은 요구사항만 선별

**통합된 요구사항 표:**`;
    
    case LayerType.VALIDATION:
      return `다음 요구사항 표를 검증하고 개선해주세요.

**검증할 요구사항:**
{input_data}

**컨텍스트:**
{context}

**검증 기준:**
1. 원본 컨텍스트와의 일치성
2. 요구사항의 명확성
3. 측정 가능성
4. 완결성

**검증된 요구사항 표:**`;
    
    default:
      return "";
  }
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
  currentViewport: null, // ✅ 초기 뷰포트 상태

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

  // ✅ 현재 워크플로우 상태를 localStorage에 저장 (뷰포트 포함)
  saveCurrentWorkflow: () => {
    const { nodes, selectedKnowledgeBase, keyword, currentViewport } = get();
    const workflowState = {
      nodes,
      selectedKnowledgeBase,
      keyword,
      viewport: currentViewport, // ✅ 현재 뷰포트 상태 포함
      savedAt: new Date().toISOString()
    };
    
    localStorage.setItem(WORKFLOW_SAVE_KEY, JSON.stringify(workflowState));
    console.log('워크플로우 상태가 뷰포트 정보와 함께 저장되었습니다:', currentViewport);
  },

  // ✅ 저장된 워크플로우 상태 복원 (뷰포트 포함)
  restoreWorkflow: () => {
    try {
      const savedState = localStorage.getItem(WORKFLOW_SAVE_KEY);
      if (savedState) {
        const workflowState = JSON.parse(savedState);
        
        set({ 
          nodes: workflowState.nodes || [],
          selectedKnowledgeBase: workflowState.selectedKnowledgeBase || '',
          keyword: workflowState.keyword || '',
          currentViewport: workflowState.viewport || null // ✅ 뷰포트 복원
        });
        
        setTimeout(() => {
          get().updatePlaceholderNodes();
        }, 100);
        
        console.log('워크플로우 상태가 뷰포트 정보와 함께 복원되었습니다:', workflowState.viewport);
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
  setKeyword: (keyword) => set({ keyword }),
  setIsExecuting: (executing) => set({ isExecuting: executing }),
  setResult: (result) => set({ result })
}));

// 초기 placeholder 노드들 생성
setTimeout(() => {
  useWorkflowStore.getState().updatePlaceholderNodes();
}, 100);
