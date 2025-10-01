import React from 'react';
import { Alert, Button, Space, Typography } from 'antd';
import { CloseOutlined, ClearOutlined } from '@ant-design/icons';
import { useNodeWorkflowStore } from '../store/nodeWorkflowStore';

const { Text } = Typography;

/**
 * 지속적인 에러 메시지 표시 컴포넌트
 * 사용자가 수동으로 개별 또는 전체 에러 메시지를 닫을 수 있음
 */
export const PersistentErrorDisplay: React.FC = () => {
  const { persistentErrors, removePersistentError, clearAllPersistentErrors } = useNodeWorkflowStore();

  if (persistentErrors.length === 0) {
    return null;
  }

  return (
    <div 
      style={{ 
        position: 'fixed', 
        top: 16, 
        right: 16, 
        zIndex: 1000,
        maxWidth: '400px',
        maxHeight: '60vh',
        overflowY: 'auto'
      }}
    >
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        {/* 전체 지우기 버튼 (여러 에러가 있을 때만) */}
        {persistentErrors.length > 1 && (
          <Button
            type="link"
            size="small"
            icon={<ClearOutlined />}
            onClick={clearAllPersistentErrors}
            style={{ 
              padding: 0, 
              height: 'auto',
              alignSelf: 'flex-end',
              color: '#ff4d4f'
            }}
          >
            모든 에러 메시지 지우기
          </Button>
        )}
        
        {/* 개별 에러 메시지들 */}
        {persistentErrors.map((error) => (
          <Alert
            key={error.id}
            message="실행 오류"
            description={
              <div>
                <Text style={{ fontSize: '12px', wordBreak: 'break-word' }}>
                  {error.message}
                </Text>
                <div style={{ marginTop: '4px' }}>
                  <Text type="secondary" style={{ fontSize: '11px' }}>
                    {new Date(error.timestamp).toLocaleTimeString()}
                  </Text>
                </div>
              </div>
            }
            type="error"
            closable
            onClose={() => removePersistentError(error.id)}
            closeIcon={<CloseOutlined style={{ fontSize: '12px' }} />}
            style={{ 
              marginBottom: '8px',
              fontSize: '13px'
            }}
            action={
              <Button
                size="small"
                type="text"
                onClick={() => removePersistentError(error.id)}
                icon={<CloseOutlined />}
                style={{ color: '#ff4d4f' }}
              />
            }
          />
        ))}
      </Space>
    </div>
  );
};