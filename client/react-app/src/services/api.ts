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
  },

  // 지식 베이스 삭제
  deleteKnowledgeBase: async (kbName: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/delete`, { kb_name: kbName });
    return response.data;
  },

  // 지식 베이스 이름 변경
  renameKnowledgeBase: async (oldName: string, newName: string): Promise<{ success: boolean; message: string; old_name: string; new_name: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/rename`, { old_name: oldName, new_name: newName });
    return response.data;
  },

  // 지식 베이스 이동
  moveKnowledgeBase: async (kbName: string, targetFolder: string): Promise<{ success: boolean; message: string; old_path: string; new_path: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/move`, { kb_name: kbName, target_folder: targetFolder });
    return response.data;
  },

  // 지식 베이스 디렉토리 구조 조회
  getKnowledgeBaseStructure: async (): Promise<{ structure: Record<string, any> }> => {
    const response = await api.get(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/structure`);
    return response.data;
  },

  // 폴더 생성
  createFolder: async (folderPath: string): Promise<{ success: boolean; message: string; folder_path: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/create-folder`, { folder_path: folderPath });
    return response.data;
  },

  // 폴더 삭제
  deleteFolder: async (folderPath: string): Promise<{ success: boolean; message: string; folder_path: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/delete-folder`, { folder_path: folderPath });
    return response.data;
  },

  // 폴더 이름 변경
  renameFolder: async (oldPath: string, newName: string): Promise<{ success: boolean; message: string; old_path: string; new_path: string }> => {
    const response = await api.put(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/rename-folder`, { old_path: oldPath, new_name: newName });
    return response.data;
  },

  // 폴더 이동
  moveFolder: async (oldPath: string, targetFolder: string): Promise<{ success: boolean; message: string; old_path: string; new_path: string }> => {
    const response = await api.put(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/move-folder`, { old_path: oldPath, target_folder: targetFolder });
    return response.data;
  },

  // 지식 베이스 생성 (BGE-M3 최적화)
  createKnowledgeBase: async (
    kbName: string, 
    chunkType: 'keyword' | 'sentence' | 'custom' | 'bge-m3',  // bge-m3: BGE-M3 최적화 모드 (백엔드에서 고정값 사용)
    contentBase64: string,
    contentType: 'base64' | 'plain' | 'file',
    fileType?: 'pdf' | 'txt',
    chunkSize?: number,
    chunkOverlap?: number,
    targetFolder?: string
  ): Promise<{ success: boolean; message: string; kb_name: string }> => {
    const payload: any = {
      kb_name: kbName,
      chunk_type: chunkType,
      chunk_size: chunkSize,
      chunk_overlap: chunkOverlap,
      target_folder: targetFolder
    };
    
    if (contentType === 'file') {
      payload.file_content = contentBase64;
      payload.file_type = fileType || 'pdf';
    } else {
      payload.text_content = contentBase64;
      payload.text_type = contentType;  // 'base64' or 'plain'
    }
    
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/create`, payload);
    return response.data;
  },

  // 🔒 폴더 보호 설정
  protectFolder: async (folderPath: string, password: string, reason?: string): Promise<{ success: boolean; message: string; folder_path: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/protect-folder`, { 
      folder_path: folderPath, 
      password: password,
      reason: reason || ''
    });
    return response.data;
  },

  // 🔓 폴더 보호 해제
  unprotectFolder: async (folderPath: string, password: string): Promise<{ success: boolean; message: string; folder_path: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/unprotect-folder`, { 
      folder_path: folderPath, 
      password: password
    });
    return response.data;
  },

  // 🔒 지식 베이스 보호 설정
  protectKnowledgeBase: async (kbName: string, password: string, reason?: string): Promise<{ success: boolean; message: string; kb_name: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/protect`, { 
      kb_name: kbName, 
      password: password,
      reason: reason || ''
    });
    return response.data;
  },

  // 🔓 지식 베이스 보호 해제
  unprotectKnowledgeBase: async (kbName: string, password: string): Promise<{ success: boolean; message: string; kb_name: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/unprotect`, { 
      kb_name: kbName, 
      password: password
    });
    return response.data;
  }
};