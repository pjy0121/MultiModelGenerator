import axios from 'axios';
import { 
  KnowledgeBase, 
  AvailableModel, 
  LLMProvider,
  WorkflowExecutionRequest 
} from '../types';
import { API_CONFIG } from '../config/constants';

export const api = axios.create({
  baseURL: API_CONFIG.BASE_URL,
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
  // 노드 기반 워크플로우 스트리밍 실행
  executeNodeWorkflowStream: async function* (request: WorkflowExecutionRequest) {
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.EXECUTE_WORKFLOW_STREAM}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        // SSE 형식 파싱
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              yield data;
            } catch (e) {
              console.error('JSON parse error:', e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },
  
  // 워크플로우 중단
  stopWorkflowExecution: async (executionId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.STOP_WORKFLOW}/${executionId}`);
    return response.data;
  }
};

// ==================== 기본 데이터 API ====================

export const workflowAPI = {
  // 지식 베이스 목록 조회
  getKnowledgeBases: async (): Promise<KnowledgeBase[]> => {
    const response = await api.get(API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES);
    return response.data.knowledge_bases;
  },

  // Provider별 모델 목록
  getProviderModels: async (provider: LLMProvider): Promise<AvailableModel[]> => {
    const response = await api.get(`${API_CONFIG.ENDPOINTS.AVAILABLE_MODELS}/${provider}`);
    // 서버 응답이 이미 클라이언트 형식과 일치하므로 그대로 반환
    return response.data;
  }
};