import { Layout, Typography } from 'antd';
import { NodeWorkflowControlPanel } from './components/NodeWorkflowControlPanel';
import { NodeWorkflowCanvas } from './components/NodeWorkflowCanvas';

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
          MultiModelGenerator - 노드 기반 워크플로우
        </Title>
      </Header>
      
      <Layout>
        <Sider 
          width={350} 
          style={{ 
            background: '#fff', 
            borderRight: '1px solid #e8e8e8',
            overflow: 'auto'
          }}
        >
          <NodeWorkflowControlPanel />
        </Sider>
        
        <Content style={{ 
          background: '#fff',
          padding: '16px'
        }}>
          <NodeWorkflowCanvas />
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;