import React from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Card, Typography, Button, Modal } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import { WorkflowNode, LayerType } from '../types';
import { useWorkflowStore } from '../store/workflowStore';

const { Text } = Typography;
const { confirm } = Modal;

type CustomNodeProps = NodeProps<WorkflowNode>;

const CustomNode: React.FC<CustomNodeProps> = ({ data, selected }) => {
  const { nodes, removeNode, currentExecutingLayer } = useWorkflowStore();

  const getNodeColor = (layer: LayerType) => {
    switch (layer) {
      case LayerType.GENERATION:
        return '#52c41a';
      case LayerType.ENSEMBLE:
        return '#722ed1'; // 보라색으로 변경 (선택된 노드의 파란색과 구분)
      case LayerType.VALIDATION:
        return '#faad14';
      default:
        return '#d9d9d9';
    }
  };

  // 현재 실행 중인 Layer인지 확인
  const isCurrentlyExecuting = currentExecutingLayer === data.layer;

  // 실행 중인 노드의 스타일
  const getExecutingStyle = () => {
    if (isCurrentlyExecuting) {
      return {
        boxShadow: '0 0 10px 2px rgba(255, 77, 79, 0.6)',
        animation: 'pulse 1.5s ease-in-out infinite alternate',
        border: '2px solid #ff4d4f',
        borderColor: '#ff4d4f !important'
      };
    }
    return {};
  };

  // ✅ 마지막 노드만 삭제 가능하도록 수정
  const isRemovable = () => {
    // Ensemble Layer는 제거 불가
    if (data.layer === LayerType.ENSEMBLE) return false;

    // 해당 레이어의 실제 노드들을 x좌표 기준으로 정렬
    const layerNodes = nodes
      .filter(n => n.type === 'customNode' && (n as any).data.layer === data.layer)
      .sort((a, b) => a.position.x - b.position.x);

    // 노드가 1개뿐이면 제거 불가
    if (layerNodes.length <= 1) return false;

    // ✅ 마지막 노드인지 확인 (가장 오른쪽 노드)
    const lastNode = layerNodes[layerNodes.length - 1];
    if (lastNode.id !== data.id) return false;

    return true;
  };

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    confirm({
      title: '마지막 노드 제거',
      content: `정말로 이 ${data.layer} 레이어의 마지막 노드를 제거하시겠습니까?`,
      okText: '제거',
      cancelText: '취소',
      okType: 'danger',
      onOk() {
        console.log('마지막 노드 제거 확인됨:', data.id);
        removeNode(data.id);
      },
      onCancel() {
        console.log('노드 제거 취소됨');
      },
    });
  };

  const isGeneration = data.layer === LayerType.GENERATION;
  const isEnsemble = data.layer === LayerType.ENSEMBLE;
  const isValidation = data.layer === LayerType.VALIDATION;
  const showRemoveButton = isRemovable();

  return (
    <div 
      className="nopan"
      style={{ position: 'relative' }}
    >
      <Card
        size="small"
        style={{
          width: 150,
          borderColor: isCurrentlyExecuting ? '#ff4d4f' : (selected ? '#1890ff' : getNodeColor(data.layer)),
          borderWidth: isCurrentlyExecuting ? 2 : (selected ? 2 : 1),
          cursor: 'pointer',
          position: 'relative',
          ...getExecutingStyle() // 실행 중인 노드 스타일 적용
        }}
        bodyStyle={{ padding: '8px 12px' }}
      >
        {/* ✅ 마지막 노드에만 제거 버튼 표시 */}
        {showRemoveButton && (
          <Button
            type="text"
            danger
            size="small"
            icon={<CloseOutlined />}
            onClick={handleRemove}
            onMouseDown={(e) => {
              e.stopPropagation();
            }}
            onDoubleClick={(e) => {
              e.stopPropagation();
            }}
            style={{
              position: 'absolute',
              top: '-8px',
              right: '-8px',
              width: '20px',
              height: '20px',
              borderRadius: '50%',
              border: '1px solid #ff4d4f',
              backgroundColor: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '10px',
              padding: 0,
              zIndex: 10,
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}
            title="마지막 노드 제거" // ✅ 툴팁 수정
          />
        )}

        {/* Generation Layer: 아래쪽 핸들러만 */}
        {isGeneration && (
          <Handle
            type="source"
            position={Position.Bottom}
            style={{ background: getNodeColor(data.layer) }}
          />
        )}

        {/* Ensemble Layer: 위쪽 타겟, 아래쪽 소스 */}
        {isEnsemble && (
          <>
            <Handle
              type="target"
              position={Position.Top}
              style={{ background: getNodeColor(data.layer) }}
            />
            <Handle
              type="source"
              position={Position.Bottom}
              style={{ background: getNodeColor(data.layer) }}
            />
          </>
        )}

        {/* Validation Layer: 좌우 핸들러 */}
        {isValidation && (
          <>
            <Handle
              type="target"
              position={Position.Left}
              id="left"
              style={{ background: getNodeColor(data.layer) }}
            />
            <Handle
              type="source"
              position={Position.Right}
              id="right"
              style={{ background: getNodeColor(data.layer) }}
            />
          </>
        )}
        
        <div style={{ textAlign: 'center' }}>
          <Text strong style={{ fontSize: '12px' }}>
            {data.label}
          </Text>
          <br />
          <Text type="secondary" style={{ fontSize: '10px' }}>
            {data.layer}
          </Text>
          {isCurrentlyExecuting && (
            <>
              <br />
              <Text style={{ fontSize: '9px', color: 'red', fontWeight: 'bold' }}>
                실행 중...
              </Text>
            </>
          )}
        </div>
      </Card>
    </div>
  );
};

export default CustomNode;
