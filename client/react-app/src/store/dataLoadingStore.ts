import { create } from 'zustand';
import { AvailableModel, KnowledgeBase, LLMProvider } from '../types';
import { workflowAPI } from '../services/api';
import { showErrorMessage } from '../utils/messageUtils';

interface DataLoadingState {
  // Model management
  availableModels: AvailableModel[];
  knowledgeBases: KnowledgeBase[];

  // Actions
  loadKnowledgeBases: () => Promise<void>;
  loadAvailableModels: (provider: LLMProvider) => Promise<void>;
}

/**
 * Data loading state management store (models, knowledge bases)
 */
export const useDataLoadingStore = create<DataLoadingState>((set, get) => ({
  availableModels: [],
  knowledgeBases: [],

  // Data loading
  loadKnowledgeBases: async () => {
    try {
      const knowledgeBases = await workflowAPI.getKnowledgeBases();
      set({ knowledgeBases });
    } catch (error) {
      console.error('Knowledge base loading failed:', error);
    }
  },

  loadAvailableModels: async (provider: LLMProvider) => {
    try {
      const models = await workflowAPI.getProviderModels(provider);
      const state = get();

      // Keep models from other providers, only replace models for this provider
      const otherProviderModels = state.availableModels.filter(model => model.provider !== provider);
      const updatedModels = [...otherProviderModels, ...models];

      set({ availableModels: updatedModels });
    } catch (error) {
      console.error(`${provider} model list loading failed:`, error);

      // On failure, remove models for this provider
      const state = get();
      const otherProviderModels = state.availableModels.filter(model => model.provider !== provider);
      set({ availableModels: otherProviderModels });

      // Notify user
      showErrorMessage(`Failed to load ${provider} model list. Please check connection status.`);
    }
  },
}));
