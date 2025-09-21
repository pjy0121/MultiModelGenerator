import React, { useState, memo, useCallback, useMemo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Card, Tag, Typography, Button, Popconfirm, Spin } from 'antd';
import { EditOutlined, DeleteOutlined, LoadingOutlined } from '@ant-design/icons';
import { NodeType, WorkflowNode } from '../types';
import NodeEditModal from './NodeEditModal';
import { useNodeWorkflowStore } from '../store/nodeWorkflowStore';

const { Text } = Typography;

interface NodeWorkflowComponentProps {
  data: WorkflowNode['data'];
  id: string;
  selected?: boolean;
}

// 노드 타입별 색상 설정
const getNodeColor = (nodeType: NodeType): { background: string; border: string; tag: string } => {
  switch (nodeType) {
    case NodeType.INPUT:
      return { background: '#e6f7ff', border: '#1890ff', tag: 'blue' };
    case NodeType.GENERATION:
      return { background: '#f6ffed', border: '#52c41a', tag: 'green' };
    case NodeType.ENSEMBLE:
      return { background: '#f9f0ff', border: '#722ed1', tag: 'purple' };
    case NodeType.VALIDATION:
      return { background: '#fff7e6', border: '#fa8c16', tag: 'orange' };
    case NodeType.OUTPUT:
      return { background: '#fff1f0', border: '#ff4d4f', tag: 'red' };
    default:
      return { background: '#f5f5f5', border: '#d9d9d9', tag: 'default' };
  }
};

// Handle 위치 결정
const getHandleConfig = (nodeType: NodeType) => {
  switch (nodeType) {
    case NodeType.INPUT:
      return { source: true, target: false }; // output만
    case NodeType.OUTPUT:
      return { source: false, target: true }; // input만
    default:
      return { source: true, target: true }; // 양방향
  }
};

export const NodeWorkflowComponent: React.FC<NodeWorkflowComponentProps> = memo(({ 
  data, 
  id, 
  selected = false 
}) => {
  const { updateNode, removeNode, nodeExecutionStates } = useNodeWorkflowStore();
  const [editModalVisible, setEditModalVisible] = useState(false);
  
  // 실행 상태 가져오기
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

  // 실행 상태에 따른 스타일 변경
  const getExecutingStyle = useCallback(() => {
    if (isExecuting) {
      return {
        background: 'linear-gradient(45deg, #e6f7ff, #bae7ff)', // 파란색 그라데이션 배경
        border: `3px solid #1890ff`, // 두꺼운 파란색 테두리
        animation: 'pulse 2s infinite', // 펄스 애니메이션
        transform: 'scale(1.05)', // 살짝 확대
        boxShadow: '0 4px 12px rgba(24, 144, 255, 0.3)', // 파란색 그림자
        zIndex: 1000 // 다른 노드들보다 위에 표시
      };
    }
    return {
      background: colors.background,
      border: `2px solid ${colors.border}`,
      transform: 'scale(1)',
      transition: 'all 0.3s ease' // 부드러운 전환
    };
  }, [isExecuting, colors.background, colors.border]);

  // 노드 편집 핸들러
  const handleEdit = useCallback(() => {
    setEditModalVisible(true);
  }, []);

  const handleEditSave = useCallback((nodeId: string, updates: Partial<WorkflowNode['data']>) => {
    updateNode(nodeId, updates);
    setEditModalVisible(false);
  }, [updateNode]);

  // 노드 삭제 핸들러
  const handleDelete = useCallback(() => {
    try {
      removeNode(id);
    } catch (error: any) {
      // 에러는 이미 store에서 message로 표시됨
    }
  }, [removeNode, id]);

  return (
    <div>
      {/* Target Handle (입력) */}
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
            ...getExecutingStyle(), // 실행 상태에 따른 스타일 적용
            borderRadius: 8,
            boxShadow: selected 
              ? `0 0 0 2px ${colors.border}40` 
              : isExecuting 
                ? '0 4px 12px rgba(24, 144, 255, 0.3)' 
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
                      color: '#1890ff', 
                      fontSize: 14,
                      animation: 'spin 1s linear infinite'  
                    }} 
                  />
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Tag 
                  color={isExecuting ? 'processing' : colors.tag} 
                  style={{ margin: 0, fontSize: 10 }}
                >
                  {isExecuting ? 'RUNNING' : data.nodeType.replace('-node', '')}
                </Tag>
                {data.nodeType !== NodeType.OUTPUT && (
                  <div>
                    <Button
                      size="small"
                      type="text"
                      icon={<EditOutlined />}
                      onClick={handleEdit}
                      style={{ padding: 0, width: 16, height: 16 }}
                      title="편집"
                    />
                    <Popconfirm
                      title="노드 삭제"
                      description={`이 ${data.nodeType}를 삭제하시겠습니까?`}
                      onConfirm={handleDelete}
                      okText="삭제"
                      cancelText="취소"
                      okType="danger"
                    >
                      <Button
                        size="small"
                        type="text"
                        icon={<DeleteOutlined />}
                        style={{ padding: 0, width: 16, height: 16, color: '#ff4d4f' }}
                        title="삭제"
                      />
                    </Popconfirm>
                  </div>
                )}
              </div>
            </div>
          }
        >
          <div style={{ fontSize: 11 }}>
            {/* LLM 노드 정보 표시 */}
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
                    ⚠️ 프롬프트가 설정되지 않았습니다
                  </Text>
                )}
              </div>
            )}
            
            {/* Content 노드 정보 표시 */}
            {isContentNode && (
              <div>
                <Text style={{ fontSize: 10, color: '#666' }}>
                  { data.content && data.content.length > 50 
                    ? `${data.content.substring(0, 50)}...` 
                    : data.content || 'Content not set!'
                  }
                </Text>
              </div>
            )}
          </div>
        </Card>
      
      {/* Source Handle (출력) */}
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

      {/* 편집 모달 */}
      <NodeEditModal
        open={editModalVisible}
        node={{ id, data, type: 'workflowNode', position: { x: 0, y: 0 } }}
        onClose={() => setEditModalVisible(false)}
        onSave={handleEditSave}
      />
    </div>
  );
});