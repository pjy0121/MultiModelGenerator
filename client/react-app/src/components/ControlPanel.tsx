import React, { useState, useEffect } from 'react';
import { Card, Select, Input, Button, Typography, Collapse, Space, message } from 'antd'; // ✅ message import 추가
import { PlayCircleOutlined, SettingOutlined } from '@ant-design/icons';
import CollapsibleWorkflowCanvas from './CollapsibleWorkflowCanvas';
import { useWorkflowStore } from '../store/workflowStore';
import { KnowledgeBase } from '../types';
import { api } from '../services/api';

const { Title } = Typography;
const { Option } = Select;
const { Panel } = Collapse;

const ControlPanel: React.FC = () => {
  const {
    selectedKnowledgeBase,
    keyword,
    isExecuting,
    setSelectedKnowledgeBase,
    setKeyword,
    setIsExecuting,
    setResult,
    nodes
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

  const handleExecute = async () => {
    // ✅ 검증 로직을 사용자에게 보이는 팝업으로 변경
    if (!selectedKnowledgeBase) {
      message.warning('지식베이스를 선택해주세요.');
      return;
    }
    
    if (!keyword.trim()) {
      message.warning('키워드를 입력해주세요.');
      return;
    }

    try {
      setIsExecuting(true);
      
      // 타입 안전한 노드 필터링 및 매핑
      const generationNodes = nodes
        .filter(n => n.type === 'customNode' && (n as any).data.layer === 'generation')
        .map(n => ({
          id: n.id,
          model_type: (n as any).data.model_type,
          prompt: (n as any).data.prompt,
          layer: (n as any).data.layer,
          position: n.position
        }));

      // 앙상블 노드 안전하게 찾기
      const ensembleNodeArray = nodes.filter(n => n.type === 'customNode' && (n as any).data.layer === 'ensemble');
      const ensembleNode = ensembleNodeArray.length > 0 ? {
        id: ensembleNodeArray[0].id,
        model_type: (ensembleNodeArray[0] as any).data.model_type,
        prompt: (ensembleNodeArray[0] as any).data.prompt,
        layer: (ensembleNodeArray[0] as any).data.layer,
        position: ensembleNodeArray[0].position
      } : null;

      const validationNodes = nodes
        .filter(n => n.type === 'customNode' && (n as any).data.layer === 'validation')
        .map(n => ({
          id: n.id,
          model_type: (n as any).data.model_type,
          prompt: (n as any).data.prompt,
          layer: (n as any).data.layer,
          position: n.position
        }));

      // 워크플로우 설정 구성
      const workflowConfig = {
        generation_nodes: generationNodes,
        ensemble_node: ensembleNode,
        validation_nodes: validationNodes
      };

      const response = await api.post('/execute-workflow', {
        knowledge_base: selectedKnowledgeBase,
        keyword: keyword.trim(),
        workflow_config: workflowConfig
      });

      setResult(response.data);
      message.success('워크플로우가 성공적으로 실행되었습니다!'); // ✅ 성공 메시지도 팝업으로
      console.log('워크플로우가 성공적으로 실행되었습니다!');
    } catch (error: any) {
      console.error('워크플로우 실행 중 오류가 발생했습니다:', error.response?.data?.detail);
      message.error('워크플로우 실행 중 오류가 발생했습니다.'); // ✅ 에러 메시지도 팝업으로
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <Card title="실행 설정" size="small" style={{ height: '100%' }}>
      <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100% - 40px)' }}>
        {/* 지식베이스 + 키워드 */}
        <div style={{ flexShrink: 0, marginBottom: '16px' }}>
          <div style={{ marginBottom: 12 }}>
            <Title level={5} style={{ marginBottom: 8, fontSize: '14px' }}>지식베이스</Title>
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

          <div style={{ marginBottom: 12 }}>
            <Title level={5} style={{ marginBottom: 8, fontSize: '14px' }}>키워드</Title>
            <Input
              placeholder="요구사항을 추출할 키워드를 입력하세요"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={handleExecute}
              size="small"
            />
          </div>

          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleExecute}
            loading={isExecuting}
            block
            size="large"
          >
            {isExecuting ? '실행 중...' : '워크플로우 실행'}
          </Button>
        </div>

        {/* 워크플로우 구성 */}
        <div style={{ flex: 1, minHeight: 0 }}>
          <Collapse 
            size="small"
            defaultActiveKey={['1']}
            expandIconPosition="end"
            style={{ height: '100%' }}
          >
            <Panel 
              header={
                <Space>
                  <SettingOutlined />
                  <span>워크플로우 구성</span>
                </Space>
              } 
              key="1"
              style={{ height: '100%' }}
            >
              <div style={{ height: '500px' }}>
                <CollapsibleWorkflowCanvas />
              </div>
            </Panel>
          </Collapse>
        </div>
      </div>
    </Card>
  );
};

export default ControlPanel;
