import React, { useState, useEffect } from 'react';
import { Card, Select, Input, Typography } from 'antd';
import { useWorkflowStore } from '../store/workflowStore';
import { KnowledgeBase } from '../types';
import { api } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const ControlPanel: React.FC = () => {
  const {
    selectedKnowledgeBase,
    keyword,
    setSelectedKnowledgeBase,
    setKeyword
  } = useWorkflowStore();

  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchKnowledgeBases();
  }, []);

  const fetchKnowledgeBases = async () => {
    try {
      setLoading(true);
      const response = await api.get('/knowledge-bases');
      setKnowledgeBases(response.data.knowledge_bases);
    } catch (error) {
      console.error('지식베이스 목록을 가져올 수 없습니다:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="실행 설정" size="small">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {/* 지식베이스 + 키워드 */}
        <div>
          <div style={{ marginBottom: 8 }}>
            <Title level={5} style={{ marginBottom: 6, fontSize: '13px' }}>지식베이스</Title>
            <Select
              style={{ width: '100%' }}
              placeholder="지식베이스를 선택하세요"
              value={selectedKnowledgeBase}
              onChange={setSelectedKnowledgeBase}
              loading={loading}
              size="small"
            >
              {knowledgeBases.map(kb => (
                <Option key={kb.name} value={kb.name}>
                  {kb.name} ({kb.chunk_count.toLocaleString()} 청크)
                </Option>
              ))}
            </Select>
          </div>

          <div style={{ marginBottom: 8 }}>
            <Title level={5} style={{ marginBottom: 6, fontSize: '13px' }}>키워드</Title>
            <Input
              placeholder="요구사항을 추출할 키워드를 입력하세요"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              size="small"
            />
          </div>
        </div>
      </div>
    </Card>
  );
};

export default ControlPanel;
