import React, { useState } from 'react';
import { Button, Input, Typography, Space, Alert, Collapse, Card, Tag } from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import { useWorkflowStore } from '../store/workflowStore';
import { LayerType } from '../types';
import ReactMarkdown from 'react-markdown';
import CollapsibleWorkflowCanvas from './CollapsibleWorkflowCanvas';

const { Text } = Typography;
const { TextArea } = Input;

// 개선된 Markdown 렌더러 - 테이블을 제대로 렌더링
const MarkdownRenderer: React.FC<{ content: string }> = ({ content }) => {
  // 빈 내용이나 undefined인 경우 처리
  if (!content || content.trim() === '') {
    return <Text type="secondary">내용이 없습니다.</Text>;
  }

  return (
    <div style={{ fontSize: '13px', lineHeight: '1.5' }}>
      <ReactMarkdown
        components={{
          table: ({ children }) => (
            <table style={{ 
              borderCollapse: 'collapse', 
              width: '100%', 
              fontSize: '12px',
              border: '2px solid #1890ff',
              marginBottom: '16px',
              backgroundColor: '#fff'
            }}>
              {children}
            </table>
          ),
          thead: ({ children }) => (
            <thead style={{ backgroundColor: '#e6f7ff' }}>
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th style={{ 
              border: '1px solid #1890ff', 
              padding: '10px',
              textAlign: 'left',
              fontWeight: 'bold',
              backgroundColor: '#bae7ff',
              color: '#1890ff'
            }}>
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td style={{ 
              border: '1px solid #1890ff', 
              padding: '8px',
              verticalAlign: 'top',
              backgroundColor: '#fff'
            }}>
              {children}
            </td>
          ),
          p: ({ children }) => (
            <p style={{ margin: '8px 0', whiteSpace: 'pre-wrap' }}>
              {children}
            </p>
          ),
          h1: ({ children }) => (
            <h1 style={{ fontSize: '16px', fontWeight: 'bold', margin: '12px 0 8px 0', color: '#1890ff' }}>
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 style={{ fontSize: '14px', fontWeight: 'bold', margin: '10px 0 6px 0', color: '#1890ff' }}>
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 style={{ fontSize: '13px', fontWeight: 'bold', margin: '8px 0 4px 0', color: '#1890ff' }}>
              {children}
            </h3>
          ),
          ul: ({ children }) => (
            <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol style={{ margin: '8px 0', paddingLeft: '20px' }}>
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li style={{ margin: '2px 0' }}>
              {children}
            </li>
          ),
          strong: ({ children }) => (
            <strong style={{ color: '#1890ff' }}>
              {children}
            </strong>
          ),
          code: ({ children }) => (
            <code style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '2px 4px', 
              borderRadius: '3px',
              fontSize: '11px',
              border: '1px solid #e8e8e8'
            }}>
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '12px', 
              borderRadius: '4px',
              border: '1px solid #e8e8e8',
              overflow: 'auto',
              fontSize: '11px'
            }}>
              {children}
            </pre>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
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
    executeLayerWithPrompt,
    setLayerPrompt,
    setLayerInput,
    setIsExecuting
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
        <Tag color="blue" style={{ margin: 0, fontSize: '11px' }}>
          Gen: {genCount}
        </Tag>
        <Tag color="orange" style={{ margin: 0, fontSize: '11px' }}>
          Ens: {ensCount}
        </Tag>
        <Tag color="green" style={{ margin: 0, fontSize: '11px' }}>
          Val: {valCount}
        </Tag>
      </Space>
    );
  };

  // 전체 워크플로우 순차 실행 (Layer별 실행 방식 사용)
  const handleBatchExecute = async () => {
    if (!selectedKnowledgeBase) {
      return;
    }
    
    if (!keyword.trim()) {
      return;
    }

    try {
      setIsExecuting(true);
      
      // 각 레이어에 기본 입력 설정 (키워드 기반)
      if (!layerInputs.generation.trim()) {
        setLayerInput(LayerType.GENERATION, keyword.trim());
      }
      
      console.log('전체 워크플로우 순차 실행 시작...');
      
      // 1. Generation Layer 실행
      console.log('Step 1: Generation Layer 실행');
      await executeLayerWithPrompt(LayerType.GENERATION);
      
      // 잠시 대기 후 결과 확인
      await new Promise(resolve => setTimeout(resolve, 500));
      const genResult = layerResults.generation;
      
      if (genResult && genResult.combined_result) {
        setLayerInput(LayerType.ENSEMBLE, genResult.combined_result);
        
        // 2. Ensemble Layer 실행
        console.log('Step 2: Ensemble Layer 실행');
        await executeLayerWithPrompt(LayerType.ENSEMBLE);
        
        // 잠시 대기 후 결과 확인
        await new Promise(resolve => setTimeout(resolve, 500));
        const ensResult = layerResults.ensemble;
        
        if (ensResult && ensResult.combined_result) {
          setLayerInput(LayerType.VALIDATION, ensResult.combined_result);
          
          // 3. Validation Layer 실행
          console.log('Step 3: Validation Layer 실행');
          await executeLayerWithPrompt(LayerType.VALIDATION);
        }
      }
      
      console.log('전체 워크플로우 실행 완료!');
    } catch (error: any) {
      console.error('전체 워크플로우 실행 중 오류가 발생했습니다:', error);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleLayerExecution = async (layerType: LayerType) => {
    // input_data 검증
    const input = layerInputs[layerType] || '';
    if (!input.trim()) {
      console.warn(`${layerType} Layer: input_data가 비어있어서 실행할 수 없습니다.`);
      return;
    }

    setExecutingLayers(prev => new Set(prev).add(layerType));
    
    try {
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
    const isExecuting = executingLayers.has(layerType);

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
              loading={isExecuting}
              disabled={!prompt.trim() || !selectedKnowledgeBase || !input.trim()}
              size="small"
            >
              실행
            </Button>
          </div>
        ),
        children: (
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
              {input && (
                <div style={{ marginTop: 8 }}>
                  <Text strong>Input 미리보기:</Text>
                  <div style={{ 
                    marginTop: 4, 
                    padding: 8, 
                    backgroundColor: '#f9f9f9', 
                    border: '1px solid #d9d9d9', 
                    borderRadius: 4,
                    maxHeight: 200,
                    overflow: 'auto'
                  }}>
                    <MarkdownRenderer content={input} />
                  </div>
                </div>
              )}
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
                  {result.combined_result ? (
                    <MarkdownRenderer content={result.combined_result} />
                  ) : (
                    <Text type="secondary">결과가 비어있습니다. 콘솔을 확인해주세요.</Text>
                  )}
                </div>
                {/* 디버깅용 정보 */}
                <details style={{ marginTop: 8, fontSize: '11px' }}>
                  <summary>디버그 정보</summary>
                  <pre style={{ fontSize: '10px', color: '#666' }}>
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </details>
              </div>
            )}
          </Space>
        )
      }
    ];

    return <Collapse items={collapseItems} />;
  };

  if (!selectedKnowledgeBase) {
    return (
      <Alert
        message="Knowledge Base가 선택되지 않았습니다"
        description="먼저 ControlPanel에서 Knowledge Base를 선택해주세요."
        type="warning"
        showIcon
      />
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
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
            disabled={!selectedKnowledgeBase || !keyword.trim()}
          >
            전체 워크플로우 실행
          </Button>
        }
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* 워크플로우 배치 섹션 */}
          <Collapse
            size="small"
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