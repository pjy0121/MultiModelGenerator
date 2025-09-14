import React, { useState } from 'react';
import { Button, Input, Typography, Space, Alert, Collapse, Card, Tag } from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import { useWorkflowStore } from '../store/workflowStore';
import { LayerType } from '../types';
import CollapsibleWorkflowCanvas from './CollapsibleWorkflowCanvas';

const { Text } = Typography;
const { TextArea } = Input;

// 실행 결과 전용 간단 마크다운 렌더러 
const SimpleMarkdownRenderer: React.FC<{ content: string }> = ({ content }) => {
  if (!content || content.trim() === '') {
    return <Text type="secondary">내용이 없습니다.</Text>;
  }

  const lines = content.split('\n');
  const elements: React.ReactElement[] = [];
  let tableLines: string[] = [];
  let inTable = false;
  let key = 0;

  const renderTable = (tableData: string[]) => {
    if (tableData.length < 2) return null;
    
    const parseRow = (row: string) => {
      return row.split('|').map(cell => cell.trim()).filter(cell => cell !== '');
    };

    const headerRow = parseRow(tableData[0]);
    const dataRows = tableData.slice(2).map(parseRow).filter(row => row.length > 0);

    if (headerRow.length === 0) return null;

    return (
      <table key={`simple-table-${key++}`} style={{
        borderCollapse: 'collapse',
        width: '100%',
        fontSize: '12px',
        border: '2px solid #722ed1',
        marginBottom: '16px',
        backgroundColor: '#fff'
      }}>
        <thead>
          <tr style={{ backgroundColor: '#e6f7ff' }}>
            {headerRow.map((header, idx) => (
              <th key={idx} style={{
                border: '1px solid #722ed1',
                padding: '8px 12px',
                textAlign: 'left',
                fontWeight: 'bold',
                backgroundColor: '#bae7ff',
                color: '#722ed1'
              }}>
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataRows.map((row, rowIdx) => (
            <tr key={rowIdx}>
              {row.map((cell, cellIdx) => (
                <td key={cellIdx} style={{
                  border: '1px solid #722ed1',
                  padding: '8px 12px',
                  verticalAlign: 'top',
                  backgroundColor: '#fff'
                }}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const isTableLine = line.trim().includes('|') && line.trim().length > 0;

    if (isTableLine) {
      if (!inTable) {
        inTable = true;
        tableLines = [];
      }
      tableLines.push(line);
    } else {
      if (inTable) {
        const table = renderTable(tableLines);
        if (table) elements.push(table);
        inTable = false;
        tableLines = [];
      }
      
      if (line.trim()) {
        if (line.startsWith('**') && line.endsWith('**')) {
          elements.push(
            <div key={`heading-${key++}`} style={{
              fontWeight: 'bold',
              fontSize: '14px',
              color: '#722ed1',
              margin: '12px 0 6px 0'
            }}>
              {line.replace(/\*\*/g, '')}
            </div>
          );
        } else {
          elements.push(
            <div key={`text-${key++}`} style={{
              margin: '4px 0',
              lineHeight: '1.5'
            }}>
              {line}
            </div>
          );
        }
      }
    }
  }

  // 마지막에 테이블이 있었다면 처리
  if (inTable && tableLines.length > 0) {
    const table = renderTable(tableLines);
    if (table) elements.push(table);
  }

  return <div>{elements}</div>;
};

export const LayerWorkflowPanel: React.FC = () => {
  const { 
    nodes,
    selectedKnowledgeBase,
    keyword,
    isExecuting,
    layerPrompts,
    layerInputs,
    layerResults,
    selectedProvider,
    executeLayerWithPrompt,
    setLayerPrompt,
    setLayerInput,
    resetExecution,
    startStepwiseExecution
  } = useWorkflowStore();

  const [executingLayers, setExecutingLayers] = useState<Set<LayerType>>(new Set());

  // 레이어별 노드 개수 계산
  const getLayerNodeCount = (layerType: LayerType): number => {
    return nodes.filter(node => 
      node.type === 'customNode' && 
      (node as any).data.layer === layerType
    ).length;
  };

  // 레이어 요약 정보 생성 (JSX 반환)
  const renderLayerSummary = () => {
    const genCount = getLayerNodeCount(LayerType.GENERATION);
    const ensCount = getLayerNodeCount(LayerType.ENSEMBLE);
    const valCount = getLayerNodeCount(LayerType.VALIDATION);
    
    return (
      <Space size={4}>
        <Tag color="green" style={{ margin: 0, fontSize: '11px' }}>
          Gen: {genCount}
        </Tag>
        <Tag color="purple" style={{ margin: 0, fontSize: '11px' }}>
          Ens: {ensCount}
        </Tag>
        <Tag color="orange" style={{ margin: 0, fontSize: '11px' }}>
          Val: {valCount}
        </Tag>
      </Space>
    );
  };

  // 전체 워크플로우 순차 실행 (startStepwiseExecution 사용)
  const handleBatchExecute = async () => {
    if (!selectedKnowledgeBase) {
      return;
    }
    
    if (!keyword.trim()) {
      return;
    }

    try {
      // 각 레이어에 기본 입력 설정 (키워드 기반)
      if (!layerInputs.generation.trim()) {
        setLayerInput(LayerType.GENERATION, keyword.trim());
      }
      
      // startStepwiseExecution을 사용하여 전체 워크플로우 실행
      await startStepwiseExecution();
      
    } catch (error: any) {
      // 에러는 startStepwiseExecution 내부에서 처리됨
      console.error('전체 워크플로우 실행 실패:', error);
    }
  };

  const handleLayerExecution = async (layerType: LayerType) => {
    // input_data 검증
    const input = layerInputs[layerType] || '';
    if (!input.trim()) {
      return;
    }

    setExecutingLayers(prev => new Set(prev).add(layerType));
    
    try {
      // 개별 Layer 실행 시 currentExecution 초기화
      resetExecution();
      await executeLayerWithPrompt(layerType);
      
      // 실행 완료 (결과는 ExecutionResultPanel에서 자동으로 감지됨)
    } finally {
      setExecutingLayers(prev => {
        const next = new Set(prev);
        next.delete(layerType);
        return next;
      });
    }
  };

  const renderLayer = (layerType: LayerType, title: string) => {
    const prompt = layerPrompts[layerType] || '';
    const input = layerInputs[layerType] || '';
    const result = layerResults[layerType];
    const isLayerExecuting = executingLayers.has(layerType);
    const isAnyExecuting = isExecuting || isLayerExecuting; // 전체 실행 또는 개별 레이어 실행 중

    const collapseItems = [
      {
        key: layerType,
        label: (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <span>{title}</span>
            <Button
              type="primary"
              onClick={(e) => {
                e.stopPropagation(); // Collapse 토글 방지
                handleLayerExecution(layerType);
              }}
              loading={isLayerExecuting}
              disabled={!prompt.trim() || !selectedKnowledgeBase || !input.trim() || isAnyExecuting}
              size="small"
            >
              실행
            </Button>
          </div>
        ),
        children: (
          <>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div>
                <Text strong>Layer Prompt:</Text>
                <TextArea
                  value={prompt}
                  onChange={(e) => setLayerPrompt(layerType, e.target.value)}
                  placeholder={`${title} 프롬프트를 입력하세요`}
                  rows={6}
                  style={{ marginTop: 8 }}
                />
              </div>

              <div>
                <Text strong>Layer Input:</Text>
                <TextArea
                  value={input}
                  onChange={(e) => setLayerInput(layerType, e.target.value)}
                  placeholder={`${title} 입력 데이터를 입력하세요`}
                  rows={4}
                  style={{ marginTop: 8 }}
                />
              </div>

              {result && (
                <div>
                  <Text strong>실행 결과:</Text>
                  <div style={{ 
                    marginTop: 8, 
                    padding: 12, 
                    backgroundColor: '#f6ffed', 
                    border: '1px solid #b7eb8f', 
                    borderRadius: 4,
                    maxHeight: 400,
                    overflow: 'auto'
                  }}>
                    {result.node_outputs ? (
                      <div style={{ width: '100%' }}>
                        {Object.keys(result.node_outputs)
                          .filter(key => key.startsWith('node'))
                          .map((nodeKey) => {
                            const general_output = result.node_outputs[nodeKey];
                            
                            return (
                              <div key={nodeKey} style={{ marginBottom: '16px' }}>
                                <Text strong style={{ fontSize: '10px', color: '#1890ff', display: 'block', marginBottom: '4px' }}>
                                  {nodeKey} 결과:
                                </Text>
                                <div style={{ 
                                  backgroundColor: '#fff',
                                  padding: '8px',
                                  borderRadius: '4px',
                                  border: '1px solid #e8e8e8',
                                  fontSize: '11px'
                                }}>
                                  <SimpleMarkdownRenderer content={general_output || '결과 없음'} />
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    ) : (
                      <Text type="secondary">결과 데이터가 없습니다.</Text>
                    )}
                  </div>
                </div>
              )}
            </Space>
          </>
        )
      }
    ];

    return <Collapse items={collapseItems} />;
  };

  if (!selectedKnowledgeBase) {
    return (
      <Alert
        message="지식 베이스가 선택되지 않았습니다"
        description="먼저 실행 설정 창에서 지식 베이스를 선택해주세요."
        type="warning"
        showIcon
      />
    );
  }

  // 실행 가능 여부 확인
  const canExecute = () => {
    if (!selectedKnowledgeBase || !keyword.trim()) {
      return false;
    }
    if (!selectedProvider) {
      return false;
    }
    // 모델 검증은 실행 시점에서 수행 (provider별 동적 로딩)
    return true;
  };

  // 실행 불가 사유 메시지
  const getDisabledReason = () => {
    if (!selectedKnowledgeBase) return '지식 베이스를 선택해주세요';
    if (!keyword.trim()) return '키워드를 입력해주세요';
    if (!selectedProvider) return 'LLM Provider를 선택해주세요';
    // 모델 검증은 실행 시점에서 수행
    return '';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
      {/* 실행 불가 상태 알림 */}
      {!canExecute() && (
        <Alert
          message={getDisabledReason()}
          type="warning"
          showIcon
          style={{ marginBottom: 8 }}
        />
      )}
      
      {/* 워크플로우 구성 카드 */}
      <Card 
        title="워크플로우 구성" 
        size="small"
        extra={
          <Button
            type="primary"
            size="small"
            onClick={handleBatchExecute}
            loading={isExecuting}
            disabled={!canExecute()}
            title={!canExecute() ? getDisabledReason() : ''}
          >
            전체 워크플로우 실행
          </Button>
        }
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* 워크플로우 배치 섹션 */}
          <Collapse
            size="small"
            defaultActiveKey={['workflow-layout']}
            items={[{
              key: 'workflow-layout',
              label: (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                  <Space>
                    <SettingOutlined />
                    <span>워크플로우 배치</span>
                  </Space>
                  {renderLayerSummary()}
                </div>
              ),
              children: (
                <div style={{ height: '400px' }}>
                  <CollapsibleWorkflowCanvas />
                </div>
              )
            }]}
          />
          
          {/* Layer별 실행 섹션 */}
          {renderLayer(LayerType.GENERATION, 'Generation Layer')}
          {renderLayer(LayerType.ENSEMBLE, 'Ensemble Layer')}
          {renderLayer(LayerType.VALIDATION, 'Validation Layer')}
        </Space>
      </Card>
    </div>
  );
};