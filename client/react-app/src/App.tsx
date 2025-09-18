import { Layout, Typography } from 'antd';
import { NodeWorkflowControlPanel } from './components/NodeWorkflowControlPanel';
import { NodeWorkflowCanvas } from './components/NodeWorkflowCanvas';
import { NodeExecutionResultPanel } from './components/NodeExecutionResultPanel';

const { Header, Content, Sider } = Layout;
const { Title } = Typography;

function App() {
  return (
    <Layout style={{ height: '100vh' }}>
      <Header style={{ 
        background: '#fff', 
        borderBottom: '1px solid #e8e8e8',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center'
      }}>
        <Title level={3} style={{ margin: 0, color: '#1890ff' }}>
          Multi Model Generator
        </Title>
      </Header>
      
      <Layout>
        <Sider 
          width={350} 
          style={{ 
            background: '#fff', 
            borderRight: '1px solid #e8e8e8',
            overflow: 'auto',
            padding: '16px'
          }}
        >
          <Title level={5} style={{ marginBottom: '16px', color: '#333' }}>실행 설정</Title>
          <NodeWorkflowControlPanel />
        </Sider>
        
        <Content style={{ 
          background: '#f0f2f5',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <Title level={5} style={{ marginBottom: '16px', color: '#333' }}>워크플로우 구성</Title>
          <div style={{ flex: 1 }}>
            <NodeWorkflowCanvas />
          </div>
        </Content>
        
        <Sider 
          width={800} 
          style={{ 
            background: '#f9f9f9', 
            borderLeft: '1px solid #e8e8e8',
            overflow: 'auto'
          }}
        >
          <NodeExecutionResultPanel />
        </Sider>
      </Layout>
    </Layout>
  );
}

export default App;