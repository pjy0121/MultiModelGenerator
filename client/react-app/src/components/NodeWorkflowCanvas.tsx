import React, { useCallback, useEffect, useState, memo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Connection,
  Edge,
  NodeTypes
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  message,
  Button,
  Modal,
  Input,
  Typography,
  Space
} from 'antd';
import {
  FileTextOutlined,
  RobotOutlined,
  BranchesOutlined,
  CheckCircleOutlined,
  SearchOutlined,
  SaveOutlined,
  ReloadOutlined,
  ClearOutlined,
  DownloadOutlined,
  UploadOutlined,
  PlayCircleOutlined, // Execute icon
  StopOutlined, // Stop icon
} from '@ant-design/icons';
import { NodeWorkflowComponent } from './NodeWorkflowComponent';
import { useNodeWorkflowStore } from '../store/nodeWorkflowStore';
import { useNodeSelectionStore } from '../store/nodeSelectionStore';
import { useViewportStore } from '../store/viewportStore';
import { WorkflowEdge, NodeType } from '../types';
import { isConnectionAllowed } from '../utils/nodeWorkflowValidation';
import { showErrorMessage } from '../utils/messageUtils';
import { UI_CONFIG, UI_COLORS } from '../config/constants';



// Node type definition - prevent recreation with memoization
const nodeTypes: NodeTypes = {
  workflowNode: NodeWorkflowComponent,
};

// Edge type definition - explicitly define default to prevent recreation
const edgeTypes = {};

// fitView options - prevent recreation
const fitViewOptions = { padding: UI_CONFIG.REACT_FLOW.FIT_VIEW_PADDING };

// ReactFlow style - prevent recreation
const reactFlowStyle = { background: UI_CONFIG.REACT_FLOW.BACKGROUND_COLOR };

