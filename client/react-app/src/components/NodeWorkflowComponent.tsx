import React, { useState, memo, useCallback, useMemo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Card, Tag, Typography, Button, Popconfirm } from 'antd';
import { EditOutlined, DeleteOutlined, LoadingOutlined } from '@ant-design/icons';
import { NodeType, WorkflowNode } from '../types';
import NodeEditModal from './NodeEditModal';
import { useNodeWorkflowStore } from '../store/nodeWorkflowStore';
import { NODE_CONFIG } from '../config/constants';

const { Text } = Typography;

// Search intensity label mapping
const getSearchIntensityLabel = (intensity: string): string => {
  return NODE_CONFIG.SEARCH_INTENSITY_LABELS[intensity as keyof typeof NODE_CONFIG.SEARCH_INTENSITY_LABELS] || intensity;
};

interface NodeWorkflowComponentProps {
  data: WorkflowNode['data'];
  id: string;
  selected?: boolean;
}

// Node type color settings
const getNodeColor = (nodeType: NodeType): { background: string; border: string; tag: string } => {
  return NODE_CONFIG.COLORS[nodeType] || NODE_CONFIG.COLORS.default;
};

// Handle position configuration
const getHandleConfig = (nodeType: NodeType) => {
  switch (nodeType) {
    case NodeType.INPUT:
      return { source: true, target: false }; // output only
    case NodeType.OUTPUT:
      return { source: false, target: true }; // input only
    default:
      return { source: true, target: true }; // bidirectional
  }
};

