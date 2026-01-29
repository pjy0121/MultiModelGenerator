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

// ==================== Node-based Workflow API ====================

export const nodeBasedWorkflowAPI = {
  // Node-based workflow streaming execution
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

        // Parse SSE format
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

  // Stop workflow execution
  stopWorkflowExecution: async (executionId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.STOP_WORKFLOW}/${executionId}`);
    return response.data;
  }
};

// ==================== Base Data API ====================

export const workflowAPI = {
  // Get knowledge bases list
  getKnowledgeBases: async (): Promise<KnowledgeBase[]> => {
    const response = await api.get(API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES);
    return response.data.knowledge_bases;
  },

  // Get models by provider
  getProviderModels: async (provider: LLMProvider): Promise<AvailableModel[]> => {
    const response = await api.get(`${API_CONFIG.ENDPOINTS.AVAILABLE_MODELS}/${provider}`);
    // Server response already matches client format, return as-is
    return response.data;
  },

  // Delete knowledge base
  deleteKnowledgeBase: async (kbName: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/delete`, { kb_name: kbName });
    return response.data;
  },

  // Rename knowledge base
  renameKnowledgeBase: async (oldName: string, newName: string): Promise<{ success: boolean; message: string; old_name: string; new_name: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/rename`, { old_name: oldName, new_name: newName });
    return response.data;
  },

  // Move knowledge base
  moveKnowledgeBase: async (kbName: string, targetFolder: string): Promise<{ success: boolean; message: string; old_path: string; new_path: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/move`, { kb_name: kbName, target_folder: targetFolder });
    return response.data;
  },

  // Get knowledge base directory structure
  getKnowledgeBaseStructure: async (): Promise<{ structure: Record<string, any> }> => {
    const response = await api.get(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/structure`);
    return response.data;
  },

  // Create folder
  createFolder: async (folderPath: string): Promise<{ success: boolean; message: string; folder_path: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/create-folder`, { folder_path: folderPath });
    return response.data;
  },

  // Delete folder
  deleteFolder: async (folderPath: string): Promise<{ success: boolean; message: string; folder_path: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/delete-folder`, { folder_path: folderPath });
    return response.data;
  },

  // Rename folder
  renameFolder: async (oldPath: string, newName: string): Promise<{ success: boolean; message: string; old_path: string; new_path: string }> => {
    const response = await api.put(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/rename-folder`, { old_path: oldPath, new_name: newName });
    return response.data;
  },

  // Move folder
  moveFolder: async (oldPath: string, targetFolder: string): Promise<{ success: boolean; message: string; old_path: string; new_path: string }> => {
    const response = await api.put(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/move-folder`, { old_path: oldPath, target_folder: targetFolder });
    return response.data;
  },

  // Create knowledge base (BGE-M3 optimized)
  createKnowledgeBase: async (
    kbName: string,
    contentBase64: string,
    contentType: 'base64' | 'plain' | 'file',
    fileType?: 'pdf' | 'txt',
    chunkSize?: number,
    chunkOverlap?: number,
    targetFolder?: string
  ): Promise<{ success: boolean; message: string; kb_name: string }> => {
    const payload: any = {
      kb_name: kbName,
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

    console.log('[KB Create] Payload:', {
      kb_name: kbName,
      content_type: contentType,
      text_type: payload.text_type,
      content_length: contentBase64.length,
      chunk_size: chunkSize,
      chunk_overlap: chunkOverlap
    });

    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/create`, payload);
    return response.data;
  },

  // Set folder protection
  protectFolder: async (folderPath: string, password: string, reason?: string): Promise<{ success: boolean; message: string; folder_path: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/protect-folder`, {
      folder_path: folderPath,
      password: password,
      reason: reason || ''
    });
    return response.data;
  },

  // Remove folder protection
  unprotectFolder: async (folderPath: string, password: string): Promise<{ success: boolean; message: string; folder_path: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/unprotect-folder`, {
      folder_path: folderPath,
      password: password
    });
    return response.data;
  },

  // Set knowledge base protection
  protectKnowledgeBase: async (kbName: string, password: string, reason?: string): Promise<{ success: boolean; message: string; kb_name: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/protect`, {
      kb_name: kbName,
      password: password,
      reason: reason || ''
    });
    return response.data;
  },

  // Remove knowledge base protection
  unprotectKnowledgeBase: async (kbName: string, password: string): Promise<{ success: boolean; message: string; kb_name: string }> => {
    const response = await api.post(`${API_CONFIG.ENDPOINTS.KNOWLEDGE_BASES}/unprotect`, {
      kb_name: kbName,
      password: password
    });
    return response.data;
  }
};