export const NodeWorkflowCanvas: React.FC = memo(() => {
  const {
    nodes: storeNodes,
    edges: storeEdges,
    isRestoring, // Restoring state
    addEdge: addStoreEdge,
    removeEdge,
    removeNode,

    // Node addition and workflow management functions
    addNode,
    saveCurrentWorkflow,
    restoreWorkflow,
    resetToInitialState,
    exportToJSON,
    importFromJSON,
    updateNodePositions,
    executeWorkflowStream, // Workflow streaming execution function
    stopWorkflowExecution, // Workflow stop function
    isExecuting, // Execution state
    isStopping, // Stopping state
  } = useNodeWorkflowStore();

  const { selectedNodeId, setSelectedNodeId } = useNodeSelectionStore();
  const { viewport, setViewport } = useViewportStore();  // Workflow management state
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [jsonText, setJsonText] = useState('');

  // Streaming execution handler
  const handleStreamingExecution = async () => {
    // Store already handles errors, so just call here
    await executeWorkflowStream(() => {
      // Streaming data is already processed in store, no additional processing needed
    });
  };

  // Workflow stop handler
  const handleStopExecution = async () => {
    // Do nothing if already stopping
    if (isStopping) return;
    await stopWorkflowExecution();
  };

  // ReactFlow instance reference
  const [reactFlowInstance, setReactFlowInstance] = React.useState<any>(null);

  // Auto-restore state management
  const [hasAutoRestored, setHasAutoRestored] = React.useState(false);

  // ReactFlow initialization handler
  const onInit = useCallback((instance: any) => {
    setReactFlowInstance(instance);

    // Auto-restore on app start (only once after instance creation)
    if (!hasAutoRestored) {
      const success = restoreWorkflow();
      if (success) {
        // Apply restored viewport after a delay (ensure ReactFlow initialization)
        setTimeout(() => {
          const { viewport } = useNodeWorkflowStore.getState();
          if (viewport) {
            instance.setViewport(viewport);
          }
        }, 50);
      }
      setHasAutoRestored(true);
    }
  }, [restoreWorkflow, hasAutoRestored]);

  // ReactFlow state (synchronized with store)
  const [nodes, setNodes, onNodesChange] = useNodesState(storeNodes);
  const [, setEdges, onEdgesChange] = useEdgesState(storeEdges); // edges uses styledEdges

  // Add selected state to nodes
  const nodesWithSelected = React.useMemo(() => {
    return nodes.map(node => ({
      ...node,
      selected: node.id === selectedNodeId
    }));
  }, [nodes, selectedNodeId]);

  // Apply viewport from store to ReactFlow (only during restoration)
  useEffect(() => {
    if (reactFlowInstance && viewport && isRestoring) {
      const currentReactFlowViewport = reactFlowInstance.getViewport();
      // Only update when viewport is actually different to prevent infinite loop
      if (
        Math.abs(currentReactFlowViewport.x - viewport.x) > 1 ||
        Math.abs(currentReactFlowViewport.y - viewport.y) > 1 ||
        Math.abs(currentReactFlowViewport.zoom - viewport.zoom) > 0.01
      ) {
        reactFlowInstance.setViewport(viewport);
      }
    }
  }, [viewport, reactFlowInstance, isRestoring]);

  // Prevent unnecessary recalculation with memoization
  const memoizedNodeTypes = React.useMemo(() => nodeTypes, []);
  const memoizedEdgeTypes = React.useMemo(() => edgeTypes, []);

  // Calculate edges for selected node
  const selectedNodeEdges = React.useMemo(() => {
    if (!selectedNodeId) return [];
    return storeEdges.filter(edge =>
      edge.source === selectedNodeId || edge.target === selectedNodeId
    );
  }, [selectedNodeId, storeEdges]);

  // Node click handler
  const onNodeClick = useCallback((_: React.MouseEvent, node: any) => {
    setSelectedNodeId(node.id);
  }, [setSelectedNodeId]);

  // Deselect on canvas background click
  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, [setSelectedNodeId]);

  // Edge styling - animate edges connected to selected node
  const styledEdges = React.useMemo(() => {
    return storeEdges.map(edge => ({
      ...edge,
      animated: selectedNodeEdges.some(selectedEdge => selectedEdge.id === edge.id),
      markerEnd: {
        type: 'arrowclosed' as const,
        width: 20,
        height: 20,
        color: selectedNodeEdges.some(selectedEdge => selectedEdge.id === edge.id)
          ? UI_COLORS.EDGE.SELECTED // Blue for selected node's edge
          : UI_COLORS.EDGE.DEFAULT // Default gray
      },
      style: {
        stroke: selectedNodeEdges.some(selectedEdge => selectedEdge.id === edge.id)
          ? UI_COLORS.EDGE.SELECTED // Blue for selected node's edge
          : UI_COLORS.EDGE.DEFAULT, // Default gray
        strokeWidth: selectedNodeEdges.some(selectedEdge => selectedEdge.id === edge.id)
          ? 2 // Thicker for selected node's edge
          : 1
      }
    }));
  }, [storeEdges, selectedNodeEdges]);

  // Detect viewport changes and update state (more sensitive detection)
  const onViewportChange = useCallback((newViewport: any) => {
    // Add null check
    if (!newViewport || !viewport) return;

    // Compare with viewport to detect changes
    if (Math.abs((newViewport.zoom || 1) - (viewport.zoom || 1)) > 0.005 ||  // More sensitive zoom detection
        Math.abs((newViewport.x || 0) - (viewport.x || 0)) > 2 ||          // More sensitive x detection
        Math.abs((newViewport.y || 0) - (viewport.y || 0)) > 2) {          // More sensitive y detection
      setViewport(newViewport);
    }
  }, [setViewport, viewport]);

  // Node change handler (only output node is immovable)
  const onNodesChangeWithFixed = useCallback((changes: any[]) => {
    const filteredChanges = changes.filter(change => {
      // Only ignore position changes for output node (completely fixed)
      if (change.type === 'position') {
        const node = nodes.find(n => n.id === change.id);
        if (node?.data?.nodeType === NodeType.OUTPUT) {
          return false;
        }
      }
      return true;
    });

    onNodesChange(filteredChanges);

    // Remove real-time store update - only sync when saving
  }, [onNodesChange, nodes]);



  // Node synchronization - safe logic to prevent infinite loop
  const prevStoreNodesRef = React.useRef(storeNodes);

  React.useEffect(() => {
    // Don't update if store nodes haven't actually changed (prevent infinite loop)
    if (prevStoreNodesRef.current === storeNodes) {
      return;
    }

    if (!hasAutoRestored) {
      // Use store nodes directly during auto-restore
      setNodes(storeNodes);
      prevStoreNodesRef.current = storeNodes;
      return;
    }

    // Detect node changes (count, ID, data changes)
    const currentIds = new Set(prevStoreNodesRef.current.map(n => n.id));
    const newIds = new Set(storeNodes.map(n => n.id));

    // 1. Check for node count or ID changes
    const hasStructuralChanges = currentIds.size !== newIds.size ||
                                [...currentIds].some(id => !newIds.has(id)) ||
                                [...newIds].some(id => !currentIds.has(id));

    // 2. Check for data changes in existing nodes (label, model, etc.)
    const hasDataChanges = !hasStructuralChanges && storeNodes.some(storeNode => {
      const prevNode = prevStoreNodesRef.current.find(n => n.id === storeNode.id);
      if (!prevNode) return false;

      // Compare node data (compare data object contents)
      return JSON.stringify(prevNode.data) !== JSON.stringify(storeNode.data) ||
             prevNode.type !== storeNode.type;
    });

    if (hasStructuralChanges || hasDataChanges) {
      // Sync when nodes are added/deleted or data changes (preserve existing positions)
      setNodes(currentReactFlowNodes => {
        const currentPositions = new Map();
        currentReactFlowNodes.forEach(node => {
          currentPositions.set(node.id, node.position);
        });

        return storeNodes.map(storeNode => {
          const existingPosition = currentPositions.get(storeNode.id);
          return {
            ...storeNode,
            position: existingPosition || storeNode.position
          };
        });
      });
    }

    prevStoreNodesRef.current = storeNodes;
  }, [storeNodes, setNodes, hasAutoRestored]);

  // Apply store edges to ReactFlow when changed
  useEffect(() => {
    setEdges(storeEdges);
  }, [storeEdges, setEdges]);

  // Connection creation handler
  const onConnect = useCallback(
    (params: Connection | Edge) => {
      const sourceNode = storeNodes.find(n => n.id === params.source);
      const targetNode = storeNodes.find(n => n.id === params.target);

      if (!sourceNode || !targetNode) {
        showErrorMessage("Cannot find source or target node to connect.");
        return;
      }

      const validation = isConnectionAllowed(sourceNode, targetNode, storeNodes, storeEdges);

      if (validation.allowed) {
        const newEdge: WorkflowEdge = {
          id: `edge-${params.source}-${params.target}`,
          source: params.source!,
          target: params.target!,
        };
        addStoreEdge(newEdge);
      } else {
        showErrorMessage(validation.reason || 'Connection violates rules. Cannot connect.');
      }
    },
    [addStoreEdge, storeNodes, storeEdges]
  );

  // Edge reconnection handler
  const onReconnect = useCallback(
    (oldEdge: Edge, newConnection: Connection) => {
      const sourceNode = storeNodes.find(n => n.id === newConnection.source);
      const targetNode = storeNodes.find(n => n.id === newConnection.target);

      if (!sourceNode || !targetNode) {
        showErrorMessage("Cannot find source or target node to connect.");
        return;
      }

      // Validate excluding the old edge during reconnection
      const edgesWithoutOld = storeEdges.filter(e => e.id !== oldEdge.id);
      const validation = isConnectionAllowed(sourceNode, targetNode, storeNodes, edgesWithoutOld);

      if (validation.allowed) {
        // Remove existing edge
        removeEdge(oldEdge.id);

        // Add new edge
        const newEdge: WorkflowEdge = {
          id: `edge-${newConnection.source}-${newConnection.target}`,
          source: newConnection.source!,
          target: newConnection.target!,
        };
        addStoreEdge(newEdge);
        message.success('Edge reconnected successfully.');
      } else {
        showErrorMessage(validation.reason || 'Connection violates rules. Cannot connect.');
      }
    },
    [addStoreEdge, removeEdge, storeNodes, storeEdges]
  );

  // Edge reconnection start handler
  const onReconnectStart = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      // Logic when edge reconnection starts (add if needed)
      console.log('Edge reconnect started:', edge.id);
    },
    []
  );

  // Edge reconnection end handler (delete edge when dropped on empty space)
  const onReconnectEnd = useCallback(
    (_: MouseEvent | TouchEvent, edge: Edge) => {
      // Delete edge if dropped on empty space
      setTimeout(() => {
        const updatedEdge = storeEdges.find(e => e.id === edge.id);
        if (updatedEdge) {
          // If connection still exists, consider it dropped on empty space and delete
          removeEdge(edge.id);
          message.info('Edge deleted.');
        }
      }, 100);
    },
    [removeEdge, storeEdges]
  );

  // Node deletion handler
  const onNodesDelete = useCallback(
    (deletedNodes: any[]) => {
      deletedNodes.forEach(node => removeNode(node.id));
    },
    [removeNode]
  );

  // Edge deletion handler
  const onEdgesDelete = useCallback(
    (deletedEdges: any[]) => {
      deletedEdges.forEach(edge => removeEdge(edge.id));
    },
    [removeEdge]
  );

  // Workflow save handler
  const handleSave = () => {
    if (reactFlowInstance) {
      const currentNodes = reactFlowInstance.getNodes();
      updateNodePositions(currentNodes.map((n: any) => ({ id: n.id, position: n.position })));
      saveCurrentWorkflow();
      message.success('Workflow saved.');
    }
  };

  // Workflow restore handler
  const handleRestore = () => {
    const success = restoreWorkflow();
    if (success) {
      // Apply viewport after restoration
      setTimeout(() => {
        if (reactFlowInstance) {
          const { viewport: restoredViewport } = useNodeWorkflowStore.getState();
          if (restoredViewport) {
            reactFlowInstance.setViewport(restoredViewport);
          }
        }
      }, 50);
      message.success('Workflow restored.');
    } else {
      message.info('No saved workflow found.');
    }
  };

  // Reset handler
  const handleReset = () => {
    Modal.confirm({
      title: 'Reset Workflow',
      content: 'Are you sure you want to delete all nodes and connections and reset to initial state?',
      okText: 'Reset',
      cancelText: 'Cancel',
      onOk: () => {
        resetToInitialState();
        message.success('Workflow reset.');
        // Reset viewport after reset
        setTimeout(() => {
          if (reactFlowInstance) {
            reactFlowInstance.setViewport({ x: 0, y: 0, zoom: 1 });
          }
        }, 50);
      },
    });
  };

  // Export to JSON handler
  const handleExport = () => {
    if (reactFlowInstance) {
      const currentNodes = reactFlowInstance.getNodes();
      updateNodePositions(currentNodes.map((n: any) => ({ id: n.id, position: n.position })));
      exportToJSON();
    }
  };

  // Open JSON import modal
  const showImportModal = () => {
    setImportModalVisible(true);
  };

  // Process JSON import
  const handleImport = () => {
    try {
      importFromJSON(jsonText);
      message.success('Workflow imported successfully.');
      setImportModalVisible(false);
      setJsonText('');
      // Apply viewport after import
      setTimeout(() => {
        if (reactFlowInstance) {
          const { viewport: importedViewport } = useNodeWorkflowStore.getState();
          if (importedViewport) {
            reactFlowInstance.setViewport(importedViewport);
          }
        }
      }, 50);
    } catch (error) {
      showErrorMessage('Invalid JSON format. Please check and try again.');
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>

      {/* Top title bar */}
      <div style={{ padding: '8px 16px', background: UI_COLORS.PANEL.HEADER_BACKGROUND, borderBottom: `1px solid ${UI_COLORS.PANEL.HEADER_BORDER}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>Workflow Configuration</Typography.Title>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {!isExecuting && !isStopping ? (
            <Button
              icon={<PlayCircleOutlined />}
              type="primary"
              onClick={handleStreamingExecution}
            >
              Run Workflow
            </Button>
          ) : isExecuting && !isStopping ? (
            <Button
              icon={<StopOutlined />}
              type="default"
              danger
              onClick={handleStopExecution}
            >
              Stop Workflow
            </Button>
          ) : (
            <Button
              icon={<StopOutlined />}
              type="default"
              danger
              disabled={true}
              loading={true}
            >
              Stopping...
            </Button>
          )}
        </div>
      </div>

      <div style={{ flex: 1, position: 'relative' }}>

        <ReactFlow
          nodes={nodesWithSelected}
          edges={styledEdges}
          onNodesChange={onNodesChangeWithFixed}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodesDelete={onNodesDelete}
          onEdgesDelete={onEdgesDelete}
          onReconnect={onReconnect}
          onReconnectStart={onReconnectStart}
          onReconnectEnd={onReconnectEnd}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={memoizedNodeTypes}
          edgeTypes={memoizedEdgeTypes}
          onInit={onInit}
          onMoveEnd={onViewportChange}
          fitView
          fitViewOptions={fitViewOptions}
          style={reactFlowStyle}
          edgesReconnectable={true}
        >
          <Background />
          <Controls />
          <MiniMap />

          <div style={{ position: 'absolute', top: 10, left: 10, zIndex: 10, display: 'flex', gap: '8px' }}>
            <Space.Compact>
              <Button icon={<FileTextOutlined />} onClick={() => addNode(NodeType.INPUT, { x: 250, y: 5 })}>Input</Button>
              <Button icon={<RobotOutlined />} onClick={() => addNode(NodeType.GENERATION, { x: 250, y: 105 })}>Generation</Button>
              <Button icon={<BranchesOutlined />} onClick={() => addNode(NodeType.ENSEMBLE, { x: 250, y: 205 })}>Ensemble</Button>
              <Button icon={<CheckCircleOutlined />} onClick={() => addNode(NodeType.VALIDATION, { x: 250, y: 305 })}>Validation</Button>
              <Button icon={<SearchOutlined />} onClick={() => addNode(NodeType.CONTEXT, { x: 250, y: 405 })}>Context</Button>
            </Space.Compact>

            <Space.Compact>
              <Button icon={<SaveOutlined />} onClick={handleSave}>Save</Button>
              <Button icon={<ReloadOutlined />} onClick={handleRestore}>Restore</Button>
              <Button icon={<ClearOutlined />} onClick={handleReset}>Reset</Button>
            </Space.Compact>

            <Space.Compact>
              <Button icon={<DownloadOutlined />} onClick={handleExport}>Export</Button>
              <Button icon={<UploadOutlined />} onClick={showImportModal}>Import</Button>
            </Space.Compact>
          </div>
        </ReactFlow>
      </div>

      <Modal
        title="Import Workflow JSON"
        open={importModalVisible}
        onOk={handleImport}
        onCancel={() => setImportModalVisible(false)}
        okText="Import"
        cancelText="Cancel"
      >
        <Input.TextArea
          rows={10}
          value={jsonText}
          onChange={(e) => setJsonText(e.target.value)}
          placeholder='Paste JSON data here.'
        />
      </Modal>
    </div>
  );
});
