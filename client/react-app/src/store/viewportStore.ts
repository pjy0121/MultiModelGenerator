import { create } from 'zustand';

interface ViewportState {
  // ReactFlow 뷰포트 상태
  viewport: { x: number; y: number; zoom: number };
  isRestoring: boolean; // 복원 상태 플래그
  
  // 액션들
  setViewport: (viewport: { x: number; y: number; zoom: number }) => void;
  setRestoring: (isRestoring: boolean) => void;
}

/**
 * 뷰포트 상태 관리 스토어
 */
export const useViewportStore = create<ViewportState>((set) => ({
  viewport: { x: 0, y: 0, zoom: 1 },
  isRestoring: false,
  
  setViewport: (viewport) => set({ viewport }),
  setRestoring: (isRestoring) => set({ isRestoring }),
}));