export const NodeWorkflowComponent: React.FC<NodeWorkflowComponentProps> = memo(({ 
  data, 
  id, 
  selected = false 
}) => {
  const { updateNode, removeNode, nodeExecutionStates } = useNodeWorkflowStore();
  const [editModalVisible, setEditModalVisible] = useState(false);
  
  // Get execution state
  const executionState = nodeExecutionStates[id] || 'idle';
  const isExecuting = executionState === 'executing';
  
  const colors = useMemo(() => getNodeColor(data.nodeType), [data.nodeType]);
  const handles = useMemo(() => getHandleConfig(data.nodeType), [data.nodeType]);
  
  const isLLMNode = useMemo(() => 
    [NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(data.nodeType), 
    [data.nodeType]
  );
  const isContentNode = useMemo(() => 
    [NodeType.INPUT, NodeType.OUTPUT].includes(data.nodeType), 
    [data.nodeType]
  );

  // Style changes based on execution and selection state
  const getExecutingStyle = useCallback(() => {
    if (isExecuting) {
      return {
        background: 'linear-gradient(45deg, #fff1f0, #ffccc7)', // Red gradient background
        border: `3px solid #ff4d4f`, // Thick red border
        boxShadow: '0 0 20px rgba(255, 77, 79, 0.6), 0 0 40px rgba(255, 77, 79, 0.3)', // Fixed red glow
        zIndex: 1000 // Display above other nodes
      };
    }

    if (selected) {
      return {
        background: colors.background,
        border: `3px solid ${colors.border}`, // Selected nodes have thicker border
        boxShadow: `0 0 15px ${colors.border}40`, // Selected nodes have glow effect
        transform: 'scale(1.02)', // Slight enlargement
        transition: 'all 0.3s ease',
        zIndex: 100
      };
    }

    return {
      background: colors.background,
      border: `2px solid ${colors.border}`,
      transform: 'scale(1)',
      transition: 'all 0.3s ease' // Smooth transition
    };
  }, [isExecuting, selected, colors.background, colors.border]);

  // Node edit handler
  const handleEdit = useCallback(() => {
    setEditModalVisible(true);
  }, []);

  const handleEditSave = useCallback((nodeId: string, updates: Partial<WorkflowNode['data']>) => {
    updateNode(nodeId, updates);
    setEditModalVisible(false);
  }, [updateNode]);

  // Node delete handler
  const handleDelete = useCallback(() => {
    try {
      removeNode(id);
    } catch (error: any) {
      // Error is already displayed via store message
    }
  }, [removeNode, id]);

  return (
    <div>
      {/* Target Handle (input) */}
      {handles.target && (
        <Handle
          type="target"
          position={Position.Top}
          style={{ 
            background: colors.border,
            width: 12,
            height: 12,
            border: `2px solid ${colors.background}`
          }}
        />
      )}
      
        <Card
          size="small"
          style={{
            minWidth: 200,
            maxWidth: 300,
            ...getExecutingStyle(), // Apply style based on execution state
            borderRadius: 8,
            boxShadow: selected 
              ? `0 0 0 2px ${colors.border}40` 
              : isExecuting 
                ? '0 4px 12px rgba(255, 77, 79, 0.3)' 
                : '0 2px 8px rgba(0,0,0,0.1)'
          }}
          title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Text strong style={{ fontSize: 12 }}>
                  {data.label}
                </Text>
                {isExecuting && (
                  <LoadingOutlined 
                    style={{ 
                      color: '#ff4d4f', 
                      fontSize: 14,
                      animation: 'spin 1s linear infinite'  
                    }} 
                  />
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Tag 
                  color={colors.tag} 
                  style={{ margin: 0, fontSize: 10 }}
                >
                  {data.nodeType.replace('-node', '')}
                </Tag>
                {data.nodeType !== NodeType.OUTPUT && (
                  <div>
                    <Button
                      size="small"
                      type="text"
                      icon={<EditOutlined />}
                      onClick={handleEdit}
                      style={{ padding: 0, width: 16, height: 16 }}
                      title="Edit"
                    />
                    <Popconfirm
                      title="Delete Node"
                      description={`Are you sure you want to delete this ${data.nodeType}?`}
                      onConfirm={handleDelete}
                      okText="Delete"
                      cancelText="Cancel"
                      okType="danger"
                    >
                      <Button
                        size="small"
                        type="text"
                        icon={<DeleteOutlined />}
                        style={{ padding: 0, width: 16, height: 16, color: '#ff4d4f' }}
                        title="Delete"
                      />
                    </Popconfirm>
                  </div>
                )}
              </div>
            </div>
          }
        >
          <div style={{ fontSize: 11 }}>
            {/* LLM node info display */}
            {isLLMNode && (
              <div style={{ marginBottom: 8 }}>
                <div style={{ marginBottom: 4 }}>
                  <Text style={{ fontSize: 10, color: '#666' }}>
                    Provider: <strong>{data.llm_provider || 'Not set'}</strong>
                  </Text>
                  <br />
                  <Text style={{ fontSize: 10, color: '#666' }}>
                    Model: <strong>{data.model_type || 'Not set'}</strong>
                  </Text>
                </div>
                {data.prompt && (
                  <div style={{ 
                    marginTop: 6,
                    padding: '6px 8px',
                    background: '#f9f9f9',
                    borderRadius: 4,
                    border: '1px solid #e8e8e8'
                  }}>
                    <Text style={{ fontSize: 10, color: '#666', fontWeight: 'bold' }}>
                      Prompt:
                    </Text>
                    <br />
                    <Text style={{ 
                      fontSize: 10, 
                      color: '#333',
                      fontFamily: 'Consolas, "Courier New", monospace'
                    }}>
                      {data.prompt.length > 80 ? `${data.prompt.substring(0, 80)}...` : data.prompt}
                    </Text>
                  </div>
                )}
                {!data.prompt && (
                  <Text style={{ fontSize: 10, color: '#ff4d4f', fontStyle: 'italic' }}>
                    ⚠️ Prompt not configured
                  </Text>
                )}
              </div>
            )}
            
            {/* Context node info display */}
            {data.nodeType === NodeType.CONTEXT && (
              <div style={{ marginBottom: 8 }}>
                <div style={{ marginBottom: 4 }}>
                  <Text style={{ fontSize: 10, color: '#666' }}>
                    <strong>{data.knowledge_base && data.knowledge_base !== 'none' ? `Base: ${data.knowledge_base}` : 'Base: None'}</strong>
                  </Text>
                  <br />
                  <Text style={{ fontSize: 10, color: '#666' }}>
                    <strong>{data.knowledge_base && data.knowledge_base !== 'none' && data.search_intensity ? `Intensity: ${getSearchIntensityLabel(data.search_intensity)}` : ''}</strong>
                  </Text>
                </div>
              </div>
            )}
            
            {/* Content node info display */}
            {isContentNode && (
              <div>
                <Text style={{ fontSize: 10, color: '#666' }}>
                  { data.content && data.content.length > 50 
                    ? `${data.content.substring(0, 50)}...` 
                    : data.content || ''
                  }
                </Text>
              </div>
            )}
          </div>
        </Card>
      
      {/* Source Handle (output) */}
      {handles.source && (
        <Handle
          type="source"
          position={Position.Bottom}
          style={{ 
            background: colors.border,
            width: 12,
            height: 12,
            border: `2px solid ${colors.background}`
          }}
        />
      )}

      {/* Edit modal */}
      <NodeEditModal
        open={editModalVisible}
        node={{ id, data, type: 'workflowNode', position: { x: 0, y: 0 } }}
        onClose={() => setEditModalVisible(false)}
        onSave={handleEditSave}
      />
    </div>
  );
});