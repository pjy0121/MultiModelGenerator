import React, { useState } from 'react';
import { Card, Typography, Alert, Button, Space, Modal } from 'antd';
import { FileExcelOutlined, FileTextOutlined, ExpandOutlined } from '@ant-design/icons';
import * as XLSX from 'xlsx';
import { useNodeWorkflowStore } from '../store/nodeWorkflowStore';

const { Title, Text } = Typography;

// 파일 다운로드 유틸리티 함수들
const downloadUtils = {
  // Excel 파일 생성 및 다운로드
  downloadExcel: (headerRow: string[], dataRows: string[][], filename: string) => {
    // 헤더와 데이터를 하나의 배열로 결합
    const wsData = [headerRow, ...dataRows];
    
    // 워크시트 생성
    const ws = XLSX.utils.aoa_to_sheet(wsData);
    
    // 워크북 생성
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, '데이터');
    
    // 열 너비 자동 조정
    const colWidths = headerRow.map((_, colIndex) => {
      const maxLength = Math.max(
        headerRow[colIndex]?.length || 0,
        ...dataRows.map(row => row[colIndex]?.length || 0)
      );
      return { width: Math.min(Math.max(maxLength + 2, 10), 50) };
    });
    ws['!cols'] = colWidths;
    
    // 파일 다운로드
    XLSX.writeFile(wb, filename);
  },

  // TXT 파일 생성 (탭으로 구분)
  tableToTXT: (headerRow: string[], dataRows: string[][]): string => {
    const allRows = [headerRow, ...dataRows];
    return allRows.map(row => row.join('\t')).join('\n');
  },

  // 마크다운 테이블 생성
  tableToMarkdown: (headerRow: string[], dataRows: string[][]): string => {
    const headerLine = '| ' + headerRow.join(' | ') + ' |';
    const separatorLine = '| ' + headerRow.map(() => '---').join(' | ') + ' |';
    const dataLines = dataRows.map(row => '| ' + row.join(' | ') + ' |');
    
    return [headerLine, separatorLine, ...dataLines].join('\n');
  },

  // 파일 다운로드
  downloadFile: (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
};

// 현재 타임스탬프 생성
const getCurrentTimestamp = (): string => {
  const now = new Date();
  return now.toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');
};

// 테이블 다운로드 컴포넌트
interface TableDownloadButtonsProps {
  headerRow: string[];
  dataRows: string[][];
  tableIndex: number;
}

const TableDownloadButtons: React.FC<TableDownloadButtonsProps> = ({ 
  headerRow, 
  dataRows, 
  tableIndex 
}) => {
  const [isModalVisible, setIsModalVisible] = useState(false);

  const handleDownloadExcel = () => {
    const filename = `table_${tableIndex + 1}_${getCurrentTimestamp()}.xlsx`;
    downloadUtils.downloadExcel(headerRow, dataRows, filename);
  };

  const handleDownloadTXT = () => {
    const txtContent = downloadUtils.tableToTXT(headerRow, dataRows);
    const filename = `table_${tableIndex + 1}_${getCurrentTimestamp()}.txt`;
    downloadUtils.downloadFile(txtContent, filename, 'text/plain;charset=utf-8;');
  };

  const handleDownloadMD = () => {
    const mdContent = downloadUtils.tableToMarkdown(headerRow, dataRows);
    const filename = `table_${tableIndex + 1}_${getCurrentTimestamp()}.md`;
    downloadUtils.downloadFile(mdContent, filename, 'text/markdown;charset=utf-8;');
  };

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
          onClick={() => setIsModalVisible(true)}
          style={{ padding: '2px 8px', height: 'auto', fontSize: '11px' }}
        >
          크게 보기
        </Button>
      </div>
      <Modal
        title={`표 크게 보기 (테이블 ${tableIndex + 1})`}
        visible={isModalVisible}
        onOk={() => setIsModalVisible(false)}
        onCancel={() => setIsModalVisible(false)}
        width="90vw"
        footer={null}
        bodyStyle={{ maxHeight: '80vh', overflowY: 'auto' }}
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
};

// 다운로드 기능이 포함된 마크다운 렌더러
interface MarkdownWithDownloadProps {
  content: string;
}

const MarkdownWithDownload: React.FC<MarkdownWithDownloadProps> = ({ content }) => {
  const renderContentWithDownload = () => {
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
  };

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
};

