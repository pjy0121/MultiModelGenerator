import React, { useState, useMemo, useCallback, memo, useRef, useEffect } from 'react';
import { Card, Typography, Alert, Button, Space, Modal } from 'antd';
import { FileExcelOutlined, FileTextOutlined, ExpandOutlined } from '@ant-design/icons';
import { useNodeWorkflowStore } from '../store/nodeWorkflowStore';
import { downloadUtils, getCurrentTimestamp } from '../utils/downloadUtils';
import { formatMarkdown } from '../utils/markdownUtils';

const { Title, Text } = Typography;

// 스트리밍 출력 컴포넌트 (자동 스크롤 기능 포함)
interface StreamingOutputProps {
  output: string;
  isExecuting: boolean;
}

const StreamingOutput: React.FC<StreamingOutputProps> = memo(({ output, isExecuting }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const previousOutputLength = useRef<number>(0);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const userScrolledRef = useRef<boolean>(false); // 사용자가 수동으로 스크롤했는지 추적
  const scrollTimeoutRef = useRef<number | null>(null);

  // 사용자가 스크롤 위치를 변경했는지 감지
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;
    
    const scrollElement = scrollRef.current;
    const isAtBottom = scrollElement.scrollTop + scrollElement.clientHeight >= scrollElement.scrollHeight - 5;
    
    // 스크롤 이벤트 디바운싱
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }
    
    scrollTimeoutRef.current = setTimeout(() => {
      if (isAtBottom) {
        // 맨 아래에 있으면 자동 스크롤 활성화
        setAutoScroll(true);
        userScrolledRef.current = false;
      } else if (!userScrolledRef.current) {
        // 사용자가 위로 스크롤했으면 자동 스크롤 비활성화
        setAutoScroll(false);
        userScrolledRef.current = true;
      }
    }, 50); // 50ms 디바운싱
  }, []);

  // 스트리밍 출력이 업데이트될 때마다 스크롤을 맨 아래로 이동 (자동 스크롤이 활성화된 경우에만)
  useEffect(() => {
    if (scrollRef.current && output && autoScroll && !userScrolledRef.current) {
      const scrollElement = scrollRef.current;
      const currentOutputLength = output.length;
      
      // 새로운 콘텐츠가 추가되었을 때만 스크롤
      if (currentOutputLength > previousOutputLength.current) {
        // requestAnimationFrame을 사용해서 DOM 업데이트 후에 스크롤
        requestAnimationFrame(() => {
          if (scrollElement && autoScroll && !userScrolledRef.current) {
            scrollElement.scrollTop = scrollElement.scrollHeight;
          }
        });
        
        previousOutputLength.current = currentOutputLength;
      }
    }
  }, [output, autoScroll]);

  // 실행이 시작될 때 자동 스크롤 활성화 및 길이 초기화
  useEffect(() => {
    if (isExecuting) {
      setAutoScroll(true);
      userScrolledRef.current = false;
      previousOutputLength.current = 0;
    }
  }, [isExecuting]);

  // 컴포넌트 언마운트 시 타이머 정리
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  if (!output) {
    return null;
  }

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ 
        fontSize: 10, 
        color: '#999', 
        marginBottom: 4,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        {!autoScroll && isExecuting && (
          <span style={{ 
            fontSize: 9, 
            color: '#ff8c00', 
            fontStyle: 'italic',
            cursor: 'pointer',
            padding: '2px 6px',
            backgroundColor: '#fff3cd',
            border: '1px solid #ffecb5',
            borderRadius: 3
          }} onClick={() => {
            setAutoScroll(true);
            userScrolledRef.current = false;
            // 클릭 시 즉시 아래로 스크롤
            if (scrollRef.current) {
              scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
            }
          }}>
            ⏸️ 자동 스크롤 중지됨 (클릭하여 재개)
          </span>
        )}
      </div>
      <div 
        ref={scrollRef}
        onScroll={handleScroll}
        style={{ 
          padding: 8,
          backgroundColor: '#f6f6f6',
          border: '1px solid #d9d9d9',
          borderRadius: 4,
          maxHeight: 200,
          overflowY: 'auto',
          scrollBehavior: 'auto' // 자동 스크롤은 즉시, 사용자 스크롤은 부드럽게
        }}
      >
        <div 
          style={{ 
            margin: 0, 
            fontSize: 11,
            color: '#333',
            lineHeight: 1.4
          }}
          dangerouslySetInnerHTML={{
            __html: formatMarkdown(output || '')
          }}
        />
      </div>
    </div>
  );
});

