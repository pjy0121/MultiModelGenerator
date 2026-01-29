import { create } from 'zustand';
import { WorkflowEdge } from '../types';

interface NodeSelectionState {
  // Selected node (for edge highlighting)
  selectedNodeId: string | null;

  // Actions
  setSelectedNodeId: (nodeId: string | null) => void;
  getSelectedNodeEdges: (edges: WorkflowEdge[]) => WorkflowEdge[];
}

/**
 * Node selection state management store
 */
export const useNodeSelectionStore = create<NodeSelectionState>((set, get) => ({
  selectedNodeId: null,

  setSelectedNodeId: (nodeId) => set({ selectedNodeId: nodeId }),

  // Return edges associated with selected node (incoming edge + outgoing edge)
  getSelectedNodeEdges: (edges) => {
    const { selectedNodeId } = get();
    if (!selectedNodeId) return [];

    return edges.filter(edge =>
      edge.source === selectedNodeId || edge.target === selectedNodeId
    );
  },
}));
