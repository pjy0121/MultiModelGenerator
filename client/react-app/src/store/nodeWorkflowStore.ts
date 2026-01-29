import { create } from 'zustand';
import { message } from 'antd';
import {
  NodeType,
  LLMProvider,
  SearchIntensity,
  WorkflowNode,
  WorkflowEdge,
  NodeData,
  NodeBasedWorkflowResponse,
  ValidationResult,
  StreamChunk
} from '../types';
import { showSuccessMessage, showErrorMessage } from '../utils/messageUtils';
import { nodeBasedWorkflowAPI } from '../services/api';
import { validateNodeWorkflow, formatValidationErrors } from '../utils/nodeWorkflowValidation';
import { createWorkflowNode, createInitialNodes } from '../utils/nodeFactory';

// ==================== Node-based Workflow Store ====================
// Based on project_reference.md - supports 5 node types only

interface NodeWorkflowState {
  // Workflow configuration
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];

  // ReactFlow viewport state (deduplication: only viewport maintained)
  viewport: { x: number; y: number; zoom: number };
  isRestoring: boolean; // Restoration state flag

  // Execution state
  isExecuting: boolean;
  isStopping: boolean; // Workflow stopping state
  currentExecutionId: string | null; // ID of currently executing workflow
  executionResult: NodeBasedWorkflowResponse | null;

  // Node execution states and streaming outputs
  nodeExecutionStates: Record<string, 'idle' | 'executing' | 'completed' | 'error'>;
  nodeStreamingOutputs: Record<string, string>;
  nodeExecutionResults: Record<string, { success: boolean; description?: string; error?: string; execution_time?: number; }>;
  nodeStartOrder: string[]; // Track node execution start order

  // Page visibility state (for limiting streaming updates when in background)
  isPageVisible: boolean;

  // Accumulated streaming outputs in background (applied when page becomes visible)
  pendingStreamingOutputs: Record<string, string>;

  // Validation state
  validationResult: ValidationResult | null;
  validationErrors: string[];

  // Error message management
  persistentErrors: Array<{ id: string; message: string; timestamp: number }>;

  // Node execution status update
  setNodeExecutionStatus: (nodeId: string, isExecuting: boolean, isCompleted?: boolean) => void;

  // Actions
  addNode: (nodeType: NodeType, position: { x: number; y: number }) => void;
  updateNode: (nodeId: string, updates: Partial<NodeData>) => void;
  removeNode: (nodeId: string) => void;
  addEdge: (edge: WorkflowEdge) => void;
  removeEdge: (edgeId: string) => void;

  validateWorkflow: () => boolean;
  getValidationErrors: () => string[];

  executeWorkflowStream: (onStreamUpdate: (data: StreamChunk) => void) => Promise<void>;
  stopWorkflowExecution: () => void;
  clearAllExecutionResults: () => void;

  // Viewport state management
  setViewport: (viewport: { x: number; y: number; zoom: number }) => void;

  // Node position update
  updateNodePositions: (nodePositions: { id: string; position: { x: number; y: number } }[]) => void;

  // Workflow save/restore/Import/Export functions
  saveCurrentWorkflow: () => void;
  restoreWorkflow: () => boolean;
  resetToInitialState: () => void;
  exportToJSON: () => void;
  importFromJSON: (jsonData: string) => boolean;
  setRestoring: (isRestoring: boolean) => void;

  // Page visibility state management
  setPageVisible: (isVisible: boolean) => void;

  // Error message management functions
  addPersistentError: (errorMessage: string) => void;
  removePersistentError: (id: string) => void;
  clearAllPersistentErrors: () => void;
}