// 완료된 결과 표시 컴포넌트 (자동 스크롤 기능 포함)
interface CompletedResultDisplayProps {
  content: string;
  nodeType: string;
  isNewResult?: boolean; // 새로 완료된 결과인지 여부
}

const CompletedResultDisplay: React.FC<CompletedResultDisplayProps> = memo(({ content, nodeType, isNewResult = false }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // 결과가 렌더링될 때마다 스크롤을 맨 아래로 이동
  useEffect(() => {
    if (scrollRef.current && content) {
      // DOM이 완전히 렌더링된 후 스크롤
      const timer = setTimeout(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      }, isNewResult ? 200 : 100); // 새 결과일 때는 조금 더 지연
      
      return () => clearTimeout(timer);
    }
  }, [content, isNewResult]);

  // 컴포넌트가 마운트된 후에도 한 번 더 스크롤 (늦게 로딩되는 내용 대응)
  useEffect(() => {
    if (scrollRef.current && content) {
      const timer = setTimeout(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      }, 300);
      
      return () => clearTimeout(timer);
    }
  }, []);

  if (!content) {
    return null;
  }

  return (
    <div 
      ref={scrollRef}
      style={{ 
        maxHeight: '300px', 
        overflowY: 'auto', 
        padding: '8px',
        border: '1px solid #d9d9d9',
        borderRadius: '4px',
        backgroundColor: nodeType === 'output-node' ? '#fafafa' : nodeType === 'input-node' ? '#f0f8ff' : '#f6f8fa',
        scrollBehavior: 'auto' // 즉시 스크롤 이동
      }}
    >
      <MarkdownWithDownload content={content} />
    </div>
  );
});

// 테이블 다운로드 컴포넌트
interface TableDownloadButtonsProps {
  headerRow: string[];
  dataRows: string[][];
  tableIndex: number;
}

