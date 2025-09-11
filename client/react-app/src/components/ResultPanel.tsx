import React from 'react';
import { Card, Typography, Table, Tag, Spin } from 'antd';
import { useWorkflowStore } from '../store/workflowStore';

const { Title, Paragraph } = Typography;

const ResultPanel: React.FC = () => {
  const { result, isExecuting } = useWorkflowStore();

  const columns = [
    {
      title: '노드 ID',
      dataIndex: 'node_id',
      key: 'node_id',
    },
    {
      title: '모델 타입',
      dataIndex: 'model_type',
      key: 'model_type',
      render: (text: string) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '실행 시간',
      dataIndex: 'execution_time',
      key: 'execution_time',
      render: (time: number) => `${time.toFixed(2)}초`
    }
  ];

  if (isExecuting) {
    return (
      <Card title="실행 결과" style={{ height: '100%' }}>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
          <div style={{ marginTop: '16px' }}>워크플로우 실행 중...</div>
        </div>
      </Card>
    );
  }

  if (!result) {
    return (
      <Card title="실행 결과" style={{ height: '100%' }}>
        <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
          워크플로우를 실행하면 결과가 여기에 표시됩니다.
        </div>
      </Card>
    );
  }

  return (
    <Card title="실행 결과" style={{ height: '100%' }}>
      <div style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}>
        <div style={{ marginBottom: '16px' }}>
          <Title level={4}>최종 요구사항</Title>
          <div style={{ 
            background: '#f8f9fa', 
            padding: '16px', 
            borderRadius: '6px',
            border: '1px solid #e9ecef',
            maxHeight: '300px',
            overflow: 'auto'
          }}>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
              {result.final_requirements}
            </pre>
          </div>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <Title level={4}>노드별 실행 정보</Title>
          <Table 
            dataSource={result.node_outputs} 
            columns={columns}
            size="small"
            rowKey="node_id"
            pagination={false}
          />
        </div>

        <div>
          <Paragraph>
            <strong>총 실행 시간:</strong> {result.total_execution_time?.toFixed(2)}초
          </Paragraph>
          <Paragraph>
            <strong>생성 시간:</strong> {new Date(result.generated_at).toLocaleString()}
          </Paragraph>
        </div>
      </div>
    </Card>
  );
};

export default ResultPanel;
