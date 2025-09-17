import React, { useEffect } from 'react';
import { 
  Card, 
  Button, 
  Select, 
  Space, 
  Typography, 
  Alert, 
  Modal, 
  message,
  Divider,
  Row,
  Col
} from 'antd';
import { PlusOutlined, PlayCircleOutlined, WarningOutlined } from '@ant-design/icons';
import { useNodeWorkflowStore } from '../store/nodeWorkflowStore';
import {
  NodeType,
  SearchIntensity
} from '../types';

const { Title, Text } = Typography;
const { Option } = Select;

const NodeWorkflowControlPanel: React.FC = () => {


  
  const {
    nodes,
    edges,
    selectedKnowledgeBase,
    searchIntensity,
    isExecuting,
    validationErrors,
    knowledgeBases,
    
    addNode,
    setSelectedKnowledgeBase,
    setSearchIntensity,
    validateWorkflow,
    getValidationErrors,
    executeWorkflowStream,
    loadKnowledgeBases
  } = useNodeWorkflowStore();

  // 컴포넌트 마운트 시 지식 베이스 로드
  useEffect(() => {
    loadKnowledgeBases();
  }, [loadKnowledgeBases]);

  // 노드 추가 핸들러
  const handleAddNode = (nodeType: NodeType) => {
    try {
      // 랜덤 위치에 노드 생성
      const position = {
        x: Math.random() * 400 + 100,
        y: Math.random() * 300 + 100
      };
      addNode(nodeType, position);
      message.success(`${nodeType} 노드가 추가되었습니다.`);
    } catch (error: any) {
      message.error(error.message);
    }
  };

  // 워크플로우 실행 핸들러 (스트리밍)
  const handleExecuteWorkflow = async () => {
    // 실행 전 검증
    const isValid = validateWorkflow();
    if (!isValid) {
      const errors = getValidationErrors();
      
      Modal.error({
        title: '워크플로우 검증 실패',
        content: (
          <div>
            <p>워크플로우가 project_reference.md의 연결 조건을 만족하지 않습니다:</p>
            <ul>
              {errors.map((error, index) => (
                <li key={index} style={{ color: '#ff4d4f', marginBottom: '4px' }}>
                  {error}
                </li>
              ))}
            </ul>
            <p style={{ marginTop: '12px', color: '#666' }}>
              연결 조건을 수정한 후 다시 시도해주세요.
            </p>
          </div>
        ),
        okText: '확인',
        width: 600,
      });
      
      return;
    }

    if (!selectedKnowledgeBase) {
      message.warning('지식 베이스를 선택하지 않고 실행합니다. 컨텍스트 검색 없이 워크플로우가 실행됩니다.');
    }

    try {
      // 초기화
      
      message.loading('스트리밍 워크플로우 실행 중...', 0);
      
      let completedNodes = 0;
      
      await executeWorkflowStream((data) => {
        switch (data.type) {
          case 'start':
            message.destroy();
            message.info('워크플로우 실행 시작');
            break;
            
          case 'node_start':
            // 노드 시작은 store에서 처리됨
            break;
            
          case 'stream':
            // 스트리밍은 store에서 처리됨
            break;
            
          case 'node_complete':
            if (data.success) {
              completedNodes++;
              // Progress는 store에서 관리됨
            }
            break;
            
          case 'complete':
            message.destroy();
            message.success(`워크플로우 실행 완료! (${(data.total_execution_time || 0).toFixed(2)}초)`);
            // 완료 상태는 store에서 관리됨
            break;
            
          case 'error':
            message.destroy();
            message.error(`실행 오류: ${data.message}`);
            break;
        }
      });
      
    } catch (error: any) {
      message.destroy();
      message.error(`워크플로우 실행 실패: ${error.message}`);
    }
  };

  // 실행 가능 여부 확인 (지식베이스 선택과 무관)
  const canExecute = () => {
    return !isExecuting && 
           nodes.length > 0 && 
           edges.length > 0;
  };

  return (
    <div style={{ padding: '16px' }}>
      <Card size="small">
        <Title level={4} style={{ margin: 0, marginBottom: 16 }}>
          노드 기반 워크플로우 제어판
        </Title>

        {/* 검증 에러 표시 */}
        {validationErrors.length > 0 && (
          <Alert
            message="워크플로우 검증 오류"
            description={
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {validationErrors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            }
            type="error"
            icon={<WarningOutlined />}
            style={{ marginBottom: 16 }}
            showIcon
          />
        )}

        {/* 실행 설정 */}
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong>지식 베이스:</Text>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              placeholder="지식 베이스를 선택하세요 (선택사항)"
              value={selectedKnowledgeBase}
              onChange={setSelectedKnowledgeBase}
              allowClear
            >
              {knowledgeBases.map(kb => (
                <Option key={kb.name} value={kb.name}>
                  {kb.name} {kb.chunk_count ? `(${kb.chunk_count} chunks)` : ''}
                </Option>
              ))}
            </Select>
          </div>

          <div>
            <Text strong>검색 강도:</Text>
            <Select
              style={{ width: '100%', marginTop: 4 }}
              value={searchIntensity}
              onChange={setSearchIntensity}
            >
              <Option value={SearchIntensity.LOW}>낮음 (빠른 실행)</Option>
              <Option value={SearchIntensity.MEDIUM}>보통 (균형)</Option>
              <Option value={SearchIntensity.HIGH}>높음 (정확도 우선)</Option>
            </Select>
          </div>

          <Divider style={{ margin: '12px 0' }} />

          {/* 노드 추가 버튼들 */}
          <div>
            <Text strong>노드 추가:</Text>
            <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
              <Col span={12}>
                <Button 
                  size="small" 
                  block
                  icon={<PlusOutlined />}
                  onClick={() => handleAddNode(NodeType.INPUT)}
                >
                  Input 노드
                </Button>
              </Col>
              <Col span={12}>
                <Button 
                  size="small" 
                  block
                  icon={<PlusOutlined />}
                  onClick={() => handleAddNode(NodeType.GENERATION)}
                >
                  Generation 노드
                </Button>
              </Col>
              <Col span={12}>
                <Button 
                  size="small" 
                  block
                  icon={<PlusOutlined />}
                  onClick={() => handleAddNode(NodeType.ENSEMBLE)}
                >
                  Ensemble 노드
                </Button>
              </Col>
              <Col span={12}>
                <Button 
                  size="small" 
                  block
                  icon={<PlusOutlined />}
                  onClick={() => handleAddNode(NodeType.VALIDATION)}
                >
                  Validation 노드
                </Button>
              </Col>
              {/* Output 노드는 추가 버튼을 숨김 - project_reference.md 규칙 */}
              {nodes.filter(node => node.data.nodeType === NodeType.OUTPUT).length === 0 && (
                <Col span={24}>
                  <Button 
                    size="small" 
                    block
                    icon={<PlusOutlined />}
                    onClick={() => handleAddNode(NodeType.OUTPUT)}
                  >
                    Output 노드
                  </Button>
                </Col>
              )}
            </Row>
          </div>

          <Divider style={{ margin: '12px 0' }} />

          {/* 실행 버튼 */}
          <Button
            type="primary"
            size="large"
            block
            icon={<PlayCircleOutlined />}
            loading={isExecuting}
            disabled={!canExecute()}
            onClick={handleExecuteWorkflow}
          >
            워크플로우 실행
          </Button>




        </Space>
      </Card>
    </div>
  );
};

export { NodeWorkflowControlPanel };