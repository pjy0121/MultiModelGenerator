import React, { useEffect } from 'react';
import { Modal, Form, Select, message } from 'antd';
import { WorkflowNodeData } from '../types';
import { useWorkflowStore } from '../store/workflowStore';

interface NodeEditModalProps {
  visible: boolean;
  nodeData: WorkflowNodeData | null;
  onSave: (data: Partial<WorkflowNodeData>) => void;
  onCancel: () => void;
}

const NodeEditModal: React.FC<NodeEditModalProps> = ({
  visible,
  nodeData,
  onSave,
  onCancel
}) => {
  const [form] = Form.useForm();
  
  // WorkflowStore에서 모든 모델 목록 가져오기
  const { allModels, loadAllModels } = useWorkflowStore();

  // 컴포넌트 마운트 시 모델 목록 로드
  useEffect(() => {
    if (visible && (!allModels || allModels.length === 0)) {
      loadAllModels();
    }
  }, [visible, allModels, loadAllModels]);

  // 노드 데이터로 폼 초기화
  useEffect(() => {
    if (nodeData && visible) {

      // 현재 노드의 모델 이름 찾기
      let selectedModelId = '';
      if (nodeData.model) {
        selectedModelId = nodeData.model;
      } else if ('model_type' in nodeData && typeof nodeData.model_type === 'string') {
        // 기존 호환성을 위해 model_type 지원 (타입 안전하게)
        selectedModelId = nodeData.model_type;
      }

      // 기본값으로 첫 번째 사용 가능한 모델 선택
      if (!selectedModelId && allModels && allModels.length > 0) {
        const firstAvailableModel = allModels.find(m => m.available);
        selectedModelId = firstAvailableModel ? firstAvailableModel.id : allModels[0].id;
      }
      
      form.setFieldsValue({
        model: selectedModelId
      });
    }
  }, [nodeData, visible, form, allModels]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      
      const selectedModel = allModels?.find(m => m.id === values.model);
      
      // 비활성화된 모델 선택 확인
      if (selectedModel && !selectedModel.available) {
        message.warning('선택된 모델은 현재 사용할 수 없습니다. API 키를 확인해주세요.');
        return;
      }
      
      onSave({
        model: values.model,
        provider: selectedModel?.provider, // 선택된 모델의 provider 정보 저장
        label: selectedModel ? selectedModel.name : 'Unknown Model'
      });
      
      message.success('노드가 업데이트되었습니다.');
    } catch (error) {
      message.error('입력값을 확인해주세요.');
    }
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  return (
    <Modal
      title={`노드 편집 - ${nodeData?.layer || ''}`}
      open={visible}
      onOk={handleSave}
      onCancel={handleCancel}
      width={500}
      destroyOnClose={true}
    >
      {nodeData && (
        <Form form={form} layout="vertical">
          <Form.Item
            name="model"
            label="모델 선택"
            rules={[{ required: true, message: '모델을 선택해주세요.' }]}
          >
            <Select placeholder="모델을 선택하세요">
              {allModels?.map((model) => (
                <Select.Option 
                  key={model.id} 
                  value={model.id}
                  disabled={!model.available}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>{model.name}</span>
                    <div>
                      <span style={{ 
                        color: model.provider === 'openai' ? '#52c41a' : 
                              model.provider === 'google' ? '#4285f4' : '#722ed1',
                        fontSize: '12px',
                        marginRight: '8px'
                      }}>
                        {model.provider.toUpperCase()}
                      </span>
                      {!model.available && (
                        <span style={{ color: '#ff4d4f', fontSize: '12px' }}>
                          사용 불가
                        </span>
                      )}
                    </div>
                  </div>
                </Select.Option>
              )) || []}
            </Select>
          </Form.Item>
        </Form>
      )}
    </Modal>
  );
};

export default NodeEditModal;
