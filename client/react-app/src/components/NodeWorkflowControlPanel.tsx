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
  SearchIntensity,
  getSearchIntensityValue
} from '../types';

const { Title, Text } = Typography;
const { Option } = Select;

export const NodeWorkflowControlPanel: React.FC = () => {
  const {
    nodes,
    edges,
    selectedKnowledgeBase,
    searchIntensity,
    isExecuting,
    executionResult,
    validationErrors,
    knowledgeBases,
    
    addNode,
    setSelectedKnowledgeBase,
    setSearchIntensity,
    validateWorkflow,
    getValidationErrors,
    executeWorkflow,
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

  // 워크플로우 실행 핸들러
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
      message.loading('노드 기반 워크플로우 실행 중...', 0);
      const result = await executeWorkflow();
      message.destroy();
      message.success(`워크플로우 실행 완료! (${(result.total_execution_time || 0).toFixed(2)}초)`);
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

          {/* 실행 결과 */}
          {executionResult && (
            <div style={{ 
              marginTop: 16, 
              padding: 12, 
              background: '#f6ffed', 
              border: '1px solid #b7eb8f', 
              borderRadius: 4 
            }}>
              <Text strong style={{ color: '#52c41a' }}>실행 완료!</Text>
              <br />
              <Text style={{ fontSize: 12 }}>
                실행 시간: {(executionResult.total_execution_time || 0).toFixed(2)}초
              </Text>
              <br />
              <Text style={{ fontSize: 12 }}>
                실행 순서: {(executionResult.execution_order || []).join(' → ')}
              </Text>
              
              {/* 각 노드의 실행 결과 표시 */}
              {executionResult.results && executionResult.results.length > 0 && (
                <>
                  <br />
                  <br />
                  <Text strong style={{ color: '#1890ff' }}>노드별 실행 결과:</Text>
                  {executionResult.results.map((result: any) => (
                    <div key={result.node_id} style={{ 
                      marginTop: 8, 
                      padding: 8, 
                      background: result.success ? '#fff' : '#fff2f0',
                      border: result.success ? '1px solid #d9d9d9' : '1px solid #ffccc7',
                      borderRadius: 4 
                    }}>
                      <Text strong style={{ fontSize: 12 }}>
                        {result.node_id}: 
                      </Text>
                      {result.success ? (
                        <Text style={{ fontSize: 12, marginLeft: 4 }}>
                          {result.description || '실행 완료'}
                        </Text>
                      ) : (
                        <Text style={{ fontSize: 12, marginLeft: 4, color: '#ff4d4f' }}>
                          오류: {result.error}
                        </Text>
                      )}
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </Space>
      </Card>
    </div>
  );
};