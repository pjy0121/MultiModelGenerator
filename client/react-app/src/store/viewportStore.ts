import { create } from 'zustand';

interface ViewportState {
  // ReactFlow viewport state
  viewport: { x: number; y: number; zoom: number };
  isRestoring: boolean; // Restoration state flag

  // Actions
  setViewport: (viewport: { x: number; y: number; zoom: number }) => void;
  setRestoring: (isRestoring: boolean) => void;
}

/**
 * Viewport state management store
 */
export const useViewportStore = create<ViewportState>((set) => ({
  viewport: { x: 0, y: 0, zoom: 1 },
  isRestoring: false,

  setViewport: (viewport) => set({ viewport }),
  setRestoring: (isRestoring) => set({ isRestoring }),
}));
