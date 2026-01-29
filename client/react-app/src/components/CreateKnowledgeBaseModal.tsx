import React, { useState } from 'react';
import { Modal, Form, Input, Upload, Button, Radio, message, InputNumber } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { workflowAPI } from '../services/api';
import { BGE_M3_CONFIG } from '../config/constants';

const { TextArea } = Input;

interface CreateKnowledgeBaseModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
  currentFolder?: string; // Current folder path
}

const CreateKnowledgeBaseModal: React.FC<CreateKnowledgeBaseModalProps> = ({
  visible,
  onClose,
  onSuccess,
  currentFolder = ''
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [inputMode, setInputMode] = useState<'base64' | 'plain' | 'file'>('base64');
  const [textContent, setTextContent] = useState<string>('');
  const [fileBase64, setFileBase64] = useState<string>('');
  const [fileType, setFileType] = useState<'pdf' | 'txt'>('pdf');
  const [chunkTokens, setChunkTokens] = useState<number>(BGE_M3_CONFIG.CHUNK_TOKENS);
  const [overlapRatio, setOverlapRatio] = useState<number>(BGE_M3_CONFIG.OVERLAP_RATIO);

  const handleFileChange = (info: any) => {
    const file = info.file.originFileObj || info.file;

    // Check file type
    const isPDF = file.type === 'application/pdf' || file.name.endsWith('.pdf');
    const isTXT = file.type === 'text/plain' || file.name.endsWith('.txt');

    if (!isPDF && !isTXT) {
      message.error('Only PDF or TXT files can be uploaded.');
      return;
    }

    // Set file type
    setFileType(isPDF ? 'pdf' : 'txt');

    const reader = new FileReader();
    reader.onload = (e) => {
      const base64 = (e.target?.result as string).split(',')[1];
      setFileBase64(base64);
      message.success(`File uploaded: ${file.name}`);
    };
    reader.onerror = () => {
      message.error('Failed to read file.');
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      let contentBase64 = '';

      if (inputMode === 'file') {
        if (!fileBase64) {
          message.error('Please select a file.');
          return;
        }
        contentBase64 = fileBase64;
      } else {
        if (!textContent.trim()) {
          message.error('Please enter text content.');
          return;
        }

        contentBase64 = textContent;
      }

      setLoading(true);

      // Calculate characters from token-based settings (using user settings)
      const chunkSize = chunkTokens * BGE_M3_CONFIG.CHARS_PER_TOKEN;
      const chunkOverlap = Math.floor(chunkSize * overlapRatio);

      await workflowAPI.createKnowledgeBase(
        values.kb_name,
        contentBase64,
        inputMode,
        inputMode === 'file' ? fileType : undefined,
        chunkSize,
        chunkOverlap,
        currentFolder || undefined
      );

      message.success(`Knowledge base '${values.kb_name}' created successfully.`);
      form.resetFields();
      setTextContent('');
      setFileBase64('');
      setInputMode('base64');
      setFileType('pdf');
      setChunkTokens(BGE_M3_CONFIG.CHUNK_TOKENS);
      setOverlapRatio(BGE_M3_CONFIG.OVERLAP_RATIO);
      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('KB creation error:', error);
      message.error(error.response?.data?.detail || 'Failed to create knowledge base.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setTextContent('');
    setFileBase64('');
    setInputMode('base64');
    setFileType('pdf');
    setChunkTokens(BGE_M3_CONFIG.CHUNK_TOKENS);
    setOverlapRatio(BGE_M3_CONFIG.OVERLAP_RATIO);
    onClose();
  };

  return (
    <Modal
      title="Add Knowledge Base"
      open={visible}
      onOk={handleSubmit}
      onCancel={handleCancel}
      confirmLoading={loading}
      width={600}
      okText="Create"
      cancelText="Cancel"
      zIndex={2000}
    >
      <Form
        form={form}
        layout="vertical"
      >
        <Form.Item
          label="Knowledge Base Name"
          name="kb_name"
          rules={[{ required: true, message: 'Please enter knowledge base name.' }]}
        >
          <Input placeholder="e.g., nvme_spec_2.2" />
        </Form.Item>

        <Form.Item label="Chunk Settings (BGE-M3 Optimized)">
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: '12px', color: '#666', display: 'block', marginBottom: '4px' }}>
                Chunk Size (tokens)
              </label>
              <Input
                type="number"
                min={128}
                max={8192}
                value={chunkTokens}
                onChange={(e) => setChunkTokens(Number(e.target.value))}
                placeholder="512"
                addonAfter="tokens"
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: '12px', color: '#666', display: 'block', marginBottom: '4px' }}>
                Overlap Ratio (%)
              </label>
              <Input
                type="number"
                min={0}
                max={50}
                step={5}
                value={Math.round(overlapRatio * 100)}
                onChange={(e) => setOverlapRatio(Number(e.target.value) / 100)}
                placeholder="15"
                addonAfter="%"
              />
            </div>
          </div>
          <div style={{ fontSize: '11px', color: '#999', marginTop: '4px' }}>
            Default: 512 tokens, 15% overlap (approx. {chunkTokens * BGE_M3_CONFIG.CHARS_PER_TOKEN} chars, {Math.round(chunkTokens * BGE_M3_CONFIG.CHARS_PER_TOKEN * overlapRatio)} chars overlap)
          </div>
        </Form.Item>

        <Form.Item label="Input Method">
          <Radio.Group value={inputMode} onChange={(e) => setInputMode(e.target.value)}>
            <Radio.Button value="base64">Base64 Text</Radio.Button>
            <Radio.Button value="plain">Plain Text</Radio.Button>
            <Radio.Button value="file">File Upload (PDF/TXT)</Radio.Button>
          </Radio.Group>
        </Form.Item>

        {inputMode === 'base64' ? (
          <Form.Item
            label="Base64 Encoded Text"
          >
            <TextArea
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              rows={10}
              placeholder="Enter base64 encoded text..."
              style={{ fontFamily: 'monospace', fontSize: '12px' }}
            />
          </Form.Item>
        ) : inputMode === 'plain' ? (
          <Form.Item
            label="Text Content"
          >
            <TextArea
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              rows={10}
              placeholder="Enter text to embed..."
              style={{ fontFamily: 'monospace', fontSize: '12px' }}
            />
          </Form.Item>
        ) : (
          <Form.Item
            label="File Upload"
          >
            <Upload
              accept=".pdf,.txt"
              maxCount={1}
              beforeUpload={() => false}
              onChange={handleFileChange}
            >
              <Button icon={<UploadOutlined />}>Select File (PDF/TXT)</Button>
            </Upload>
          </Form.Item>
        )}

        <div style={{ fontSize: '12px', color: '#888', marginTop: '8px' }}>
          {inputMode === 'file' && fileBase64 && <p style={{ margin: '4px 0' }}>* {fileType.toUpperCase()} file selected.</p>}
          {currentFolder && <p style={{ margin: '4px 0' }}>* Creation location: /{currentFolder}</p>}
        </div>
      </Form>
    </Modal>
  );
};

export default CreateKnowledgeBaseModal;
