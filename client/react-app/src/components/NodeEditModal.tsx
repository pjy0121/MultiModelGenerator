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

const EditForm: React.FC<Omit<NodeEditModalProps, 'visible'>> = ({ node, onClose, onSave }) => {
  const { availableModels, loadAvailableModels } = useNodeWorkflowStore();
  const [form] = Form.useForm();

  // 모달이 열릴 때 폼 초기화
  useEffect(() => {
    if (node) {
      const provider = node.data.llm_provider || LLMProvider.GOOGLE;
      
      form.setFieldsValue({
        label: node.data.label,
        content: node.data.content || '',
        llm_provider: provider,
        model_type: node.data.model_type || '',
        prompt: node.data.prompt || '',
        output_format: node.data.output_format || ''
      });
      
      // 해당 provider의 모델이 아직 로드되지 않았을 때 로드
      const currentProviderModels = availableModels.filter(model => model.provider === provider);
      if (currentProviderModels.length === 0) {
        loadAvailableModels(provider);
      }
    }
  }, [node, form, availableModels, loadAvailableModels]);

  // 모델이 로드될 때 기본 모델 자동 선택
  useEffect(() => {
    if (node && availableModels.length > 0) {
      const currentProvider = node.data.llm_provider || LLMProvider.GOOGLE;
      const currentModel = node.data.model_type;
      
      if (!currentModel || !availableModels.some(m => m.value === currentModel && m.provider === currentProvider)) {
        const providerModels = availableModels.filter(model => model.provider === currentProvider);
        
        if (providerModels.length > 0) {
          const defaultModel = currentProvider === LLMProvider.GOOGLE 
            ? providerModels.find(m => m.value.includes('gemini-2.0-flash')) || providerModels[0]
            : providerModels.find(m => m.value.includes('gpt-4o-mini')) || providerModels[0];
          
          form.setFieldValue('model_type', defaultModel.value);
        }
      }
    }
  }, [availableModels, node, form]);

  // Provider 변경 시 모델 목록 로드 및 기본 모델 선택
  const handleProviderChange = async (provider: LLMProvider) => {
    form.setFieldValue('model_type', '');
    await loadAvailableModels(provider);
    
    setTimeout(() => {
      const state = useNodeWorkflowStore.getState();
      const providerModels = state.availableModels.filter(model => model.provider === provider);
      
      if (providerModels.length > 0) {
        const defaultModel = provider === LLMProvider.GOOGLE
          ? providerModels.find(m => m.value.includes('gemini-2.0-flash')) || providerModels[0]
          : providerModels.find(m => m.value.includes('gpt-4o-mini')) || providerModels[0];
        
        form.setFieldValue('model_type', defaultModel.value);
      }
    }, 100);
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
      open={true} // 이 컴포넌트는 항상 열려있는 것으로 간주
      onOk={handleSave}
      onCancel={onClose}
      width={600}
      okText="저장"
      cancelText="취소"
      destroyOnHidden // 모달이 닫힐 때 내부 상태를 완전히 파괴
    >
      <Form
        form={form}
        layout="vertical"
        style={{ marginTop: 16 }}
        key={node.id}
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
                <Option value={LLMProvider.GOOGLE}>Google AI Studio</Option>
                <Option value={LLMProvider.OPENAI}>OpenAI</Option>
              </Select>
            </Form.Item>

            <Form.Item
              label={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>모델</span>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => {
                      const provider = form.getFieldValue('llm_provider') || LLMProvider.GOOGLE;
                      loadAvailableModels(provider);
                      message.info('모델 목록을 새로고침했습니다.');
                    }}
                    style={{ padding: 0, fontSize: '12px' }}
                  >
                    새로고침
                  </Button>
                </div>
              }
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
                {availableModels
                  .filter(model => model.provider === (form.getFieldValue('llm_provider') || LLMProvider.GOOGLE))
                  .map((model: AvailableModel) => (
                    <Option key={model.value} value={model.value}>
                      <Text strong>{model.label}</Text>
                    </Option>
                  ))
                }
              </Select>
            </Form.Item>

            <Form.Item
              label={
                <span>
                  출력 형식
                  <Tooltip title="LLM이 출력할 내용 중 핵심 결과를 보여줄 형식을 작성하세요. 이 형식으로 출력된 내용이 다음 노드로 전달됩니다.">
                    <InfoCircleOutlined style={{ marginLeft: 4, color: '#1890ff' }} />
                  </Tooltip>
                </span>
              }
              name="output_format"
            >
              <div>
                <div style={{ marginBottom: 8, display: 'flex', gap: 8 }}>
                  <Button 
                    size="small" 
                    onClick={() => form.setFieldValue('output_format', '{\n  "requirements": [\n    {\n      "id": "REQ-001",\n      "requirement": "[구체적인 요구사항 내용]"\n      "reference": "[원문 내용과 위치]"\n    }\n  ]\n}')}
                  >
                    JSON 예시
                  </Button>
                  <Button
                    size="small" 
                    onClick={() => form.setFieldValue('output_format', '| ID | 요구사항 | 근거(reference) |\n|---|---|---|\n| REQ-001 | [구체적인 요구사항 내용] | [원문 내용과 위치]\n| REQ-002 | ... | ... |')}
                  >
                    마크다운 표 예시
                  </Button>
                </div>
                <Form.Item name="output_format" noStyle>
                  <TextArea
                    rows={4}
                    placeholder="예: 요구사항 목록"
                    style={{ fontFamily: 'Consolas, "Courier New", monospace' }}
                  />
                </Form.Item>
              </div>
            </Form.Item>

            <Form.Item
              label={
                <span>
                  프롬프트
                  <Tooltip title="LLM에 전달될 프롬프트입니다. 미리 정의된 변수를 사용하여 동적으로 데이터를 삽입할 수 있습니다.">
                    <InfoCircleOutlined style={{ marginLeft: 4, color: '#1890ff' }} />
                  </Tooltip>
                </span>
              }
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
                
                <Form.Item name="prompt" noStyle>
                  <TextArea
                    rows={8}
                    placeholder="프롬프트를 입력하세요."
                    style={{ fontFamily: 'Consolas, "Courier New", monospace' }}
                  />
                </Form.Item>
                
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

export const NodeEditModal: React.FC<NodeEditModalProps> = ({ visible, node, onClose, onSave }) => {
  if (!visible || !node) {
    return null;
  }

  return <EditForm node={node} onClose={onClose} onSave={onSave} />;
};