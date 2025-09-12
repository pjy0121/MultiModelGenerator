import React from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { PlusOutlined } from '@ant-design/icons';
import { LayerType, PlaceholderNode as PlaceholderNodeType } from '../types';
import { useWorkflowStore } from '../store/workflowStore';

type PlaceholderNodeProps = NodeProps<PlaceholderNodeType>;

const PlaceholderNode: React.FC<PlaceholderNodeProps> = ({ data, selected }) => {
  const { isExecuting } = useWorkflowStore();

  const getNodeColor = (layer: LayerType) => {
    switch (layer) {
      case LayerType.GENERATION:
        return '#52c41a';
      case LayerType.VALIDATION:
        return '#faad14';
      default:
        return '#d9d9d9';
    }
  };

  const isValidation = data.layer === LayerType.VALIDATION;
  
  // 실행 중일 때는 비활성화
  const isDisabled = isExecuting;

  return (
    <div
      style={{
        width: 150,
        height: 75,
        border: `2px dashed ${isDisabled ? '#d9d9d9' : getNodeColor(data.layer)}`,
        borderRadius: '6px',
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        backgroundColor: selected ? `${getNodeColor(data.layer)}20` : 'transparent',
        transition: 'all 0.2s ease',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        userSelect: 'none',
        opacity: isDisabled ? 0.5 : 1
      }}
    >
      {/* Generation Layer: 아래쪽 핸들러 */}
      {data.layer === LayerType.GENERATION && (
        <Handle
          type="source"
          position={Position.Bottom}
          style={{ 
            background: getNodeColor(data.layer),
            border: `2px solid ${getNodeColor(data.layer)}`,
            opacity: 0.5
          }}
        />
      )}
      {/* Validation Layer: 좌측 핸들러 */}
      {isValidation && (
        <Handle
          type="target"
          position={Position.Left}
          id="left"
          style={{ 
            background: getNodeColor(data.layer),
            border: `2px solid ${getNodeColor(data.layer)}`,
            opacity: 0.5
          }}
        />
      )}
      
      <div style={{ textAlign: 'center', color: isDisabled ? '#d9d9d9' : getNodeColor(data.layer) }}>
        <PlusOutlined style={{ fontSize: '24px', marginBottom: '4px' }} />
        <div style={{ fontSize: '10px', opacity: 0.8 }}>
          {isDisabled ? 'Executing...' : 'Add Node'}
        </div>
      </div>
    </div>
 );
};
export default PlaceholderNode;
