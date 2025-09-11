import React from 'react';
import { Layout, Typography, Row, Col } from 'antd';
import ControlPanel from './components/ControlPanel';
import ResultPanel from './components/ResultPanel';
import '@xyflow/react/dist/style.css';
import 'antd/dist/reset.css';

const { Header, Content } = Layout;
const { Title } = Typography;

const App: React.FC = () => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#001529', padding: '0 24px' }}>
        <Title level={3} style={{ color: 'white', margin: '16px 0' }}>
          🔬 Requirements Generation Workflow
        </Title>
      </Header>
      
      <Content style={{ padding: '24px', backgroundColor: '#f0f2f5' }}>
        <Row gutter={[16, 0]} style={{ height: 'calc(100vh - 112px)' }}>
          {/* 실행 제어 - 좌측 */}
          <Col span={10} style={{ height: '100%' }}>
            <div style={{ 
              height: '100%', 
              overflowY: 'auto',
              paddingRight: '8px'
            }}>
              <ControlPanel />
            </div>
          </Col>
          
          {/* 실행 결과 - 우측 */}
          <Col span={14} style={{ height: '100%' }}>
            <div style={{ 
              height: '100%', 
              overflowY: 'auto',
              paddingLeft: '8px'
            }}>
              <ResultPanel />
            </div>
          </Col>
        </Row>
      </Content>
    </Layout>
  );
};

export default App;
