import React, { useState, useEffect } from 'react';
import { Card, Select, Input, Typography, Space, Tag } from 'antd';
import { useWorkflowStore } from '../store/workflowStore';
import { KnowledgeBase, SearchIntensity, LLMProvider } from '../types';
import { api } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const ControlPanel: React.FC = () => {
  const {
    selectedKnowledgeBase,
    keyword,
    searchIntensity,
    selectedProvider,
    setSelectedKnowledgeBase,
    setKeyword,
    setSearchIntensity,
    setSelectedProvider
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
      console.error('지식 베이스 목록을 가져올 수 없습니다:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="실행 설정" size="small">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {/* 지식 베이스 + 키워드 */}
        <div>
          <div style={{ marginBottom: 8 }}>
            <Title level={5} style={{ marginBottom: 6, fontSize: '13px' }}>지식 베이스</Title>
            <Select
              style={{ width: '100%' }}
              placeholder="지식 베이스를 선택하세요"
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

          {/* 검색 강도 설정 */}
          <div style={{ marginBottom: 8 }}>
            <Title level={5} style={{ marginBottom: 6, fontSize: '13px' }}>
              검색 강도 
            </Title>
            <Select
              style={{ width: '100%' }}
              value={searchIntensity}
              onChange={setSearchIntensity}
              size="small"
            >
              <Option value={SearchIntensity.LOW}>
                <Space>
                  <Tag color="green" style={{ margin: 0 }}>약</Tag>
                  빠른 검색 (5-15개 문서)
                </Space>
              </Option>
              <Option value={SearchIntensity.MEDIUM}>
                <Space>
                  <Tag color="orange" style={{ margin: 0 }}>중</Tag>
                  균형잡힌 검색 (15-25개 청크)
                </Space>
              </Option>
              <Option value={SearchIntensity.HIGH}>
                <Space>
                  <Tag color="red" style={{ margin: 0 }}>강</Tag>
                  철저한 검색 (25~35개 청크)
                </Space>
              </Option>
            </Select>
          </div>

          {/* LLM Provider 선택 */}
          <div style={{ marginBottom: 8 }}>
            <Title level={5} style={{ marginBottom: 6, fontSize: '13px' }}>
              LLM Provider
            </Title>
            <Select
              style={{ width: '100%' }}
              placeholder="LLM Provider를 선택하세요"
              value={selectedProvider}
              onChange={setSelectedProvider}
              size="small"
              allowClear
            >
              <Option value={LLMProvider.PERPLEXITY}>
                <Space>
                  <Tag color="purple" style={{ margin: 0 }}>Perplexity</Tag>
                </Space>
              </Option>
              <Option value={LLMProvider.OPENAI}>
                <Space>
                  <Tag color="blue" style={{ margin: 0 }}>OpenAI</Tag>
                </Space>
              </Option>
              <Option value={LLMProvider.GOOGLE}>
                <Space>
                  <Tag color="orange" style={{ margin: 0 }}>Google AI</Tag>
                </Space>
              </Option>
            </Select>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default ControlPanel;
