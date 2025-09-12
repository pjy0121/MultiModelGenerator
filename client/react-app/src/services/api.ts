import axios from 'axios';
import { LayerPromptRequest } from '../types';

export const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Import types
import {
  SearchContextRequest,
  SearchContextResponse,
  SingleNodeRequest,
  SingleNodeResponse,
  EnsembleRequest,
  ValidationRequest,
  ValidationResponse,
  KnowledgeBase,
  LayerExecutionRequest,
  LayerExecutionResponse,
  ValidationLayerResponse
} from '../types';

// ==================== 새로운 Layer별 워크플로우 API ====================

export const layerWorkflowAPI = {
  // Generation Layer 실행
  executeGenerationLayer: async (request: LayerExecutionRequest): Promise<LayerExecutionResponse> => {
    const response = await api.post('/execute-generation-layer', request);
    return response.data;
  },

  // Ensemble Layer 실행
  executeEnsembleLayer: async (request: LayerExecutionRequest): Promise<LayerExecutionResponse> => {
    const response = await api.post('/execute-ensemble-layer', request);
    return response.data;
  },

  // Validation Layer 실행
  executeValidationLayer: async (request: LayerExecutionRequest): Promise<ValidationLayerResponse> => {
    const response = await api.post('/execute-validation-layer', request);
    return response.data;
  }
};

// ==================== 기존 단계별 워크플로우 API ====================

export const stepwiseWorkflowAPI = {
  // 1. 컨텍스트 검색
  searchContext: async (request: SearchContextRequest): Promise<SearchContextResponse> => {
    const response = await api.post('/search-context', request);
    return response.data;
  },

  // 2. 단일 노드 실행 (Generation Layer)
  executeNode: async (request: SingleNodeRequest): Promise<SingleNodeResponse> => {
    const response = await api.post('/execute-node', request);
    return response.data;
  },

  // 3. 앙상블 실행
  executeEnsemble: async (request: EnsembleRequest): Promise<SingleNodeResponse> => {
    const response = await api.post('/execute-ensemble', request);
    return response.data;
  },

  // 4. 검증 실행
  executeValidation: async (request: ValidationRequest): Promise<ValidationResponse> => {
    const response = await api.post('/execute-validation', request);
    return response.data;
  }
};

// ==================== 기존 API 함수들 ====================

export const workflowAPI = {
  // 지식 베이스 목록 조회
  getKnowledgeBases: async (): Promise<KnowledgeBase[]> => {
    const response = await api.get('/knowledge-bases');
    return response.data.knowledge_bases;
  },

  // Provider별 모델 목록
  getProviderModels: async (provider: string) => {
    const response = await api.get(`/available-models/${provider}`);
    // 서버 응답을 클라이언트 AvailableModel 형식으로 변환
    return response.data.map((serverModel: any) => ({
      id: serverModel.value || serverModel.model_type, // value를 id로 매핑
      name: serverModel.label || serverModel.value,    // label을 name으로 매핑  
      provider: serverModel.provider,
      model_type: serverModel.model_type,
      available: !serverModel.disabled               // disabled의 반대값을 available로 매핑
    }));
  },

  // 기본 프롬프트 템플릿
  getDefaultPrompts: async () => {
    const response = await api.get('/default-prompts');
    return response.data;
  }
};

// Layer별 프롬프트 시스템 API
export const layerPromptAPI = {
  executeLayerPrompt: async (request: LayerPromptRequest) => {
    const response = await api.post('/execute-layer-prompt', request);
    return response.data;
  }
};
