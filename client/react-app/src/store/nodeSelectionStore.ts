import { create } from 'zustand';
import { WorkflowEdge } from '../types';

interface NodeSelectionState {
  // 선택된 노드 (edge 강조를 위해)
  selectedNodeId: string | null;
  
  // 액션들
  setSelectedNodeId: (nodeId: string | null) => void;
  getSelectedNodeEdges: (edges: WorkflowEdge[]) => WorkflowEdge[];
}

/**
 * 노드 선택 상태 관리 스토어
 */
export const useNodeSelectionStore = create<NodeSelectionState>((set, get) => ({
  selectedNodeId: null,
  
  setSelectedNodeId: (nodeId) => set({ selectedNodeId: nodeId }),
  
  // 선택된 노드와 연관된 edges 반환 (들어오는 edge + 나가는 edge)
  getSelectedNodeEdges: (edges) => {
    const { selectedNodeId } = get();
    if (!selectedNodeId) return [];
    
    return edges.filter(edge => 
      edge.source === selectedNodeId || edge.target === selectedNodeId
    );
  },
}));