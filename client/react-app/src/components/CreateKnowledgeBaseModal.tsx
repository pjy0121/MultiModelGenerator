import React, { useState } from 'react';
import { Modal, Form, Input, Upload, Button, Radio, message } from 'antd';
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
  const textContentRef = React.useRef<HTMLTextAreaElement>(null);
  const [fileBase64, setFileBase64] = useState<string>('');
  const [fileType, setFileType] = useState<'pdf' | 'txt'>('pdf');
  
  // BGE-M3 최적화 고정 설정 (512 tokens, 15% overlap)
  const CHUNK_SIZE = 2048;  // 512 tokens * 4 characters/token
  const CHUNK_OVERLAP = 307; // 15% overlap

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
        const textContent = textContentRef.current?.value || '';
        if (!textContent.trim()) {
          message.error('텍스트 내용을 입력해주세요.');
          return;
        }
        
        contentBase64 = textContent;
      }

      setLoading(true);

      await workflowAPI.createKnowledgeBase(
        values.kb_name,
        'bge-m3',  // BGE-M3 최적화 모드 (하위 호환성용, 백엔드에서 무시됨)
        contentBase64,
        inputMode,
        inputMode === 'file' ? fileType : undefined,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
        currentFolder || undefined
      );

      message.success(`지식 베이스 '${values.kb_name}'가 성공적으로 생성되었습니다.`);
      form.resetFields();
      if (textContentRef.current) textContentRef.current.value = '';
      setFileBase64('');
      setInputMode('base64');
      setFileType('pdf');
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
    if (textContentRef.current) textContentRef.current.value = '';
    setFileBase64('');
    setInputMode('base64');
    setFileType('pdf');
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
      zIndex={2000}
    >
      <Form
        form={form}
        layout="vertical"
      >
        <Form.Item
          label="지식 베이스 이름"
          name="kb_name"
          rules={[{ required: true, message: '지식 베이스 이름을 입력해주세요.' }]}
          extra="BGE-M3 최적화 설정 (512 tokens, 15% overlap) 자동 적용"
        >
          <Input placeholder="예: nvme_spec_2.2" />
        </Form.Item>

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
          >
            <TextArea
              ref={textContentRef}
              rows={10}
              placeholder="base64 인코딩된 텍스트를 입력하세요..."
              style={{ fontFamily: 'monospace', fontSize: '12px' }}
            />
          </Form.Item>
        ) : inputMode === 'plain' ? (
          <Form.Item
            label="텍스트 내용"
          >
            <TextArea
              ref={textContentRef}
              rows={10}
              placeholder="임베딩할 텍스트를 입력하세요..."
              style={{ fontFamily: 'monospace', fontSize: '12px' }}
            />
          </Form.Item>
        ) : (
          <Form.Item
            label="파일 업로드"
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
          {inputMode === 'file' && fileBase64 && <p style={{ margin: '4px 0' }}>※ {fileType.toUpperCase()} 파일이 선택되었습니다.</p>}
          {currentFolder && <p style={{ margin: '4px 0' }}>※ 생성 위치: /{currentFolder}</p>}
        </div>
      </Form>
    </Modal>
  );
};

export default CreateKnowledgeBaseModal;
