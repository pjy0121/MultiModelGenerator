import React from 'react';
import { Layout, Typography, Row, Col } from 'antd';
import ControlPanel from './components/ControlPanel';
import { LayerWorkflowPanel } from './components/LayerWorkflowPanel';
import ExecutionResultPanel from './components/ExecutionResultPanel';
import '@xyflow/react/dist/style.css';
import 'antd/dist/reset.css';

const { Header, Content } = Layout;
const { Title } = Typography;

const App: React.FC = () => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#001529', padding: '0 24px' }}>
        <Title level={3} style={{ color: 'white', margin: '16px 0' }}>
          🔬 Multi Model Generator
        </Title>
      </Header>
      
      <Content style={{ padding: '16px', backgroundColor: '#f0f2f5' }}>
        <Row gutter={[16, 0]} style={{ height: 'calc(100vh - 112px)' }}>
          {/* 워크플로우 설정 및 실행 결과 - 좌측 */}
          <Col span={8} style={{ height: '100%' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
              {/* 실행 설정 - 필요한 크기만 차지 */}
              <div style={{ flexShrink: 0 }}>
                <ControlPanel />
              </div>
              {/* 실행 결과 영역 - 나머지 공간 모두 사용 */}
              <div style={{ flex: 1, minHeight: 0 }}>
                <ExecutionResultPanel />
              </div>
            </div>
          </Col>
          
          {/* Layer별 워크플로우 실행 - 우측 */}
          <Col span={16} style={{ height: '100%' }}>
            <LayerWorkflowPanel />
          </Col>
        </Row>
      </Content>
    </Layout>
  );
};

export default App;
