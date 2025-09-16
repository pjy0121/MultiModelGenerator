import React, { useEffect } from 'react';
import { Modal, Form, Input, Select, Typography, message, Button, Tooltip, Divider } from 'antd';
import { InfoCircleOutlined, CopyOutlined } from '@ant-design/icons';
import { NodeType, LLMProvider, WorkflowNode, AvailableModel } from '../types';
import { useNodeWorkflowStore } from '../store/nodeWorkflowStore';
import { DEFAULT_PROMPTS, PROMPT_VARIABLES } from '../config/defaultPrompts';

const { TextArea } = Input;
const { Option } = Select;
const { Text } = Typography;

interface NodeEditModalProps {
  visible: boolean;
  node: WorkflowNode | null;
  onClose: () => void;
  onSave: (nodeId: string, updates: Partial<WorkflowNode['data']>) => void;
}

export const NodeEditModal: React.FC<NodeEditModalProps> = ({
  visible,
  node,
  onClose,
  onSave
}) => {
  const { availableModels, loadAvailableModels } = useNodeWorkflowStore();
  const [form] = Form.useForm();

  // 모달이 열릴 때 폼 초기화
  useEffect(() => {
    if (visible && node) {
      form.setFieldsValue({
        label: node.data.label,
        content: node.data.content || '',
        llm_provider: node.data.llm_provider || LLMProvider.OPENAI,
        model_type: node.data.model_type || '',
        prompt: node.data.prompt || ''
      });
      
      if (node.data.llm_provider) {
        loadAvailableModels(node.data.llm_provider);
      }
    }
  }, [visible, node, form, loadAvailableModels]);

  // Provider 변경 시 모델 목록 로드
  const handleProviderChange = (provider: LLMProvider) => {
    loadAvailableModels(provider);
    form.setFieldValue('model_type', ''); // 모델 초기화
  };

  // 저장 핸들러
  const handleSave = async () => {
    if (!node) return;

    try {
      const values = await form.validateFields();
      onSave(node.id, values);
      message.success('노드가 성공적으로 업데이트되었습니다.');
      onClose();
    } catch (error) {
      message.error('폼 검증에 실패했습니다.');
    }
  };

  if (!node) return null;

  const isLLMNode = [NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(node.data.nodeType);
  const isContentNode = [NodeType.INPUT, NodeType.OUTPUT].includes(node.data.nodeType);

  // 노드 타입별 제목
  const getModalTitle = (nodeType: NodeType) => {
    const titles = {
      [NodeType.INPUT]: "입력 노드 편집",
      [NodeType.GENERATION]: "생성 노드 편집",
      [NodeType.ENSEMBLE]: "앙상블 노드 편집",
      [NodeType.VALIDATION]: "검증 노드 편집",
      [NodeType.OUTPUT]: "출력 노드 편집"
    };
    return titles[nodeType];
  };

  return (
    <Modal
      title={getModalTitle(node.data.nodeType)}
      open={visible}
      onOk={handleSave}
      onCancel={onClose}
      width={600}
      okText="저장"
      cancelText="취소"
    >
      <Form
        form={form}
        layout="vertical"
        style={{ marginTop: 16 }}
      >
        {/* 공통 필드: 라벨 */}
        <Form.Item
          label="노드 라벨"
          name="label"
          rules={[{ required: true, message: '노드 라벨을 입력해주세요.' }]}
        >
          <Input placeholder="노드의 표시명을 입력하세요" />
        </Form.Item>

        {/* Content 노드 (input-node, output-node) */}
        {isContentNode && (
          <Form.Item
            label="내용"
            name="content"
            rules={[{ required: true, message: '내용을 입력해주세요.' }]}
          >
            <TextArea
              rows={4}
              placeholder={
                node.data.nodeType === NodeType.INPUT 
                  ? "다음 노드로 전달할 입력 텍스트를 입력하세요"
                  : "출력 결과 설명을 입력하세요"
              }
            />
          </Form.Item>
        )}

        {/* LLM 노드 (generation-node, ensemble-node, validation-node) */}
        {isLLMNode && (
          <>
            <Form.Item
              label="LLM Provider"
              name="llm_provider"
              rules={[{ required: true, message: 'LLM Provider를 선택해주세요.' }]}
            >
              <Select 
                placeholder="Provider 선택"
                onChange={handleProviderChange}
              >
                <Option value={LLMProvider.OPENAI}>OpenAI</Option>
                <Option value={LLMProvider.GOOGLE}>Google</Option>
                <Option value={LLMProvider.PERPLEXITY}>Perplexity</Option>
              </Select>
            </Form.Item>

            <Form.Item
              label="모델"
              name="model_type"
              rules={[{ required: true, message: '모델을 선택해주세요.' }]}
            >
              <Select 
                placeholder="모델 선택"
                loading={availableModels.length === 0}
                showSearch
                filterOption={(input, option) =>
                  String(option?.children ?? '').toLowerCase().includes(input.toLowerCase())
                }
              >
                {availableModels.map((model: AvailableModel) => (
                  <Option key={model.id} value={model.id}>
                    <Text strong>{model.name}</Text>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label={
                <span>
                  프롬프트 
                  <Tooltip title="LLM에 전달될 프롬프트입니다. 변수를 사용하여 동적 데이터를 삽입할 수 있습니다.">
                    <InfoCircleOutlined style={{ marginLeft: 4, color: '#1890ff' }} />
                  </Tooltip>
                </span>
              }
              name="prompt"
              rules={[{ required: true, message: '프롬프트를 입력해주세요.' }]}
            >
              <div>
                <div style={{ marginBottom: 8 }}>
                  <Button 
                    size="small" 
                    icon={<CopyOutlined />}
                    onClick={() => {
                      const defaultPrompt = DEFAULT_PROMPTS[node.data.nodeType as keyof typeof DEFAULT_PROMPTS];
                      if (defaultPrompt) {
                        form.setFieldValue('prompt', defaultPrompt);
                        message.success('기본 프롬프트가 적용되었습니다.');
                      }
                    }}
                  >
                    기본 템플릿 사용
                  </Button>
                </div>
                
                <TextArea
                  rows={8}
                  placeholder={`${node.data.nodeType} 작업을 위한 프롬프트를 입력하세요.`}
                  style={{ fontFamily: 'Consolas, "Courier New", monospace' }}
                />
                
                <Divider style={{ margin: '12px 0' }} />
                
                <div style={{ fontSize: 12, color: '#666' }}>
                  <div style={{ fontWeight: 'bold', marginBottom: 4 }}>사용 가능한 변수:</div>
                  {Object.entries(PROMPT_VARIABLES).map(([variable, description]) => (
                    <div key={variable} style={{ marginBottom: 2 }}>
                      <code style={{ 
                        background: '#f5f5f5', 
                        padding: '1px 4px', 
                        borderRadius: 2,
                        fontSize: 11 
                      }}>
                        {variable}
                      </code>
                      <span style={{ marginLeft: 8 }}>{description}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Form.Item>
          </>
        )}
      </Form>
    </Modal>
  );
};