// 간단한 마크다운 포맷팅 함수
const formatMarkdown = (text: string): string => {
  if (!text) return '';
  
  let result = text;
  
  // 1. 코드 블록 처리 (가장 먼저)
  result = result.replace(/```([\s\S]*?)```/g, '<pre style="background: #f8f8f8; padding: 12px; border-radius: 6px; border: 1px solid #e1e1e1; margin: 12px 0; overflow-x: auto; font-family: \'Consolas\', \'Monaco\', monospace; font-size: 11px; line-height: 1.5; white-space: pre-wrap;">$1</pre>');
  
  // 2. 인라인 코드 처리
  result = result.replace(/`([^`]+)`/g, '<code style="background: #f1f1f1; padding: 3px 6px; border-radius: 4px; font-family: \'Consolas\', \'Monaco\', monospace; font-size: 10px; color: #e83e8c; border: 1px solid #e9ecef;">$1</code>');
  
  // 3. 헤더 처리 (### → ## → #)
  result = result.replace(/^### (.*$)/gim, '<h3 style="margin: 16px 0 8px 0; font-size: 13px; font-weight: 600; color: #1d39c4; border-bottom: 1px solid #d9d9d9; padding-bottom: 4px; line-height: 1.4;">$1</h3>');
  result = result.replace(/^## (.*$)/gim, '<h2 style="margin: 20px 0 10px 0; font-size: 14px; font-weight: 600; color: #1d39c4; border-bottom: 2px solid #1d39c4; padding-bottom: 6px; line-height: 1.4;">$1</h2>');
  result = result.replace(/^# (.*$)/gim, '<h1 style="margin: 24px 0 12px 0; font-size: 16px; font-weight: 600; color: #1d39c4; border-bottom: 3px solid #1d39c4; padding-bottom: 8px; line-height: 1.4;">$1</h1>');
  
  // 4. 굵은 텍스트 처리
  result = result.replace(/\*\*(.*?)\*\*/g, '<strong style="font-weight: 600; color: #262626;">$1</strong>');
  
  // 5. 기울임 텍스트 처리 (굵은 텍스트와 겹치지 않도록)
  result = result.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em style="font-style: italic; color: #595959;">$1</em>');
  
  // 6. 리스트 처리
  result = result.replace(/^\- (.+$)/gim, '<div style="margin: 6px 0; padding-left: 20px; position: relative; line-height: 1.5;"><span style="position: absolute; left: 0; color: #1890ff; font-weight: bold;">•</span>$1</div>');
  result = result.replace(/^(\d+)\. (.+$)/gim, '<div style="margin: 6px 0; padding-left: 28px; position: relative; line-height: 1.5;"><span style="position: absolute; left: 0; color: #1890ff; font-weight: bold;">$1.</span>$2</div>');
  
  // 7. 테이블 처리
  result = formatTables(result);
  
  // 8. 줄바꿈 처리 (마지막)
  result = result.replace(/\n/g, '<br/>');
  
  return result;
};

// 테이블 포맷팅 함수
const formatTables = (text: string): string => {
  const lines = text.split('\n');
  let result: string[] = [];
  let inTable = false;
  let tableRows: string[] = [];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 테이블 행인지 확인 (|로 시작하고 끝나거나, |가 포함됨)
    if (line.includes('|')) {
      if (!inTable) {
        inTable = true;
        tableRows = [];
      }
      tableRows.push(line);
    } else {
      // 테이블이 끝남
      if (inTable) {
        result.push(convertTableToHTML(tableRows));
        tableRows = [];
        inTable = false;
      }
      result.push(line);
    }
  }
  
  // 마지막에 테이블이 있는 경우
  if (inTable && tableRows.length > 0) {
    result.push(convertTableToHTML(tableRows));
  }
  
  return result.join('\n');
};

// HTML 문자열용 테이블 변환 (기존 유지)
const convertTableToHTML = (tableRows: string[]): string => {
  if (tableRows.length < 2) return tableRows.join('\n');
  
  const processedRows = tableRows.map(row => 
    row.replace(/^\||\|$/g, '').split('|').map(cell => cell.trim())
  );
  
  let html = '<table style="border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 11px; border: 1px solid #d9d9d9;">';
  
  // 헤더 행
  if (processedRows.length > 0) {
    html += '<thead><tr>';
    processedRows[0].forEach(cell => {
      html += `<th style="border: 1px solid #d9d9d9; padding: 8px 12px; background: #f5f5f5; font-weight: 600; text-align: left; color: #262626;">${cell}</th>`;
    });
    html += '</tr></thead>';
  }
  
  // 구분선 행 스킵 (보통 두 번째 행)
  const dataStartIndex = processedRows.length > 1 && processedRows[1].every(cell => cell.match(/^-+$/)) ? 2 : 1;
  
  // 데이터 행들
  if (processedRows.length > dataStartIndex) {
    html += '<tbody>';
    for (let i = dataStartIndex; i < processedRows.length; i++) {
      html += '<tr>';
      processedRows[i].forEach(cell => {
        html += `<td style="border: 1px solid #d9d9d9; padding: 6px 12px; color: #595959; line-height: 1.4;">${cell}</td>`;
      });
      html += '</tr>';
    }
    html += '</tbody>';
  }
  
  html += '</table>';
  return html;
};

export const NodeExecutionResultPanel: React.FC = () => {
  const {
    nodes,
    isExecuting,
    executionResult,
    nodeExecutionStates,
    nodeStreamingOutputs,
    nodeExecutionResults,
    nodeStartOrder,
  } = useNodeWorkflowStore();

  // 노드 실행 시작 순서대로 정렬 (고정된 순서 유지)
  const getOrderedNodes = () => {
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
  };

  const orderedNodes = getOrderedNodes();

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
                {streamingOutput && executionState === 'executing' && (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 10, color: '#999', marginBottom: 4 }}>
                      실시간 출력:
                    </div>
                    <div style={{ 
                      padding: 8,
                      backgroundColor: '#f6f6f6',
                      border: '1px solid #d9d9d9',
                      borderRadius: 4,
                      maxHeight: 200,
                      overflow: 'auto'
                    }}>
                      <div 
                        style={{ 
                          margin: 0, 
                          fontSize: 11,
                          color: '#333',
                          lineHeight: 1.4
                        }}
                        dangerouslySetInnerHTML={{
                          __html: formatMarkdown(streamingOutput || '')
                        }}
                      />
                    </div>
                  </div>
                )}
                
                {/* 실행 결과 표시 */}
                {executionResult && (
                  <div style={{ fontSize: 11 }}>
                    {executionResult.success ? (
                      <div>
                        {/* 완료된 경우 최종 결과 표시 */}
                        {executionState === 'completed' && executionResult.description && (
                          <div>
                            {/* output-node의 경우 <output></output> 내의 내용만 추출하여 스크롤 가능하게 표시 */}
                            {node.node_type === 'output-node' ? (
                              (() => {
                                const outputMatch = executionResult.description?.match(/<output>([\s\S]*?)<\/output>/);
                                const outputContent = outputMatch ? outputMatch[1].trim() : executionResult.description;
                                
                                return (
                                  <div>
                                    <div style={{ 
                                      maxHeight: '300px', 
                                      overflowY: 'auto', 
                                      padding: '8px',
                                      border: '1px solid #d9d9d9',
                                      borderRadius: '4px',
                                      backgroundColor: '#fafafa'
                                    }}>
                                      <MarkdownWithDownload content={outputContent || ''} />
                                    </div>
                                  </div>
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
                                    <div style={{ 
                                      maxHeight: '300px', 
                                      overflowY: 'auto', 
                                      padding: '8px',
                                      border: '1px solid #d9d9d9',
                                      borderRadius: '4px',
                                      backgroundColor: isInputNode ? '#f0f8ff' : undefined
                                    }}>
                                      {content && content.trim() ? (
                                        <MarkdownWithDownload content={content} />
                                      ) : (
                                        <div style={{ 
                                          color: '#999', 
                                          fontStyle: 'italic',
                                          textAlign: 'center',
                                          padding: '20px'
                                        }}>
                                          {isInputNode ? '입력 노드에 내용이 설정되지 않았습니다.' : '출력 내용이 없습니다.'}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                );
                              })()
                            )}
                          </div>
                        )}
                      </div>
                    ) : (
                      <Text style={{ color: '#ff4d4f' }}>
                        {executionResult.error || ''}
                      </Text>
                    )}
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
};