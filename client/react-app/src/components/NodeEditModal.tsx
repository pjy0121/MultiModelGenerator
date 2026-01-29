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

  // Helper function to select default model for each provider
  const getDefaultModelForProvider = (provider: LLMProvider, models: AvailableModel[]) => {
    if (provider === LLMProvider.GOOGLE) {
      return models.find(m => m.value.includes('gemini-2.0-flash-lite')) || models[0];
    } else if (provider === LLMProvider.OPENAI) {
      return models.find(m => m.value.includes('gpt-4o-mini')) || models[0];
    } else if (provider === LLMProvider.INTERNAL) {
      return models[0];
    } else {
      return models[0];
    }
  };

  // Initialize form when modal opens (only when node.id changes)
  useEffect(() => {
    if (node) {
      if (isLLMNode || isContextNode) {
        loadKnowledgeBases();
      }

      const provider = node.data.llm_provider || LLMProvider.GOOGLE;

      // Set default search intensity based on node type
      const getDefaultSearchIntensity = () => {
        if (node.data.search_intensity) {
          // Check if value is valid
          const validValues = [SearchIntensity.EXACT, SearchIntensity.STANDARD, SearchIntensity.COMPREHENSIVE];
          if (validValues.includes(node.data.search_intensity as SearchIntensity)) {
            return node.data.search_intensity;
          }
          // Return default value if invalid
          return SearchIntensity.STANDARD;
        }
        // Use standard search as default for all node types
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
        rerank_provider: node.data.rerank_provider || LLMProvider.NONE, // Default: no reranking
        additional_context: node.data.additional_context || '',
      });

      // Load models if not already loaded for this provider
      const currentProviderModels = availableModels.filter((model: AvailableModel) => model.provider === provider);
      if (currentProviderModels.length === 0 && isLLMNode) {
        loadAvailableModels(provider);
      }

    }
  }, [node?.id]); // Only run when node.id changes

  // Auto-select default model when models are loaded (only on initial load)
  useEffect(() => {
    if (node && availableModels.length > 0) {
      const currentProvider = node.data.llm_provider || LLMProvider.GOOGLE;
      const currentModel = node.data.model_type;

      // Only auto-select if no existing model or current model doesn't belong to current provider
      const hasValidModel = currentModel && availableModels.some((m: AvailableModel) => m.value === currentModel && m.provider === currentProvider);

      if (!hasValidModel) {
        const providerModels = availableModels.filter((model: AvailableModel) => model.provider === currentProvider);

        if (providerModels.length > 0) {
          const defaultModel = getDefaultModelForProvider(currentProvider, providerModels);

          // Only set if form doesn't already have another value
          const currentFormModel = form.getFieldValue('model_type');
          if (!currentFormModel || currentFormModel === '') {
            form.setFieldValue('model_type', defaultModel.value);
          }
        }
      }
    }
  }, [availableModels, node?.id]); // Modified to only run when node.id changes

  // Load model list and select default model when provider changes
  const handleProviderChange = useCallback(async (provider: LLMProvider) => {
    form.setFieldValue('model_type', '');

    try {
      // Load model list (if fails, models for that provider are removed from store)
      await loadAvailableModels(provider);

      // Use current available models directly to prevent circular reference
      const providerModels = availableModels.filter((model: AvailableModel) => model.provider === provider);

      if (providerModels.length > 0) {
        const defaultModel = getDefaultModelForProvider(provider, providerModels);
        console.log('Setting default model:', defaultModel);
        // Execute on next tick to prevent state conflicts
        setTimeout(() => {
          form.setFieldValue('model_type', defaultModel.value);
        }, 0);
      }
      // If providerModels.length === 0, model field remains empty
    } catch (error) {
      console.error('Error in handleProviderChange:', error);
    }
  }, [loadAvailableModels, availableModels, form]);

  // Save handler
  const handleSave = async () => {
    if (!node) return;
    try {
      const values = await form.validateFields();
      onSave(node.id, values);
      message.success('Node updated successfully.');
      onClose();
    } catch (error) {
      showErrorMessage('Form validation failed.');
    }
  };

  if (!node) return null;

  const isContentNode = [NodeType.INPUT, NodeType.OUTPUT].includes(node.data.nodeType);

  const getModalTitle = (nodeType: NodeType) => {
    const titles = {
      [NodeType.INPUT]: "Edit Input Node",
      [NodeType.GENERATION]: "Edit Generation Node",
      [NodeType.ENSEMBLE]: "Edit Ensemble Node",
      [NodeType.VALIDATION]: "Edit Validation Node",
      [NodeType.CONTEXT]: "Edit Context Node",
      [NodeType.OUTPUT]: "Edit Output Node"
    };
    return titles[nodeType];
  };

  return (
    <Modal
      title={getModalTitle(node.data.nodeType)}
      open={true} // This component is considered always open
      onOk={handleSave}
      onCancel={onClose}
      width={600}
      okText="Save"
      cancelText="Cancel"
      destroyOnHidden // Completely destroy internal state when modal closes
    >
      <Form
        form={form}
        layout="vertical"
        style={{ marginTop: 16 }}
        key={node.id}
      >
        {/* Common field: Name */}
        <Form.Item
          label="Node Name"
          name="label"
          rules={[{ required: true, message: 'Please enter node name.' }]}
        >
          <Input placeholder="Enter display name for this node" />
        </Form.Item>

        {/* Content nodes (input-node, output-node) */}
        {isContentNode && (
          <Form.Item
            label="Content"
            name="content"
            rules={[{ required: true, message: 'Please enter content.' }]}
          >
            <TextArea
              rows={4}
              placeholder={
                node.data.nodeType === NodeType.INPUT
                  ? "Enter input text to pass to the next node"
                  : "Enter output result description"
              }
            />
          </Form.Item>
        )}

        {/* LLM nodes (generation-node, ensemble-node, validation-node) */}
        {isLLMNode && (
          <>
            <Form.Item
              label="LLM Provider"
              name="llm_provider"
              rules={[{ required: true, message: 'Please select LLM Provider.' }]}
            >
              <Select
                placeholder="Select Provider"
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
                  <span>Model</span>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => {
                      const provider = form.getFieldValue('llm_provider') || LLMProvider.GOOGLE;
                      loadAvailableModels(provider);
                      message.info('Model list refreshed.');
                    }}
                    style={{ padding: 0, fontSize: '12px' }}
                  >
                    Refresh
                  </Button>
                </div>
              }
              name="model_type"
              rules={[{ required: true, message: 'Please select a model.' }]}
            >
              <Select
                placeholder="Select Model"
                loading={availableModels.length === 0}
                showSearch
                filterOption={(input, option) =>
                  String(option?.children ?? '').toLowerCase().includes(input.toLowerCase())
                }
                onChange={(value) => {
                  console.log('Model selection changed:', value);
                  // Explicitly handle model change
                  form.setFieldValue('model_type', value);
                  // Verify value was set correctly
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

            <Divider>Output Format & Prompt</Divider>

            <Form.Item
              label={
                <span>
                  Output Format
                  <Tooltip title="Define the format for key results that the LLM will output. Content in this format will be passed to the next node.">
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
                        message.success('Default output format applied.');
                      }
                    }}
                  >
                    Default Template
                  </Button>
                  <Button
                    size="small"
                    onClick={() => form.setFieldValue('output_format', '{\n  "requirements": [\n    {\n      "id": "REQ-001",\n      "requirement": "[Specific requirement content]",\n      "reference": "[Original text and location]"\n    }\n  ]\n}')}
                  >
                    JSON Example
                  </Button>
                  <Button
                    size="small"
                    onClick={() => form.setFieldValue('output_format', '| ID | Requirement | Reference |\n|---|---|---|\n| REQ-001 | [Specific requirement content] | [Original text and location] |\n| REQ-002 | ... | ... |')}
                  >
                    Markdown Table Example
                  </Button>
                </div>
                <Form.Item name="output_format" noStyle>
                  <TextArea
                    rows={4}
                    placeholder="Enter the output format for key results."
                    style={{ fontFamily: 'Consolas, "Courier New", monospace' }}
                  />
                </Form.Item>
              </div>
            </Form.Item>

            <Form.Item
              label={
                <span>
                  Prompt
                  <Tooltip title="Enter the prompt to send to the LLM.">
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
                        message.success('Default prompt applied.');
                      }
                    }}
                  >
                    Use Default Template
                  </Button>
                </div>

                <Form.Item name="prompt" noStyle>
                  <TextArea
                    rows={8}
                    placeholder="Enter prompt."
                    style={{ fontFamily: 'Consolas, "Courier New", monospace' }}
                  />
                </Form.Item>

                <Divider style={{ margin: '12px 0' }} />

                <div style={{ fontSize: 12, color: UI_COLORS.TEXT.SECONDARY }}>
                  <div style={{ fontWeight: 'bold', marginBottom: 4 }}>Available Variables:</div>
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

        {/* Context node (context-node) */}
        {isContextNode && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontWeight: 500 }}>Knowledge Base</span>
              <Button
                type="default"
                size="small"
                icon={<SettingOutlined />}
                onClick={() => setKbManageModalVisible(true)}
              >
                Manage List
              </Button>
            </div>

            <Form.Item
              name="knowledge_base"
              tooltip="Select a knowledge base for search. Select 'None' to use only additional content."
            >
              <Select
                placeholder="Select Knowledge Base"
                showSearch
                optionFilterProp="children"
                filterOption={(input, option) => {
                  const label = option?.children?.[0]?.props?.children || '';
                  return label.toLowerCase().includes(input.toLowerCase());
                }}
              >
                <Option value="none">
                  <Text type="secondary">None</Text>
                </Option>
                {knowledgeBases.map((kb: KnowledgeBase) => (
                  <Option key={kb.name} value={kb.name} title={kb.name}>
                    <Text>{kb.name}</Text>
                    <Text type="secondary" style={{ fontSize: '11px', marginLeft: '8px' }}>
                      ({kb.chunk_count} chunks)
                    </Text>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="Search Intensity"
              name="search_intensity"
              rules={[{ required: true, message: 'Please select search intensity.' }]}
              tooltip="Select document search intensity."
            >
              <Select>
                <Option value={SearchIntensity.EXACT}>
                  🎯 Exact (Search as precisely as possible)
                </Option>
                <Option value={SearchIntensity.STANDARD}>
                  ⚖️ Standard (Balanced search)
                </Option>
                <Option value={SearchIntensity.COMPREHENSIVE}>
                  🔬 Comprehensive (Broad context search)
                </Option>
              </Select>
            </Form.Item>

            <Form.Item
              label="Use Reranking"
              name="rerank_provider"
              tooltip="Rerank searched chunks by relevance to query using LLM-based reranking model (BAAI/bge-reranker-v2-m3). Use this to improve search accuracy."
            >
              <Select placeholder="Select reranking option">
                <Option value={LLMProvider.NONE}>Disabled</Option>
                <Option value="enabled">Enabled (BAAI/bge-reranker-v2-m3)</Option>
              </Select>
            </Form.Item>

            <Divider style={{ margin: '16px 0' }} />

            <Form.Item
              label={
                <span>
                  Additional Content
                  <Tooltip title="Enter custom context to include in addition to knowledge base search results. You can also use only this content without selecting a knowledge base.">
                    <InfoCircleOutlined style={{ marginLeft: 4, color: UI_COLORS.UI.INFO }} />
                  </Tooltip>
                </span>
              }
              name="additional_context"
            >
              <TextArea
                rows={6}
                placeholder="Enter additional context to include. (Optional)"
                style={{ fontFamily: 'Consolas, "Courier New", monospace' }}
              />
            </Form.Item>
          </>
        )}
      </Form>

      {/* Knowledge Base Management Modal */}
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