export const useNodeWorkflowStore = create<NodeWorkflowState>((set, get) => {
  // Create initial nodes (without connections)
  const initialNodes = createInitialNodes();

  return {
    // Initial state - input-node and output-node are created by default (no connections)
    nodes: initialNodes,
    edges: [],

    viewport: { x: 0, y: 0, zoom: 1 },
    isRestoring: false, // Restoration state initial value

    isExecuting: false,
    isStopping: false, // Stopping state initial value
    currentExecutionId: null, // Execution ID initial value
    executionResult: null,

    validationResult: null,
    validationErrors: [],

    // Error message management
    persistentErrors: [],

    // Node execution states and outputs
    nodeExecutionStates: {},
    nodeStreamingOutputs: {},
    nodeExecutionResults: {},
    nodeStartOrder: [], // Node execution start order

    isPageVisible: true, // Page visibility initial value
    pendingStreamingOutputs: {}, // Accumulated streaming outputs initial value

    setRestoring: (isRestoring: boolean) => set({ isRestoring }),

  // Node management actions
  addNode: async (nodeType: NodeType, position: { x: number; y: number }) => {
    // Only one output-node can exist
    if (nodeType === NodeType.OUTPUT) {
      const state = get();
      const hasOutputNode = state.nodes.some(node => node.data.nodeType === NodeType.OUTPUT);
      if (hasOutputNode) {
        throw new Error('Only one output node can exist.');
      }
    }

    // Only Output node uses fixed position
    let nodePosition = position;
    if (nodeType === NodeType.OUTPUT) {
      nodePosition = { x: 400, y: 550 }; // Fixed at bottom center
    }

    const newNode = createWorkflowNode(nodeType, nodePosition);

    // First add the node
    set(_ => ({
      nodes: get().nodes.concat(newNode)
    }));

    // Set default provider and model for LLM nodes
    if ([NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(nodeType)) {
      const state = get();
      state.updateNode(newNode.id, {
        llm_provider: LLMProvider.GOOGLE,
        model_type: 'gemini-2.0-flash-lite' // Default model setting
      });
      showSuccessMessage(`${nodeType} node created. Change model in edit if needed.`);
    }

    // Set default search intensity and rerank for Context node
    if (nodeType === NodeType.CONTEXT) {
      const state = get();
      state.updateNode(newNode.id, {
        search_intensity: SearchIntensity.STANDARD,
        rerank_provider: LLMProvider.NONE // Default: no reranking
      });
      message.success(`${nodeType} node created. Please select a knowledge base.`);
    }
  },

  updateNode: (nodeId, updates) => {
    set(state => ({
      nodes: state.nodes.map(node =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...updates } }
          : node
      ),
    }));
  },

  removeNode: (nodeId) => {
    const nodeToRemove = get().nodes.find(n => n.id === nodeId);

    if (!nodeToRemove) return;

    // Output-node cannot be deleted
    if (nodeToRemove.data.nodeType === NodeType.OUTPUT) {
      showErrorMessage('Output node cannot be deleted.');
      throw new Error('Output node cannot be deleted.');
    }

    // Input-node cannot be deleted if it's the last one
    if (nodeToRemove.data.nodeType === NodeType.INPUT) {
      const inputNodes = get().nodes.filter(node => node.data.nodeType === NodeType.INPUT);
      if (inputNodes.length <= 1) {
        showErrorMessage('At least one input node must exist.');
        throw new Error('At least one input node must exist.');
      }
    }

    set(state => ({
      nodes: state.nodes.filter(node => node.id !== nodeId),
      edges: state.edges.filter(edge => edge.source !== nodeId && edge.target !== nodeId)
    }));

    message.success(`${nodeToRemove.data.nodeType} node deleted.`);
  },

  addEdge: (edge: WorkflowEdge) => {
    set(state => ({
      edges: [...state.edges, edge]
    }));
  },

  removeEdge: (edgeId: string) => {
    set(state => ({
      edges: state.edges.filter(edge => edge.id !== edgeId)
    }));
  },

    setViewport: (viewport: { x: number; y: number; zoom: number }) => {
      set({ viewport });
    },  updateNodePositions: (nodePositions: { id: string; position: { x: number; y: number } }[]) => {
    set(state => ({
      nodes: state.nodes.map(node => {
        const positionUpdate = nodePositions.find(np => np.id === node.id);
        if (positionUpdate) {
          return {
            ...node,
            position: positionUpdate.position
          };
        }
        return node;
      })
    }));
  },

  // Node execution status update
  setNodeExecutionStatus: (nodeId: string, isExecuting: boolean, isCompleted?: boolean) => {
    set(state => ({
      nodes: state.nodes.map(node =>
        node.id === nodeId
          ? {
              ...node,
              data: {
                ...node.data,
                isExecuting,
                isCompleted: isCompleted ?? node.data.isCompleted
              }
            }
          : node
      )
    }));
  },
  // Validation actions
  validateWorkflow: () => {
    const { nodes, edges } = get();
    const result = validateNodeWorkflow(nodes, edges);
    const errors = result.isValid ? [] : formatValidationErrors(result.errors);

    set({
      validationResult: result,
      validationErrors: errors
    });

    return result.isValid;
  },

  getValidationErrors: () => {
    return get().validationErrors;
  },

  // Workflow streaming execution (the only execution method)
  executeWorkflowStream: async (onStreamUpdate: (data: StreamChunk) => void) => {
    const state = get();

    // Pre-execution validation - provide specific error messages
    if (!state.validateWorkflow()) {
      const errors = state.getValidationErrors();
      const detailedMessage = errors.length > 0
        ? `Workflow validation failed:\n${errors.join('\n')}`
        : 'Workflow validation failed. Please check connection rules.';

      console.error('Workflow validation failed:', errors);
      throw new Error(detailedMessage);
    }

    set({ isExecuting: true, executionResult: null, currentExecutionId: null });

    try {
      // Convert to WorkflowExecutionRequest format expected by server
      const workflowDefinition = {
        nodes: state.nodes.map(node => {
          const isLlmNode = [NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(node.data.nodeType);
          let finalPrompt = node.data.prompt || '';

          if (isLlmNode && node.data.output_format) {
            const outputFormatInstruction = `\n\nYou must include key results in the following format at the beginning of your output. This is an absolute requirement.\n\n<output>\n${node.data.output_format}\n</output>`;
            finalPrompt += outputFormatInstruction;
          }

          return {
            id: node.id,
            type: node.data.nodeType,
            position: node.position,
            content: node.data.content || null,
            model_type: node.data.model_type || null,
            llm_provider: node.data.llm_provider || null,
            prompt: finalPrompt,
            knowledge_base: node.data.knowledge_base || null,
            search_intensity: node.data.search_intensity || null,
            rerank_provider: node.data.rerank_provider || null,
            additional_context: node.data.additional_context || null,

            output: null,
            executed: false,
            error: null
          };
        }),
        edges: state.edges
      };

      const request = {
        workflow: workflowDefinition,
      };

      // Initialize - set all nodes to idle state
      const initialStates: Record<string, 'idle' | 'executing' | 'completed' | 'error'> = {};
      const initialOutputs: Record<string, string> = {};
      const initialResults: Record<string, { success: boolean; description?: string; error?: string; execution_time?: number; }> = {};

      state.nodes.forEach(node => {
        initialStates[node.id] = 'idle';
        initialOutputs[node.id] = '';
        initialResults[node.id] = { success: false };
      });

      set({
        nodeExecutionStates: initialStates,
        nodeStreamingOutputs: initialOutputs,
        nodeExecutionResults: initialResults,
        nodeStartOrder: [], // Initialize at streaming execution start
        pendingStreamingOutputs: {} // Also initialize accumulated outputs
      });

      // Streaming update batch processing variables - prevent React infinite loop
      let streamBatch: Record<string, string> = {};
      let pendingBatch: Record<string, string> = {};
      let batchTimeout: number | null = null;
      let lastFlushTime = 0;
      const MIN_FLUSH_INTERVAL = 50; // 20 FPS (50ms) - stronger throttling

      // Batch flush function - prevent React update depth exceeded
      const flushBatch = () => {
        const now = Date.now();
        if (now - lastFlushTime < MIN_FLUSH_INTERVAL) {
          return; // Prevent too frequent updates
        }

        if (Object.keys(streamBatch).length > 0 || Object.keys(pendingBatch).length > 0) {
          set(state => {
            let hasChanges = false;
            let newStreamingOutputs = { ...state.nodeStreamingOutputs };
            let newPendingOutputs = { ...state.pendingStreamingOutputs };

            // Apply stream batch
            Object.keys(streamBatch).forEach(nodeId => {
              const currentOutput = state.nodeStreamingOutputs[nodeId] || '';
              const newOutput = streamBatch[nodeId];
              if (currentOutput !== newOutput) {
                newStreamingOutputs[nodeId] = newOutput;
                hasChanges = true;
              }
            });

            // Apply pending batch
            Object.keys(pendingBatch).forEach(nodeId => {
              const currentPending = state.pendingStreamingOutputs[nodeId] || '';
              const newPending = pendingBatch[nodeId];
              if (currentPending !== newPending) {
                newPendingOutputs[nodeId] = newPending;
                hasChanges = true;
              }
            });

            if (!hasChanges) {
              return state; // Prevent re-render if no changes
            }

            return {
              ...state,
              nodeStreamingOutputs: newStreamingOutputs,
              pendingStreamingOutputs: newPendingOutputs
            };
          });

          // Reset batch
          streamBatch = {};
          pendingBatch = {};
          lastFlushTime = now;
        }
        batchTimeout = null;
      };

      // Streaming execution
      for await (const chunk of nodeBasedWorkflowAPI.executeNodeWorkflowStream(request)) {
        onStreamUpdate(chunk);

        // Receive and store execution_id
        if (chunk.type === 'execution_started' && chunk.execution_id) {
          set({ currentExecutionId: chunk.execution_id });
          console.log('Execution ID received:', chunk.execution_id);
        }

        // Handle validation_error type
        if (chunk.type === 'validation_error') {
          const validationErrors = chunk.errors || ['Unknown validation error'];
          const detailedMessage = `Backend workflow validation failed:\n${validationErrors.map((error: string, index: number) => `${index + 1}. ${error}`).join('\n')}`;

          console.error('Backend validation failed:', validationErrors);
          throw new Error(detailedMessage);
        }

        // Handle stop request event
        if (chunk.type === 'stop_requested') {
          console.log('Server confirmed stop request:', chunk.message);
          // isStopping is already set to true, no additional processing needed
        }

        // Node state update - prevent infinite loop when page is in background
        if (chunk.type === 'node_start' && chunk.node_id) {
          set(state => {
            const currentStartOrder = state.nodeStartOrder;
            const isAlreadyStarted = currentStartOrder.includes(chunk.node_id);
            const isAlreadyExecuting = state.nodeExecutionStates[chunk.node_id] === 'executing';

            // No state change if already executing and in start order
            if (isAlreadyExecuting && isAlreadyStarted) {
              return state;
            }

            return {
              ...state,
              nodeExecutionStates: {
                ...state.nodeExecutionStates,
                [chunk.node_id]: 'executing'
              },
              nodeStartOrder: isAlreadyStarted
                ? currentStartOrder
                : [...currentStartOrder, chunk.node_id]
            };
          });
        } else if (chunk.type === 'stream' && chunk.node_id && chunk.content) {
          // Accumulate streaming content to batch - minimize get() calls to prevent infinite loop
          if (!streamBatch[chunk.node_id]) {
            // Only get current state for first chunk
            const currentState = get();
            const baseOutput = currentState.isPageVisible
              ? (currentState.nodeStreamingOutputs[chunk.node_id] || '')
              : (currentState.pendingStreamingOutputs[chunk.node_id] || '');

            if (currentState.isPageVisible) {
              streamBatch[chunk.node_id] = baseOutput + chunk.content;
            } else {
              pendingBatch[chunk.node_id] = baseOutput + chunk.content;
            }
          } else {
            // Subsequent chunks only accumulate to batch (no get() call)
            if (streamBatch[chunk.node_id] !== undefined) {
              streamBatch[chunk.node_id] += chunk.content;
            } else if (pendingBatch[chunk.node_id] !== undefined) {
              pendingBatch[chunk.node_id] += chunk.content;
            } else {
              // fallback: check current state
              const currentState = get();
              if (currentState.isPageVisible) {
                streamBatch[chunk.node_id] = (currentState.nodeStreamingOutputs[chunk.node_id] || '') + chunk.content;
              } else {
                pendingBatch[chunk.node_id] = (currentState.pendingStreamingOutputs[chunk.node_id] || '') + chunk.content;
              }
            }
          }

          // Schedule batch update (throttled)
          if (batchTimeout) {
            clearTimeout(batchTimeout);
          }
          batchTimeout = setTimeout(flushBatch, MIN_FLUSH_INTERVAL);
        } else if (chunk.type === 'node_complete' && chunk.node_id) {
          const status = chunk.success ? 'completed' : 'error';

          set(state => {
            // Prevent duplicate update if already completed
            const currentStatus = state.nodeExecutionStates[chunk.node_id];
            if (currentStatus === status) {
              return state;
            }

            // Preserve streaming output received so far even on failure
            const currentStreamingOutput = state.nodeStreamingOutputs[chunk.node_id] || '';

            // If failed but has streaming output, only add error message
            const description = chunk.description || (chunk.success ? '' : chunk.error);
            const finalDescription = !chunk.success && currentStreamingOutput
              ? `${currentStreamingOutput}\n\n[Error] ${description}`
              : description;

            // Immediately save completion results for all nodes (regardless of success/failure)
            const updatedResults = {
              ...state.nodeExecutionResults,
              [chunk.node_id]: {
                success: chunk.success,
                description: finalDescription,
                error: chunk.success ? undefined : chunk.error,
                execution_time: chunk.execution_time
              }
            };

            return {
              ...state,
              nodeExecutionStates: {
                ...state.nodeExecutionStates,
                [chunk.node_id]: status
              },
              nodeExecutionResults: updatedResults
              // nodeStreamingOutputs is not explicitly deleted so it's preserved
            };
          });
        }

        // Save results on completion
        if (chunk.type === 'complete') {
          // Update nodeExecutionResults with actual node execution results
          const nodeResults: Record<string, { success: boolean; description?: string; error?: string; execution_time?: number }> = {};
          if (chunk.results && Array.isArray(chunk.results)) {
            chunk.results.forEach((result: { node_id?: string; success: boolean; description?: string; error?: string; execution_time?: number }) => {
              if (result.node_id) {
                nodeResults[result.node_id] = {
                  success: result.success,
                  description: result.description, // Actual node execution result
                  error: result.error,
                  execution_time: result.execution_time
                };
              }
            });
          }

          // Set all completed nodes' state to completed
          const completedStates: Record<string, 'idle' | 'executing' | 'completed' | 'error'> = {};
          if (chunk.results && Array.isArray(chunk.results)) {
            chunk.results.forEach((result: { node_id?: string; success: boolean }) => {
              if (result.node_id) {
                completedStates[result.node_id] = result.success ? 'completed' : 'error';
              }
            });
          }

          // Check stopping state (before state update)
          const currentState = get();
          const wasStopping = currentState.isStopping;
          const serverWasStopped = chunk.was_stopped; // Stop info from server

          set(state => ({
            executionResult: {
              success: chunk.success,
              results: chunk.results || [],
              final_output: chunk.final_output,
              total_execution_time: chunk.total_execution_time,
              execution_order: chunk.execution_order || [],
              error: chunk.error
            },
            nodeExecutionResults: {
              ...state.nodeExecutionResults,
              ...nodeResults // Update with actual execution results
            },
            nodeExecutionStates: {
              ...state.nodeExecutionStates,
              ...completedStates // Update completed node states
            },
            isExecuting: false,
            isStopping: false, // Clear stopping state on workflow completion
            currentExecutionId: null // Clear execution ID
          }));

          // Processing complete if there was a stop request
          if (wasStopping || serverWasStopped) {
            message.success('Workflow stopped. All outputs from executing nodes have been completed.');
          }

          // WorkflowComplete processing complete, don't execute finally block
          return;
        } else if (chunk.type === 'error') {
          // On error, only reset executing nodes to idle, keep completed nodes
          const state = get();
          const updatedStates = { ...state.nodeExecutionStates };

          // Only reset executing nodes to idle
          Object.keys(updatedStates).forEach(nodeId => {
            if (updatedStates[nodeId] === 'executing') {
              updatedStates[nodeId] = 'idle';
            }
          });

          set({
            isExecuting: false,
            nodeExecutionStates: updatedStates
            // Keep completed nodes' results and outputs
          });
        }
      }

      // Flush remaining batch updates when streaming completes
      if (batchTimeout) {
        clearTimeout(batchTimeout);
      }
      flushBatch();

    } catch (error: unknown) {
      console.error('Streaming workflow execution error:', error);

      // On error, only reset executing nodes to idle, keep completed nodes
      const state = get();
      const updatedStates = { ...state.nodeExecutionStates };

      // Only reset executing nodes to idle
      Object.keys(updatedStates).forEach(nodeId => {
        if (updatedStates[nodeId] === 'executing') {
          updatedStates[nodeId] = 'idle';
        }
      });

      set({
        isExecuting: false,
        nodeExecutionStates: updatedStates,
        currentExecutionId: null // Clear on error too
        // Keep completed nodes' results and outputs
      });

      let errorMessage = 'An unknown error occurred.';
      if (error instanceof Error && error.message) {
        errorMessage = error.message;
      }

      // Display as persistent error and don't throw to prevent infinite loop
      // Can't directly access store methods so use message.error
      const id = `execution-error-${Date.now()}`;
      message.error({
        content: `Streaming execution error: ${errorMessage}`,
        duration: 0, // Won't disappear
        key: id,
        onClick: () => {
          message.destroy(id);
        }
      });
    } finally {
      // Check stopping state (before state cleanup)
      const currentState = get();
      const wasStopping = currentState.isStopping;

      // Clean up execution and stopping states
      set({
        isExecuting: false,
        isStopping: false,
        currentExecutionId: null // Cleanup
      });

      // Show message if stopped
      if (wasStopping) {
        message.success('Workflow stopped. All outputs from executing nodes have been completed.');
      }
    }
  },

  stopWorkflowExecution: async () => {
    // Manually stop workflow execution
    const state = get();
    if (!state.isExecuting || state.isStopping) return;

    const executionId = state.currentExecutionId;
    if (!executionId) {
      showErrorMessage('Execution ID not found.');
      return;
    }

    // Transition to stopping state
    set({ isStopping: true });

    try {
      // Send stop request to server
      const result = await nodeBasedWorkflowAPI.stopWorkflowExecution(executionId);
      message.info(result.message || 'Workflow stop request sent.');
    } catch (error) {
      console.error('Workflow stop request failed:', error);
      showErrorMessage('Failed to send workflow stop request.');
      // Release stopping state on failure
      set({ isStopping: false });
    }
  },

  clearAllExecutionResults: () => {
    // Completely reset all execution results (user intentionally selected)
    const state = get();
    const resetStates: Record<string, 'idle' | 'executing' | 'completed' | 'error'> = {};
    const resetOutputs: Record<string, string> = {};
    const resetResults: Record<string, { success: boolean; description?: string; error?: string; execution_time?: number; }> = {};

    state.nodes.forEach(node => {
      resetStates[node.id] = 'idle';
      resetOutputs[node.id] = '';
      resetResults[node.id] = { success: false };
    });

    set({
      isExecuting: false,
      nodeExecutionStates: resetStates,
      nodeStreamingOutputs: resetOutputs,
      nodeExecutionResults: resetResults,
      nodeStartOrder: [],
      executionResult: null,
      pendingStreamingOutputs: {} // Also reset accumulated outputs
    });

    message.success('All execution results have been reset.');
  },

  // Data loading
  // Workflow save/restore/Import/Export function implementations
  saveCurrentWorkflow: () => {
    const { nodes, edges, viewport } = get();
    const workflowState = {
      nodes,
      edges,
      viewport, // Save current viewport state
      savedAt: new Date().toISOString(),
      version: '1.1' // Version update
    };

    try {
      localStorage.setItem('node_workflow_state', JSON.stringify(workflowState));
    } catch (error) {
      console.error('Workflow save failed:', error);
      showErrorMessage('Failed to save workflow.');
    }
  },

  restoreWorkflow: () => {
    try {
      const savedState = localStorage.getItem('node_workflow_state');
      if (!savedState) return false;

      const workflowState = JSON.parse(savedState);
      const savedViewport = workflowState.viewport || { x: 0, y: 0, zoom: 1 };

      set({
        nodes: workflowState.nodes || [],
        edges: workflowState.edges || [],
        viewport: savedViewport,
        // viewport is already set above
        // Reset execution-related states
        isExecuting: false,
        executionResult: null,
        nodeExecutionStates: {},
        nodeStreamingOutputs: {},
        nodeExecutionResults: {},
        validationResult: null,
        validationErrors: [],
        isRestoring: true, // Start restoration
      });

      // Set isRestoring to false after restoration completes
      setTimeout(() => set({ isRestoring: false }), 100);

      return true;

    } catch (error) {
      console.error('Workflow restoration failed:', error);
      showErrorMessage('Failed to restore workflow.');
      set({ isRestoring: false }); // Release restoration state on error
      return false;
    }
  },

  resetToInitialState: () => {
    const initialNodes = createInitialNodes();
    const initialViewport = { x: 0, y: 0, zoom: 1 }; // Adjusted so nodes are centered
    set({
      nodes: initialNodes,
      edges: [],
      viewport: initialViewport,
      // viewport is already set above
      // Reset execution-related states
      isExecuting: false,
      executionResult: null,
      nodeExecutionStates: {},
      nodeStreamingOutputs: {},
      nodeExecutionResults: {},
      validationResult: null,
      validationErrors: []
    });
  },

  exportToJSON: () => {
    const { nodes, edges, viewport } = get();
    const exportData = {
      version: '1.1', // Version update
      exportedAt: new Date().toISOString(),
      workflow: {
        nodes,
        edges,
        viewport,
      }
    };

    try {
      const jsonString = JSON.stringify(exportData, null, 2);
      const blob = new Blob([jsonString], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `workflow_${new Date().toISOString()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('Workflow exported to file.');
    } catch (error) {
      console.error('Workflow export failed:', error);
      showErrorMessage('Failed to export workflow.');
    }
  },

  importFromJSON: (jsonData: string) => {
    try {
      const workflowData = JSON.parse(jsonData);

      // Extract node and edge data
      let nodes = workflowData.nodes || workflowData.workflow?.nodes || [];
      let edges = workflowData.edges || workflowData.workflow?.edges || [];
      const viewport = workflowData.viewport || workflowData.workflow?.viewport || { x: 0, y: 0, zoom: 1 };

      // Validate and normalize node data
      if (!Array.isArray(nodes)) {
        throw new Error('No node information in JSON data.');
      }
      if (!Array.isArray(edges)) {
        throw new Error('No edge information in JSON data.');
      }

      // Update workflow state
      set({
        nodes,
        edges,
        viewport,
        // viewport is already set
        // Reset execution-related states
        isExecuting: false,
        executionResult: null,
        nodeExecutionStates: {},
        nodeStreamingOutputs: {},
        nodeExecutionResults: {},
        validationResult: null,
        validationErrors: [],
        isRestoring: true, // Start restoration
      });

      // Set isRestoring to false after restoration completes
      setTimeout(() => set({ isRestoring: false }), 100);

      return true;

    } catch (error) {
      console.error('JSON parsing error:', error);
      showErrorMessage('Invalid JSON format.');
      return false;
    }
  },

  // Page visibility state update
  setPageVisible: (isVisible: boolean) => {
    set(state => {
      // Don't update if state is already the same
      if (state.isPageVisible === isVisible) {
        return state;
      }

      if (isVisible && !state.isPageVisible) {
        // When page becomes visible again, merge accumulated outputs to actual outputs
        const updatedOutputs = { ...state.nodeStreamingOutputs };
        let hasUpdates = false;

        Object.keys(state.pendingStreamingOutputs).forEach(nodeId => {
          const pendingContent = state.pendingStreamingOutputs[nodeId];
          if (pendingContent) {
            updatedOutputs[nodeId] = (updatedOutputs[nodeId] || '') + pendingContent;
            hasUpdates = true;
          }
        });

        if (hasUpdates) {
          return {
            ...state,
            isPageVisible: isVisible,
            nodeStreamingOutputs: updatedOutputs,
            pendingStreamingOutputs: {} // Reset accumulated outputs
          };
        }
      }

      return {
        ...state,
        isPageVisible: isVisible
      };
    });
  },

  // Error message management functions
  addPersistentError: (errorMessage: string) => {
    const id = Date.now().toString();
    set(state => ({
      ...state,
      persistentErrors: [
        ...state.persistentErrors,
        { id, message: errorMessage, timestamp: Date.now() }
      ]
    }));

    message.error({
      content: errorMessage,
      duration: 0, // Won't disappear
      key: id, // Prevent duplicates
      onClick: () => {
        message.destroy(id);
      }
    });
  },

  removePersistentError: (id: string) => {
    set(state => ({
      ...state,
      persistentErrors: state.persistentErrors.filter(error => error.id !== id)
    }));

    // Also remove antd message
    message.destroy(id);
  },

  clearAllPersistentErrors: () => {
    const { persistentErrors } = get();

    // Remove all antd messages
    persistentErrors.forEach(error => {
      message.destroy(error.id);
    });

    set(state => ({
      ...state,
      persistentErrors: []
    }));
  }
  };
});
