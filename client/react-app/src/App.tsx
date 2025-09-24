import { Layout, Typography } from 'antd';
import { useEffect } from 'react';
import { NodeExecutionResultPanel } from './components/NodeExecutionResultPanel';
import { NodeWorkflowCanvas } from './components/NodeWorkflowCanvas';
import { useNodeWorkflowStore } from './store/nodeWorkflowStore';
import './App.css';

const { Header, Content, Sider } = Layout;
const { Title } = Typography;

function App() {
  useEffect(() => {
    const store = useNodeWorkflowStore.getState();
    // 지식베이스만 미리 로드하고, 모델은 필요할 때 로드
    store.loadKnowledgeBases();
  }, []);

  return (
    <Layout style={{ height: '100vh', width: '100vw', overflow: 'hidden' }}>
      <Header style={{ 
        background: '#fff', 
        padding: '0 24px', 
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        height: '64px',
        minHeight: '64px',
        zIndex: 10
      }}>
        <Title level={4} style={{ margin: 0 }}>Multi-Model Generator</Title>
      </Header>
      <Layout style={{ height: 'calc(100vh - 64px)', width: '100%' }}>
        <Content style={{ 
          background: '#f0f2f5',
          padding: '0',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          width: '50%',
          flex: '1 1 50%'
        }}>
          <div style={{ flex: 1, position: 'relative', height: '100%', width: '100%' }}>
            <NodeWorkflowCanvas />
          </div>
        </Content>
        
        <Sider 
          width="50%" 
          style={{ 
            background: '#f9f9f9', 
            borderLeft: '1px solid #e8e8e8',
            height: '100%',
            overflowY: 'auto',
            flex: '1 1 50%',
            maxWidth: '50%',
            minWidth: '50%'
          }}
        >
          <NodeExecutionResultPanel />
        </Sider>
      </Layout>
    </Layout>
  );
}

export default App;