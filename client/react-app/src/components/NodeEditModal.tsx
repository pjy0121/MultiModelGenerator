import React, { useEffect, useCallback, useState } from 'react';
import { Modal, Form, Input, Select, Typography, Button, Tooltip, Divider, message } from 'antd';
import { CopyOutlined, InfoCircleOutlined, SettingOutlined } from '@ant-design/icons';
import { showErrorMessage } from '../utils/messageUtils';
import { NodeType, LLMProvider, WorkflowNode, AvailableModel, SearchIntensity, KnowledgeBase } from '../types';
import { useDataLoadingStore } from '../store/dataLoadingStore';
import { DEFAULT_PROMPTS, OUTPUT_FORMAT_TEMPLATES, PROMPT_VARIABLES } from '../config/defaultPrompts';
import { UI_COLORS } from '../config/constants';
import KnowledgeBaseManageModal from './KnowledgeBaseManageModal';

const { TextArea } = Input;
const { Option } = Select;
const { Text } = Typography;

interface NodeEditModalProps {
  open: boolean;
  node: WorkflowNode | null;
  onClose: () => void;
  onSave: (nodeId: string, updates: Partial<WorkflowNode['data']>) => void;
}

const EditForm: React.FC<Omit<NodeEditModalProps, 'open'>> = ({ node, onClose, onSave }) => {
  const { availableModels, loadAvailableModels, knowledgeBases, loadKnowledgeBases } = useDataLoadingStore();
  const [form] = Form.useForm();
  const [kbManageModalVisible, setKbManageModalVisible] = useState<boolean>(false);
  const isLLMNode = node ? [NodeType.GENERATION, NodeType.ENSEMBLE, NodeType.VALIDATION].includes(node.data.nodeType) : false;
  const isContextNode = node ? node.data.nodeType === NodeType.CONTEXT : false;

  // Provider별 기본 모델 선택 헬퍼 함수
  const getDefaultModelForProvider = (provider: LLMProvider, models: AvailableModel[]) => {
    if (provider === LLMProvider.GOOGLE) {
      return models.find(m => m.value.includes('gemini-1.5-flash')) || models[0];
    } else if (provider === LLMProvider.OPENAI) {
      return models.find(m => m.value.includes('gpt-4o-mini')) || models[0];
    } else if (provider === LLMProvider.INTERNAL) {
      return models[0];
    } else {
      return models[0];
    }
  };

  // 모달이 열릴 때 폼 초기화 (node.id가 변경될 때만)
  useEffect(() => {
    if (node) {
      if (isLLMNode || isContextNode) {
        loadKnowledgeBases();
      }

      const provider = node.data.llm_provider || LLMProvider.GOOGLE;
      
      // 노드 타입에 따른 기본 검색 강도 설정
      const getDefaultSearchIntensity = () => {
        if (node.data.search_intensity) {
          // 유효한 값인지 확인
          const validValues = [SearchIntensity.EXACT, SearchIntensity.STANDARD, SearchIntensity.COMPREHENSIVE];
          if (validValues.includes(node.data.search_intensity as SearchIntensity)) {
            return node.data.search_intensity;
          }
          // 유효하지 않은 값이면 기본값 반환
          return SearchIntensity.STANDARD;
        }
        // 모든 노드 타입에서 표준 검색을 기본값으로 사용
        return SearchIntensity.STANDARD;
      };

      form.setFieldsValue({
        label: node.data.label,
        content: node.data.content || '',
        llm_provider: provider,
        model_type: node.data.model_type || '',
        prompt: node.data.prompt || '',
        output_format: node.data.output_format || '',
        knowledge_base: node.data.knowledge_base || (isContextNode ? 'none' : ''),
        search_intensity: getDefaultSearchIntensity(),
        rerank_provider: node.data.rerank_provider || LLMProvider.NONE, // 기본값: 재정렬 사용 안 함
        additional_context: node.data.additional_context || '',
      });
      
      // 해당 provider의 모델이 아직 로드되지 않았을 때 로드
      const currentProviderModels = availableModels.filter((model: AvailableModel) => model.provider === provider);
      if (currentProviderModels.length === 0 && isLLMNode) {
        loadAvailableModels(provider);
      }
      
    }
  }, [node?.id]); // node.id가 변경될 때만 실행

  // 모델이 로드될 때 기본 모델 자동 선택 (초기 로드 시에만)
  useEffect(() => {
    if (node && availableModels.length > 0) {
      const currentProvider = node.data.llm_provider || LLMProvider.GOOGLE;
      const currentModel = node.data.model_type;
      
      // 기존 모델이 없거나 현재 provider에 해당하는 모델이 없을 때만 자동 선택
      const hasValidModel = currentModel && availableModels.some((m: AvailableModel) => m.value === currentModel && m.provider === currentProvider);
      
      if (!hasValidModel) {
        const providerModels = availableModels.filter((model: AvailableModel) => model.provider === currentProvider);
        
        if (providerModels.length > 0) {
          const defaultModel = getDefaultModelForProvider(currentProvider, providerModels);
          
          // 폼에 이미 다른 값이 설정되어 있지 않은 경우에만 설정
          const currentFormModel = form.getFieldValue('model_type');
          if (!currentFormModel || currentFormModel === '') {
            form.setFieldValue('model_type', defaultModel.value);
          }
        }
      }
    }
  }, [availableModels, node?.id]); // node.id 변경 시에만 실행되도록 수정

  // Provider 변경 시 모델 목록 로드 및 기본 모델 선택
  const handleProviderChange = useCallback(async (provider: LLMProvider) => {    
    form.setFieldValue('model_type', '');
    
    try {
      // 모델 목록 로드 (실패 시 store에서 해당 provider 모델들이 제거됨)
      await loadAvailableModels(provider);
      
      // 현재 available models를 직접 사용하여 circular reference 방지
      const providerModels = availableModels.filter((model: AvailableModel) => model.provider === provider);
      
      if (providerModels.length > 0) {
        const defaultModel = getDefaultModelForProvider(provider, providerModels);
        console.log('Setting default model:', defaultModel);
        // 다음 틱에 실행하여 상태 충돌 방지
        setTimeout(() => {
          form.setFieldValue('model_type', defaultModel.value);
        }, 0);
      }
      // providerModels.length === 0인 경우 모델 필드는 비어있는 상태로 유지됨
    } catch (error) {
      console.error('Error in handleProviderChange:', error);
    }
  }, [loadAvailableModels, availableModels, form]);

  // 저장 핸들러
  const handleSave = async () => {
    if (!node) return;
    try {
      const values = await form.validateFields();
      onSave(node.id, values);
      message.success('노드가 성공적으로 업데이트되었습니다.');
      onClose();
    } catch (error) {
      showErrorMessage('폼 검증에 실패했습니다.');
    }
  };

  if (!node) return null;

  const isContentNode = [NodeType.INPUT, NodeType.OUTPUT].includes(node.data.nodeType);

  const getModalTitle = (nodeType: NodeType) => {
    const titles = {
      [NodeType.INPUT]: "입력 노드 편집",
      [NodeType.GENERATION]: "생성 노드 편집",
      [NodeType.ENSEMBLE]: "앙상블 노드 편집",
      [NodeType.VALIDATION]: "검증 노드 편집",
      [NodeType.CONTEXT]: "컨텍스트 노드 편집",
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
        {/* 공통 필드: 이름 */}
        <Form.Item
          label="노드 이름"
          name="label"
          rules={[{ required: true, message: '노드 이름을 입력해주세요.' }]}
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
                <Option value={LLMProvider.INTERNAL}>Internal LLM</Option>
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
                onChange={(value) => {
                  console.log('Model selection changed:', value);
                  // 명시적으로 모델 변경 처리
                  form.setFieldValue('model_type', value);
                  // 값이 제대로 설정되었는지 확인
                  setTimeout(() => {
                    const currentValue = form.getFieldValue('model_type');
                    console.log('Current form model after change:', currentValue);
                  }, 10);
                }}
                value={form.getFieldValue('model_type')}
              >
                {availableModels
                  .filter((model: AvailableModel) => model.provider === (form.getFieldValue('llm_provider') || LLMProvider.GOOGLE))
                  .map((model: AvailableModel) => (
                    <Option key={model.value} value={model.value}>
                      <Text strong>{model.label}</Text>
                    </Option>
                  ))
                }
              </Select>
            </Form.Item>

            <Divider>출력 형식 및 프롬프트</Divider>

            <Form.Item
              label={
                <span>
                  출력 형식
                  <Tooltip title="LLM이 출력할 내용 중 핵심 결과를 보여줄 형식을 작성하세요. 이 형식으로 출력된 내용이 다음 노드로 전달됩니다.">
                    <InfoCircleOutlined style={{ marginLeft: 4, color: UI_COLORS.UI.INFO }} />
                  </Tooltip>
                </span>
              }
              name="output_format"
            >
              <div>
                <div style={{ marginBottom: 8, display: 'flex', gap: 8 }}>
                  <Button 
                    size="small" 
                    icon={<CopyOutlined />}
                    onClick={() => {
                      if (!node) return;
                      const defaultOutputFormat = OUTPUT_FORMAT_TEMPLATES[node.data.nodeType as keyof typeof OUTPUT_FORMAT_TEMPLATES];
                      if (defaultOutputFormat) {
                        form.setFieldValue('output_format', defaultOutputFormat);
                        message.success('기본 출력 형식이 적용되었습니다.');
                      }
                    }}
                  >
                    기본 템플릿
                  </Button>
                  <Button 
                    size="small" 
                    onClick={() => form.setFieldValue('output_format', '{\n  "requirements": [\n    {\n      "id": "REQ-001",\n      "requirement": "[구체적인 요구사항 내용]",\n      "reference": "[원문 내용과 위치]"\n    }\n  ]\n}')}
                  >
                    JSON 예시
                  </Button>
                  <Button
                    size="small" 
                    onClick={() => form.setFieldValue('output_format', '| ID | 요구사항 | 근거(reference) |\n|---|---|---|\n| REQ-001 | [구체적인 요구사항 내용] | [원문 내용과 위치] |\n| REQ-002 | ... | ... |')}
                  >
                    마크다운 표 예시
                  </Button>
                </div>
                <Form.Item name="output_format" noStyle>
                  <TextArea
                    rows={4}
                    placeholder="핵심 결과의 출력 형식을 입력하세요."
                    style={{ fontFamily: 'Consolas, "Courier New", monospace' }}
                  />
                </Form.Item>
              </div>
            </Form.Item>

            <Form.Item
              label={
                <span>
                  프롬프트
                  <Tooltip title="LLM에 전달할 프롬프트를 입력하세요.">
                    <InfoCircleOutlined style={{ marginLeft: 4, color: UI_COLORS.UI.INFO }} />
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
                      if (!node) return;
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
                
                <div style={{ fontSize: 12, color: UI_COLORS.TEXT.SECONDARY }}>
                  <div style={{ fontWeight: 'bold', marginBottom: 4 }}>사용 가능한 변수:</div>
                  {Object.entries(PROMPT_VARIABLES).map(([variable, description]) => (
                    <div key={variable} style={{ marginBottom: 2 }}>
                      <code style={{ 
                        background: UI_COLORS.UI.BACKGROUND_LIGHT, 
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

        {/* Context 노드 (context-node) */}
        {isContextNode && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontWeight: 500 }}>지식 베이스</span>
              <Button
                type="default"
                size="small"
                icon={<SettingOutlined />}
                onClick={() => setKbManageModalVisible(true)}
              >
                목록 수정
              </Button>
            </div>
            
            <Form.Item
              name="knowledge_base"
              tooltip="검색에 사용할 지식 베이스를 선택합니다. '없음'을 선택하면 추가 내용만 사용합니다."
            >
              <Select placeholder="지식 베이스 선택">
                <Option value="none">
                  <Text type="secondary">없음</Text>
                </Option>
                {knowledgeBases.map((kb: KnowledgeBase) => (
                  <Option key={kb.name} value={kb.name}>
                    <Text strong>{kb.name}</Text>
                    <Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>
                      ({kb.chunk_count}개 청크)
                    </Text>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="검색 강도"
              name="search_intensity"
              rules={[{ required: true, message: '검색 강도를 선택해주세요.' }]}
              tooltip="문서 검색 강도를 선택합니다."
            >
              <Select>
                <Option value={SearchIntensity.EXACT}>
                  🎯 정확 (최대한 정확하게 검색)
                </Option>
                <Option value={SearchIntensity.STANDARD}>
                  ⚖️ 기본 (균형잡힌 검색)
                </Option>
                <Option value={SearchIntensity.COMPREHENSIVE}>
                  🔬 포괄 (광범위한 문맥 검색)
                </Option>
              </Select>
            </Form.Item>

            <Form.Item
              label="재정렬 사용"
              name="rerank_provider"
              tooltip="검색된 청크를 LLM 기반 재정렬 모델(BAAI/bge-reranker-v2-m3)로 쿼리와의 관련도 순으로 다시 정렬합니다. 검색 정확도를 높이고 싶을 때 사용하세요."
            >
              <Select placeholder="재정렬 사용 여부 선택">
                <Option value={LLMProvider.NONE}>사용 안 함</Option>
                <Option value="enabled">사용 (BAAI/bge-reranker-v2-m3)</Option>
              </Select>
            </Form.Item>

            <Divider style={{ margin: '16px 0' }} />
            
            <Form.Item
              label={
                <span>
                  추가 내용
                  <Tooltip title="지식 베이스 검색 결과에 추가로 포함할 사용자 정의 컨텍스트를 입력합니다. 지식 베이스를 선택하지 않고 이 내용만 사용할 수도 있습니다.">
                    <InfoCircleOutlined style={{ marginLeft: 4, color: UI_COLORS.UI.INFO }} />
                  </Tooltip>
                </span>
              }
              name="additional_context"
            >
              <TextArea
                rows={6}
                placeholder="추가로 포함할 컨텍스트를 입력하세요. (선택사항)"
                style={{ fontFamily: 'Consolas, "Courier New", monospace' }}
              />
            </Form.Item>
          </>
        )}
      </Form>

      {/* 지식 베이스 관리 모달 */}
      <KnowledgeBaseManageModal
        visible={kbManageModalVisible}
        onClose={() => setKbManageModalVisible(false)}
        onRefresh={loadKnowledgeBases}
      />
    </Modal>
  );
};

const NodeEditModal: React.FC<NodeEditModalProps> = ({ open, node, onClose, onSave }) => {
  if (!open || !node) {
    return null;
  }

  return <EditForm node={node} onClose={onClose} onSave={onSave} />;
};

export default NodeEditModal;