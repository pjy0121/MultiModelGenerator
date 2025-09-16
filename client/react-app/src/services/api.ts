import axios from 'axios';
import { 
  NodeBasedWorkflowResponse,
  KnowledgeBase,
  AvailableModel,
  LLMProvider
} from '../types';

export const api = axios.create({
  baseURL: 'http://localhost:5001',
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

// ==================== 노드 기반 워크플로우 API ====================

export const nodeBasedWorkflowAPI = {
  // 노드 기반 워크플로우 실행
  executeNodeWorkflow: async (request: any): Promise<NodeBasedWorkflowResponse> => {
    const response = await api.post('/execute-workflow', request);
    return response.data;
  }
};

// ==================== 기본 데이터 API ====================

export const workflowAPI = {
  // 지식 베이스 목록 조회
  getKnowledgeBases: async (): Promise<KnowledgeBase[]> => {
    const response = await api.get('/knowledge-bases');
    return response.data.knowledge_bases;
  },

  // Provider별 모델 목록
  getProviderModels: async (provider: LLMProvider): Promise<AvailableModel[]> => {
    const response = await api.get(`/available-models/${provider}`);
    // 서버 응답을 클라이언트 AvailableModel 형식으로 변환
    return response.data.map((serverModel: any) => ({
      id: serverModel.value || serverModel.model_type,
      name: serverModel.label || serverModel.value,    
      provider: serverModel.provider,
      model_type: serverModel.model_type,
      available: !serverModel.disabled               
    }));
  }
};