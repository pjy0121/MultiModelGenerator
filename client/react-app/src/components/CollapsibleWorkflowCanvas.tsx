import React, { useState } from 'react';
import { Space, Button, Modal, message, Input } from 'antd';
import { SaveOutlined, ImportOutlined, UndoOutlined, DownloadOutlined } from '@ant-design/icons';
import WorkflowCanvas from './WorkflowCanvas';
import { useWorkflowStore } from '../store/workflowStore';
import { AnyWorkflowNode } from '../types';

const { TextArea } = Input;

const CollapsibleWorkflowCanvas: React.FC = () => {
  const { 
    setNodes, 
    saveCurrentWorkflow, 
    restoreWorkflow, 
    exportToJSON,
    isExecuting
  } = useWorkflowStore();
  
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [jsonText, setJsonText] = useState('');

  const handleSave = () => {
    saveCurrentWorkflow();
    message.success('현재 워크플로우 상태가 저장되었습니다.');
  };

  // ✅ 복원 시 뷰포트도 함께 복원되도록 개선
  const handleRestore = async () => {
    if (isExecuting) {
      Modal.warning({
        title: '워크플로우 실행 중',
        content: '워크플로우가 실행 중입니다. 실행이 완료된 후 복원을 시도해주세요.',
        okText: '확인'
      });
      return;
    }
    
    try {
      const success = await restoreWorkflow();
      if (success) {
        message.success('저장된 워크플로우 상태를 복원했습니다.');
        // 뷰포트 복원은 store에서 자동으로 처리됨
      } else {
        message.warning('저장된 워크플로우가 없습니다.');
      }
    } catch (error) {
      console.error('복원 중 오류:', error);
      message.error('워크플로우 복원 중 오류가 발생했습니다.');
    }
  };

  const handleExport = () => {
    exportToJSON();
    message.success('워크플로우가 JSON 파일로 내보내졌습니다.');
  };

  const handleJsonChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setJsonText(e.target.value);
  };

  const handleImportJson = () => {
    if (isExecuting) {
      Modal.warning({
        title: '워크플로우 실행 중',
        content: '워크플로우가 실행 중입니다. 실행이 완료된 후 JSON 파일을 불러와주세요.',
        okText: '확인'
      });
      return;
    }

    try {
      const workflowData = JSON.parse(jsonText.trim());
      
      if (!workflowData.nodes && !workflowData.workflow?.nodes) {
        throw new Error('유효하지 않은 워크플로우 데이터입니다.');
      }

      const nodesToImport = workflowData.nodes || workflowData.workflow?.nodes;
      setNodes(nodesToImport as AnyWorkflowNode[]);
      setImportModalVisible(false);
      setJsonText('');
      message.success('워크플로우를 불러왔습니다.');
      
    } catch (error) {
      console.error('JSON 파싱 오류:', error);
      message.error('유효하지 않은 JSON 형식입니다.');
    }
  };

  const openImportModal = () => {
    if (isExecuting) {
      Modal.warning({
        title: '워크플로우 실행 중',
        content: '워크플로우가 실행 중입니다. 실행이 완료된 후 JSON 파일을 불러와주세요.',
        okText: '확인'
      });
      return;
    }
    setImportModalVisible(true);
    setJsonText('');
  };

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      position: 'relative'
    }}>
      {/* 워크플로우 캔버스 */}
      <div style={{ 
        border: '1px solid #d9d9d9', 
        borderRadius: '6px',
        backgroundColor: 'white',
        height: '600px',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <WorkflowCanvas />

        {/* 텍스트 포함 버튼 패널 */}
        <div style={{
          position: 'absolute',
          bottom: '16px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 1000,
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(8px)',
          padding: '12px 20px',
          borderRadius: '32px',
          boxShadow: '0 6px 24px rgba(0, 0, 0, 0.15)',
          border: '1px solid rgba(255, 255, 255, 0.3)'
        }}>
          <Space size="middle">
            <Button 
              icon={<SaveOutlined />}
              onClick={handleSave}
              type="primary"
              size="middle"
              style={{ 
                minWidth: '140px',
                height: '36px',
                borderRadius: '18px'
              }}
            >
              워크플로우 저장
            </Button>
            
            <Button 
              icon={<UndoOutlined />}
              onClick={handleRestore}
              size="middle"
              style={{ 
                minWidth: '140px',
                height: '36px',
                borderRadius: '18px'
              }}
            >
              워크플로우 복원
            </Button>
            
            <div style={{ 
              width: '1px', 
              height: '24px', 
              backgroundColor: '#e0e0e0', 
              margin: '0 8px' 
            }} />
            
            <Button 
              icon={<DownloadOutlined />}
              onClick={handleExport}
              size="middle"
              style={{ 
                minWidth: '130px',
                height: '36px',
                borderRadius: '18px'
              }}
            >
              JSON 내보내기
            </Button>
            
            <Button 
              icon={<ImportOutlined />}
              onClick={openImportModal}
              size="middle"
              style={{ 
                minWidth: '130px',
                height: '36px',
                borderRadius: '18px'
              }}
            >
              JSON 불러오기
            </Button>
          </Space>
        </div>
      </div>

      {/* JSON 붙여넣기 모달 */}
      <Modal
        title="JSON 워크플로우 불러오기"
        open={importModalVisible}
        onOk={handleImportJson}
        onCancel={() => setImportModalVisible(false)}
        width={600}
        okText="불러오기"
        cancelText="취소"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ marginBottom: 8 }}>
            Export된 JSON 데이터를 붙여넣으세요:
          </div>
          <TextArea
            placeholder='{"nodes":[...]} 또는 {"workflow":{"nodes":[...]}}'
            value={jsonText}
            onChange={handleJsonChange}
            rows={12}
            style={{ fontFamily: 'monospace', fontSize: '12px' }}
          />
          <div style={{ color: '#666', fontSize: '12px' }}>
            💡 JSON Export로 내보낸 파일 내용을 전체 복사하여 붙여넣으세요.
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default CollapsibleWorkflowCanvas;
