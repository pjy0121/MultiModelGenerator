import React, { useState, useEffect } from 'react';
import { Modal, Form, Select, Input, message } from 'antd';
import { WorkflowNodeData, ModelType } from '../types';

const { TextArea } = Input;

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

  useEffect(() => {
    if (nodeData && visible) {
      console.log('모달에서 받은 노드 데이터:', nodeData); // 디버깅용
      form.setFieldsValue({
        model_type: nodeData.model_type,
        prompt: nodeData.prompt
      });
    }
  }, [nodeData, visible, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      console.log('폼 값:', values); // 디버깅용
      
      onSave({
        model_type: values.model_type,
        prompt: values.prompt,
        label: getModelLabel(values.model_type)
      });
      
      message.success('노드가 업데이트되었습니다.');
    } catch (error) {
      console.error('폼 검증 실패:', error);
      message.error('입력값을 확인해주세요.');
    }
  };

  const getModelLabel = (modelType: ModelType): string => {
    switch (modelType) {
      case ModelType.PERPLEXITY_SONAR_PRO:
        return "Sonar Pro";
      case ModelType.PERPLEXITY_SONAR_MEDIUM:
        return "Sonar Medium";
      case ModelType.OPENAI_GPT4:
        return "GPT-4";
      case ModelType.OPENAI_GPT35:
        return "GPT-3.5";
      default:
        return "Unknown";
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
      width={800}
      destroyOnClose={true} // 모달이 닫힐 때 완전히 제거
    >
      {nodeData && (
        <Form form={form} layout="vertical">
          <Form.Item
            name="model_type"
            label="모델 타입"
            rules={[{ required: true, message: '모델 타입을 선택해주세요.' }]}
          >
            <Select placeholder="모델을 선택하세요">
              <Select.Option value={ModelType.PERPLEXITY_SONAR_PRO}>
                Perplexity Sonar Pro
              </Select.Option>
              <Select.Option value={ModelType.PERPLEXITY_SONAR_MEDIUM}>
                Perplexity Sonar Medium
              </Select.Option>
              <Select.Option value={ModelType.OPENAI_GPT4} disabled>
                OpenAI GPT-4 (Coming Soon)
              </Select.Option>
              <Select.Option value={ModelType.OPENAI_GPT35} disabled>
                OpenAI GPT-3.5 (Coming Soon)
              </Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="prompt"
            label="프롬프트"
            rules={[{ required: true, message: '프롬프트를 입력해주세요.' }]}
          >
            <TextArea
              rows={15}
              placeholder="프롬프트를 입력하세요..."
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
        </Form>
      )}
    </Modal>
  );
};

export default NodeEditModal;
