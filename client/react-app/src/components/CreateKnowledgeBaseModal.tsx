import React, { useState } from 'react';
import { Modal, Form, Input, Select, InputNumber, Upload, Button, Radio, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { workflowAPI } from '../services/api';

const { TextArea } = Input;

interface CreateKnowledgeBaseModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
  currentFolder?: string; // 현재 폴더 경로
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
  const [chunkType, setChunkType] = useState<'keyword' | 'sentence' | 'custom'>('sentence');
  const [chunkSize, setChunkSize] = useState<number>(8000);
  const [chunkOverlap, setChunkOverlap] = useState<number>(200);

  const handleFileChange = (info: any) => {
    const file = info.file.originFileObj || info.file;
    
    // 파일 타입 확인
    const isPDF = file.type === 'application/pdf' || file.name.endsWith('.pdf');
    const isTXT = file.type === 'text/plain' || file.name.endsWith('.txt');
    
    if (!isPDF && !isTXT) {
      message.error('PDF 또는 TXT 파일만 업로드 가능합니다.');
      return;
    }
    
    // 파일 타입 설정
    setFileType(isPDF ? 'pdf' : 'txt');

    const reader = new FileReader();
    reader.onload = (e) => {
      const base64 = (e.target?.result as string).split(',')[1];
      setFileBase64(base64);
      message.success(`파일이 업로드되었습니다: ${file.name}`);
    };
    reader.onerror = () => {
      message.error('파일 읽기에 실패했습니다.');
    };
    reader.readAsDataURL(file);
  };

  const handleChunkTypeChange = (value: 'keyword' | 'sentence' | 'custom') => {
    setChunkType(value);
    if (value === 'keyword') {
      setChunkSize(1000);
      setChunkOverlap(100);
    } else if (value === 'sentence') {
      setChunkSize(8000);
      setChunkOverlap(200);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      let contentBase64 = '';
      
      if (inputMode === 'file') {
        if (!fileBase64) {
          message.error('파일을 선택해주세요.');
          return;
        }
        contentBase64 = fileBase64;
      } else {
        if (!textContent.trim()) {
          message.error('텍스트 내용을 입력해주세요.');
          return;
        }
        
        if (inputMode === 'base64') {
          // base64 텍스트는 그대로 전송
          contentBase64 = textContent;
        } else {
          // plain text도 그대로 전송
          contentBase64 = textContent;
        }
      }

      setLoading(true);

      await workflowAPI.createKnowledgeBase(
        values.kb_name,
        chunkType,
        contentBase64,
        inputMode,
        inputMode === 'file' ? fileType : undefined,
        chunkType === 'custom' ? chunkSize : undefined,
        chunkType === 'custom' ? chunkOverlap : undefined,
        currentFolder || undefined
      );

      message.success('지식 베이스가 성공적으로 생성되었습니다.');
      form.resetFields();
      setTextContent('');
      setFileBase64('');
      setInputMode('base64');
      setFileType('pdf');
      setChunkType('sentence');
      setChunkSize(8000);
      setChunkOverlap(200);
      onSuccess();
      onClose();
    } catch (error: any) {
      console.error('KB creation error:', error);
      message.error(error.response?.data?.detail || '지식 베이스 생성에 실패했습니다.');
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
    setChunkType('sentence');
    setChunkSize(8000);
    setChunkOverlap(200);
    onClose();
  };

  return (
    <Modal
      title="지식 베이스 추가"
      open={visible}
      onOk={handleSubmit}
      onCancel={handleCancel}
      confirmLoading={loading}
      width={600}
      okText="생성"
      cancelText="취소"
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          chunk_type: 'sentence',
          chunk_size: 8000,
          chunk_overlap: 200
        }}
      >
        <Form.Item
          label="지식 베이스 이름"
          name="kb_name"
          rules={[{ required: true, message: '지식 베이스 이름을 입력해주세요.' }]}
          extra={`생성될 이름: ${chunkType}_[입력한 이름]`}
        >
          <Input placeholder="예: nvme_spec" />
        </Form.Item>

        <Form.Item
          label="청킹 타입"
        >
          <Select value={chunkType} onChange={handleChunkTypeChange}>
            <Select.Option value="keyword">Keyword (1000자, 100 오버랩)</Select.Option>
            <Select.Option value="sentence">Sentence (8000자, 200 오버랩)</Select.Option>
            <Select.Option value="custom">Custom (사용자 지정)</Select.Option>
          </Select>
        </Form.Item>

        {chunkType === 'custom' && (
          <>
            <Form.Item label="Chunk Size">
              <InputNumber
                min={100}
                max={20000}
                value={chunkSize}
                onChange={(value) => setChunkSize(value || 8000)}
                style={{ width: '100%' }}
              />
            </Form.Item>
            <Form.Item label="Chunk Overlap">
              <InputNumber
                min={0}
                max={1000}
                value={chunkOverlap}
                onChange={(value) => setChunkOverlap(value || 200)}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </>
        )}

        <Form.Item label="입력 방식">
          <Radio.Group value={inputMode} onChange={(e) => setInputMode(e.target.value)}>
            <Radio.Button value="base64">Base64 Text</Radio.Button>
            <Radio.Button value="plain">Plain Text</Radio.Button>
            <Radio.Button value="file">파일 업로드 (PDF/TXT)</Radio.Button>
          </Radio.Group>
        </Form.Item>

        {inputMode === 'base64' ? (
          <Form.Item
            label="Base64 인코딩된 텍스트"
            extra="base64로 인코딩된 텍스트를 붙여넣으세요."
          >
            <TextArea
              rows={10}
              placeholder="base64 인코딩된 텍스트를 입력하세요..."
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              style={{ fontFamily: 'monospace', fontSize: '12px' }}
            />
          </Form.Item>
        ) : inputMode === 'plain' ? (
          <Form.Item
            label="텍스트 내용"
            extra="일반 텍스트를 입력하세요."
          >
            <TextArea
              rows={10}
              placeholder="임베딩할 텍스트를 입력하세요..."
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              style={{ fontFamily: 'monospace', fontSize: '12px' }}
            />
          </Form.Item>
        ) : (
          <Form.Item
            label="파일 업로드"
            extra="PDF 또는 TXT 파일을 선택하세요. 자동으로 텍스트가 추출됩니다."
          >
            <Upload
              accept=".pdf,.txt"
              maxCount={1}
              beforeUpload={() => false}
              onChange={handleFileChange}
            >
              <Button icon={<UploadOutlined />}>파일 선택 (PDF/TXT)</Button>
            </Upload>
          </Form.Item>
        )}

        <div style={{ fontSize: '12px', color: '#888', marginTop: '8px' }}>
          <p style={{ margin: '4px 0' }}>※ prefix는 자동으로 추가됩니다 (keyword_, sentence_, custom_)</p>
          <p style={{ margin: '4px 0' }}>※ 입력한 내용은 자동으로 청킹되어 VectorDB에 저장됩니다.</p>
          {(inputMode === 'plain' || inputMode === 'base64') && <p style={{ margin: '4px 0' }}>※ 텍스트 길이: {textContent.length} 문자</p>}
          {inputMode === 'file' && fileBase64 && <p style={{ margin: '4px 0' }}>※ {fileType.toUpperCase()} 파일이 선택되었습니다.</p>}
          {currentFolder && <p style={{ margin: '4px 0' }}>※ 생성 위치: /{currentFolder}</p>}
        </div>
      </Form>
    </Modal>
  );
};

export default CreateKnowledgeBaseModal;