const TableDownloadButtons: React.FC<TableDownloadButtonsProps> = memo(({ 
  headerRow, 
  dataRows, 
  tableIndex 
}) => {
  const [isModalVisible, setIsModalVisible] = useState(false);

  const handleDownloadExcel = useCallback(() => {
    const filename = `table_${tableIndex + 1}_${getCurrentTimestamp()}.xlsx`;
    downloadUtils.downloadExcel(headerRow, dataRows, filename);
  }, [headerRow, dataRows, tableIndex]);

  const handleDownloadTXT = useCallback(() => {
    const txtContent = downloadUtils.tableToTXT(headerRow, dataRows);
    const filename = `table_${tableIndex + 1}_${getCurrentTimestamp()}.txt`;
    downloadUtils.downloadFile(txtContent, filename, 'text/plain;charset=utf-8;');
  }, [headerRow, dataRows, tableIndex]);

  const handleDownloadMD = useCallback(() => {
    const mdContent = downloadUtils.tableToMarkdown(headerRow, dataRows);
    const filename = `table_${tableIndex + 1}_${getCurrentTimestamp()}.md`;
    downloadUtils.downloadFile(mdContent, filename, 'text/markdown;charset=utf-8;');
  }, [headerRow, dataRows, tableIndex]);

  const openModal = useCallback(() => setIsModalVisible(true), []);
  const closeModal = useCallback(() => setIsModalVisible(false), []);

  return (
    <>
      <div style={{ 
        margin: '8px 0',
        padding: '8px',
        backgroundColor: '#f8f9fa',
        borderRadius: '4px',
        border: '1px solid #e9ecef',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <Space size="small">
          <Text strong style={{ fontSize: '11px', color: '#666' }}>
            표 다운로드:
          </Text>
          <Button
            type="link"
            size="small"
            icon={<FileExcelOutlined />}
            onClick={handleDownloadExcel}
            style={{ padding: '2px 8px', height: 'auto', fontSize: '11px' }}
          >
            Excel
          </Button>
          <Button
            type="link"
            size="small"
            icon={<FileTextOutlined />}
            onClick={handleDownloadTXT}
            style={{ padding: '2px 8px', height: 'auto', fontSize: '11px' }}
          >
            TXT
          </Button>
          <Button
            type="link"
            size="small"
            icon={<FileTextOutlined />}
            onClick={handleDownloadMD}
            style={{ padding: '2px 8px', height: 'auto', fontSize: '11px' }}
          >
            MD
          </Button>
        </Space>
        <Button
          type="link"
          size="small"
          icon={<ExpandOutlined />}
          onClick={openModal}
          style={{ padding: '2px 8px', height: 'auto', fontSize: '11px' }}
        >
          크게 보기
        </Button>
      </div>
      <Modal
        title={`표 크게 보기 (테이블 ${tableIndex + 1})`}
        open={isModalVisible}
        onOk={closeModal}
        onCancel={closeModal}
        width="90vw"
        footer={null}
        styles={{ body: { maxHeight: '80vh', overflowY: 'auto' } }}
      >
        <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '14px' }}>
          <thead>
            <tr>
              {headerRow.map((cell, idx) => (
                <th key={idx} style={{
                  border: '1px solid #d9d9d9',
                  padding: '12px',
                  background: '#f5f5f5',
                  fontWeight: 600,
                  textAlign: 'left'
                }}>
                  {cell}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {row.map((cell, cellIdx) => (
                  <td key={cellIdx} style={{
                    border: '1px solid #d9d9d9',
                    padding: '12px',
                    verticalAlign: 'top',
                    wordBreak: 'break-word'
                  }}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Modal>
    </>
  );
});

// 다운로드 기능이 포함된 마크다운 렌더러
interface MarkdownWithDownloadProps {
  content: string;
}

const MarkdownWithDownload: React.FC<MarkdownWithDownloadProps> = memo(({ content }) => {
  const renderContentWithDownload = useCallback(() => {
    if (!content) return null;

    // 테이블이 있는지 확인
    const hasTable = content.includes('|');
    
    // 테이블이 없으면 기존 formatMarkdown 사용
    if (!hasTable) {
      return (
        <div dangerouslySetInnerHTML={{ __html: formatMarkdown(content) }} />
      );
    }

    const lines = content.split('\n');
    const elements: React.ReactElement[] = [];
    let inTable = false;
    let tableLines: string[] = [];
    let currentTableIndex = 0;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const isTableLine = line.includes('|') && line.trim().length > 0;

      if (isTableLine) {
        if (!inTable) {
          inTable = true;
          tableLines = [];
        }
        tableLines.push(line);
      } else {
        if (inTable) {
          // 테이블 종료 - 테이블과 다운로드 버튼을 함께 렌더링
          const table = renderTableWithDownload(tableLines, currentTableIndex++);
          if (table) elements.push(table);
          inTable = false;
          tableLines = [];
        }

        // 일반 텍스트 처리
        if (line.trim()) {
          elements.push(
            <div key={`text-${i}`} style={{ marginBottom: '8px' }}>
              <span dangerouslySetInnerHTML={{ __html: formatMarkdown(line) }} />
            </div>
          );
        } else {
          // 빈 줄 처리
          elements.push(<div key={`empty-${i}`} style={{ height: '8px' }} />);
        }
      }
    }

    // 마지막에 테이블이 있는 경우
    if (inTable && tableLines.length > 0) {
      const table = renderTableWithDownload(tableLines, currentTableIndex);
      if (table) elements.push(table);
    }

    return elements;
  }, [content]);

  const renderTableWithDownload = (tableLines: string[], tableIndex: number): React.ReactElement | null => {
    if (tableLines.length < 2) return null;

    const processedRows = tableLines.map(row => 
      row.replace(/^\||\|$/g, '').split('|').map(cell => cell.trim())
    );

    // 구분선 행 찾기 및 스킵
    const separatorIndex = processedRows.findIndex(row => 
      row.every(cell => cell.match(/^-+$/))
    );
    
    const headerRow = processedRows[0];
    const dataStartIndex = separatorIndex > 0 ? separatorIndex + 1 : 1;
    const dataRows = processedRows.slice(dataStartIndex);

    if (headerRow.length === 0 || dataRows.length === 0) return null;

    return (
      <div key={`table-${tableIndex}`} style={{ margin: '12px 0' }}>
        <TableDownloadButtons 
          headerRow={headerRow}
          dataRows={dataRows}
          tableIndex={tableIndex}
        />
        <table style={{ 
          borderCollapse: 'collapse', 
          width: '100%', 
          fontSize: '11px', 
          border: '1px solid #d9d9d9'
        }}>
          <thead>
            <tr>
              {headerRow.map((cell, idx) => (
                <th key={idx} style={{
                  border: '1px solid #d9d9d9',
                  padding: '8px 12px',
                  background: '#f5f5f5',
                  fontWeight: 600,
                  textAlign: 'left',
                  color: '#262626'
                }}>
                  {cell}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {row.map((cell, cellIdx) => (
                  <td key={cellIdx} style={{
                    border: '1px solid #d9d9d9',
                    padding: '8px 12px',
                    verticalAlign: 'top',
                    wordBreak: 'break-word'
                  }}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div 
      style={{ 
        padding: 8,
        backgroundColor: '#f9f9f9',
        borderRadius: 4,
        border: '1px solid #e1e1e1',
        fontSize: 11,
        lineHeight: 1.6
      }}
    >
      {renderContentWithDownload()}
    </div>
  );
});



export const NodeExecutionResultPanel: React.FC = memo(() => {
  const {
    nodes,
    isExecuting,
    executionResult,
    nodeExecutionStates,
    nodeStreamingOutputs,
    nodeExecutionResults,
    nodeStartOrder,
  } = useNodeWorkflowStore();

  // 이전 실행 상태를 추적하여 새로 완료된 노드 감지
  const previousExecutionStates = useRef<Record<string, string>>({});
  const [newlyCompletedNodes, setNewlyCompletedNodes] = useState<Set<string>>(new Set());

  // 실행 상태 변화 감지
  useEffect(() => {
    const currentStates = { ...nodeExecutionStates };
    const newlyCompleted = new Set<string>();
    
    Object.keys(currentStates).forEach(nodeId => {
      const currentState = currentStates[nodeId];
      const previousState = previousExecutionStates.current[nodeId];
      
      // 이전 상태가 'executing'이고 현재 상태가 'completed'이면 새로 완료됨
      if (previousState === 'executing' && currentState === 'completed') {
        newlyCompleted.add(nodeId);
      }
    });
    
    if (newlyCompleted.size > 0) {
      setNewlyCompletedNodes(newlyCompleted);
      
      // 일정 시간 후 새로 완료됨 플래그 제거
      const timer = setTimeout(() => {
        setNewlyCompletedNodes(new Set());
      }, 1000);
      
      return () => clearTimeout(timer);
    }
    
    previousExecutionStates.current = currentStates;
  }, [nodeExecutionStates]);

  // 노드 실행 시작 순서대로 정렬 (고정된 순서 유지) - 메모이제이션으로 최적화
  const orderedNodes = useMemo(() => {
    // 실행 결과가 있거나 실행 상태가 설정된 노드들만 포함
    const startedNodes = nodes.filter(node => {
      const state = nodeExecutionStates[node.id];
      const hasResult = nodeExecutionResults[node.id];
      return hasResult || (state && state !== 'idle');
    });
    
    // 노드 시작 순서가 있으면 그 순서를 기준으로 정렬
    if (nodeStartOrder.length > 0) {
      const orderedNodes: any[] = [];
      
      // 시작 순서에 따라 노드 배치
      nodeStartOrder.forEach(nodeId => {
        const node = startedNodes.find(n => n.id === nodeId);
        if (node) {
          orderedNodes.push(node);
        }
      });
      
      // 시작 순서에 없지만 현재 실행된 노드들을 뒤에 추가 (ID 순)
      const remainingNodes = startedNodes
        .filter(node => !nodeStartOrder.includes(node.id))
        .sort((a, b) => a.id.localeCompare(b.id));
      
      return [...orderedNodes, ...remainingNodes];
    }
    
    // 시작 순서 정보가 없으면 단순히 ID 순으로 정렬
    return startedNodes.sort((a, b) => a.id.localeCompare(b.id));
  }, [nodes, nodeExecutionStates, nodeExecutionResults, nodeStartOrder]);

  return (
    <div style={{ padding: '16px', height: '100%' }}>
      <Title level={4} style={{ marginBottom: 16 }}>
        실행 결과
      </Title>

      {/* 실행 중 표시 */}
      {isExecuting && (
        <Alert
          message="워크플로우 실행 중..."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 노드별 실행 결과 */}
      {orderedNodes.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {orderedNodes.map(node => {
            const executionState = nodeExecutionStates[node.id];
            const streamingOutput = nodeStreamingOutputs[node.id];
            const executionResult = nodeExecutionResults[node.id];
            
            const getStatusColor = () => {
              switch (executionState) {
                case 'executing': return '#ff4d4f'; // 실행 중만 빨간색
                case 'completed': return '#52c41a';
                case 'error': return '#ff4d4f';
                default: return '#666';
              }
            };

            const getBorderColor = () => {
              // 실행 중인 노드만 빨간색 테두리, 나머지는 기본 테두리
              return executionState === 'executing' ? '#ff4d4f' : '#d9d9d9';
            };
            
            const getStatusText = () => {
              switch (executionState) {
                case 'executing': return '실행 중...';
                case 'completed': return '완료';
                case 'error': return '오류';
                default: return '대기';
              }
            };

            const getBackgroundColor = () => {
              switch (executionState) {
                case 'executing': return '#e6f7ff';
                case 'completed': return '#f6ffed';
                case 'error': return '#fff2f0';
                default: return '#f9f9f9';
              }
            };
            
            return (
              <Card
                key={node.id}
                size="small"
                style={{
                  background: getBackgroundColor(),
                  border: `1px solid ${getBorderColor()}`,
                }}
                title={
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Text strong style={{ color: getStatusColor() }}>
                      {node.data?.label || node.id}
                    </Text>
                    <span style={{ 
                      padding: '2px 8px', 
                      backgroundColor: getStatusColor(),
                      color: '#fff',
                      borderRadius: 3,
                      fontSize: 11
                    }}>
                      {getStatusText()}
                    </span>
                  </div>
                }
              >
                {/* 스트리밍 출력 (실행 중일 때만 표시) */}
                {executionState === 'executing' && (
                  <StreamingOutput 
                    output={streamingOutput || ''} 
                    isExecuting={true} 
                  />
                )}
                
                {/* 실행 결과 표시 (완료된 경우에만) */}
                {executionResult && executionState === 'completed' && (
                  <div style={{ fontSize: 11 }}>
                    {executionResult.success ? (
                      <div>
                        {/* 완료된 경우 최종 결과만 표시 */}
                        {executionResult.description && (
                          <div>
                            {/* output-node의 경우 <output></output> 또는 <출력></출력> 내의 내용만 추출하여 스크롤 가능하게 표시 */}
                            {node.node_type === 'output-node' ? (
                              (() => {
                                const outputPatterns = [
                                  /<output>([\s\S]*?)<\/output>/i,
                                  /<출력>([\s\S]*?)<\/출력>/i
                                ];
                                
                                let outputMatch = null;
                                for (const pattern of outputPatterns) {
                                  outputMatch = executionResult.description?.match(pattern);
                                  if (outputMatch) break;
                                }
                                
                                const outputContent = outputMatch ? outputMatch[1].trim() : executionResult.description;
                                
                                return (
                                  <CompletedResultDisplay 
                                    content={outputContent || ''} 
                                    nodeType={node.node_type}
                                    isNewResult={newlyCompletedNodes.has(node.id)}
                                  />
                                );
                              })()
                            ) : (
                              // input-node와 일반 노드의 경우 전체 내용을 스크롤 가능하게 표시
                              (() => {
                                const content = executionResult.description || '';
                                const isInputNode = node.node_type === 'input-node';
                                
                                return (
                                  <div>
                                    {isInputNode && (
                                      <div style={{ 
                                        marginBottom: '8px', 
                                        fontSize: '10px', 
                                        color: '#1890ff',
                                        fontWeight: 'bold'
                                      }}>
                                        📄 입력 데이터 내용: {content ? `(${content.length}자)` : '(내용 없음)'}
                                      </div>
                                    )}
                                    {content && content.trim() ? (
                                      <CompletedResultDisplay 
                                        content={content} 
                                        nodeType={node.node_type}
                                        isNewResult={newlyCompletedNodes.has(node.id)}
                                      />
                                    ) : (
                                      <div style={{ 
                                        color: '#999', 
                                        fontStyle: 'italic',
                                        fontSize: '10px',
                                        textAlign: 'center',
                                        padding: '20px'
                                      }}>
                                        {isInputNode ? '입력 노드에 내용이 설정되지 않았습니다.' : '출력 내용이 없습니다.'}
                                      </div>
                                    )}
                                  </div>
                                );
                              })()
                            )}
                          </div>
                        )}
                      </div>
                    ) : (
                      <Text style={{ color: '#ff4d4f' }}>
                        {executionResult.error || '알 수 없는 오류가 발생했습니다.'}
                      </Text>
                    )}
                  </div>
                )}
                
                {/* 에러 상태 표시 */}
                {executionState === 'error' && executionResult && (
                  <div style={{ fontSize: 11 }}>
                    <Text style={{ color: '#ff4d4f' }}>
                      {executionResult.error || '알 수 없는 오류가 발생했습니다.'}
                    </Text>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      ) : (
        <div style={{ 
          textAlign: 'center', 
          color: '#999', 
          marginTop: 40 
        }}>
          워크플로우를 실행하면 결과가 여기에 표시됩니다.
        </div>
      )}

      {/* 전체 실행 결과 요약 */}
      {executionResult && (
        <Card
          size="small"
          style={{ 
            marginTop: 16,
            background: executionResult.success ? '#f6ffed' : '#fff2f0', 
            border: `1px solid ${executionResult.success ? '#b7eb8f' : '#ffccc7'}`,
          }}
          title={
            <Text strong style={{ color: executionResult.success ? '#52c41a' : '#ff4d4f' }}>
              {executionResult.success ? '워크플로우 실행 완료!' : '워크플로우 실행 실패'}
            </Text>
          }
        >
          <Text style={{ fontSize: 12 }}>
            총 실행 시간: {(executionResult.total_execution_time || 0).toFixed(2)}초
          </Text>
          {executionResult.execution_order && executionResult.execution_order.length > 0 && (
            <>
              <br />
              <Text style={{ fontSize: 12 }}>
                실행 순서: {executionResult.execution_order.map(nodeId => {
                  const node = nodes.find(n => n.id === nodeId);
                  return node?.data?.label || nodeId;
                }).join(' → ')}
              </Text>
            </>
          )}
        </Card>
      )}
    </div>
  );
});