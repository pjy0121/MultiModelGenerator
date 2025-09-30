import { create } from 'zustand';
import { AvailableModel, KnowledgeBase, LLMProvider } from '../types';
import { workflowAPI } from '../services/api';
import { showErrorMessage } from '../utils/messageUtils';

interface DataLoadingState {
  // 모델 관리
  availableModels: AvailableModel[];
  knowledgeBases: KnowledgeBase[];
  
  // 액션들
  loadKnowledgeBases: () => Promise<void>;
  loadAvailableModels: (provider: LLMProvider) => Promise<void>;
}

/**
 * 데이터 로딩 상태 관리 스토어 (모델, 지식베이스)
 */
export const useDataLoadingStore = create<DataLoadingState>((set, get) => ({
  availableModels: [],
  knowledgeBases: [],
  
  // 데이터 로딩
  loadKnowledgeBases: async () => {
    try {
      const knowledgeBases = await workflowAPI.getKnowledgeBases();
      set({ knowledgeBases });
    } catch (error) {
      console.error('지식 베이스 로딩 실패:', error);
    }
  },
  
  loadAvailableModels: async (provider: LLMProvider) => {
    try {
      const models = await workflowAPI.getProviderModels(provider);
      const state = get();
      
      // 기존 모델 중 다른 provider 모델들은 유지하고, 해당 provider 모델만 교체
      const otherProviderModels = state.availableModels.filter(model => model.provider !== provider);
      const updatedModels = [...otherProviderModels, ...models];
      
      set({ availableModels: updatedModels });
    } catch (error) {
      console.error(`${provider} 모델 목록 로딩 실패:`, error);
      
      // 실패 시 해당 provider의 모델들을 제거
      const state = get();
      const otherProviderModels = state.availableModels.filter(model => model.provider !== provider);
      set({ availableModels: otherProviderModels });
      
      // 사용자에게 알림
      showErrorMessage(`${provider} 모델 목록을 불러오는데 실패했습니다. 연결 상태를 확인해주세요.`);
    }
  },
}));