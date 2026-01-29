import React, { useState, useMemo, useCallback, memo, useRef, useEffect } from 'react';
import { Card, Typography, Alert, Button, Space, Modal } from 'antd';
import { FileExcelOutlined, FileTextOutlined, ExpandOutlined } from '@ant-design/icons';
import { useNodeWorkflowStore } from '../store/nodeWorkflowStore';
import { downloadUtils, getCurrentTimestamp } from '../utils/downloadUtils';
import { formatMarkdown } from '../utils/markdownUtils';

const { Title, Text } = Typography;

// Streaming output component (with auto-scroll feature)
interface StreamingOutputProps {
  output: string;
  isExecuting: boolean;
}

const StreamingOutput: React.FC<StreamingOutputProps> = memo(({ output, isExecuting }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const previousOutputLength = useRef<number>(0);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const userScrolledRef = useRef<boolean>(false); // Track if user manually scrolled
  const programmaticScrollRef = useRef<boolean>(false); // Track programmatic scroll
  const lastScrollTopRef = useRef<number>(0); // Track last scroll position

  // Detect if user changed scroll position (improved logic)
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;

    // Ignore if programmatic scroll
    if (programmaticScrollRef.current) {
      programmaticScrollRef.current = false;
      return;
    }

    const scrollElement = scrollRef.current;
    const currentScrollTop = scrollElement.scrollTop;
    const scrollHeight = scrollElement.scrollHeight;
    const clientHeight = scrollElement.clientHeight;
    const isAtBottom = currentScrollTop + clientHeight >= scrollHeight - 10; // Add more margin

    // Check if user scrolled up (precise detection)
    const scrolledUp = currentScrollTop < lastScrollTopRef.current - 5; // Ignore small changes
    const scrolledDown = currentScrollTop > lastScrollTopRef.current + 5;

    if (scrolledUp && autoScroll && isExecuting) {
      setAutoScroll(false);
      userScrolledRef.current = true;
    } else if (isAtBottom && !autoScroll) {
      // Re-enable auto-scroll if scrolled to bottom
      setAutoScroll(true);
      userScrolledRef.current = false;
    }

    // Update scroll position (prevent too frequent updates with debouncing)
    if (scrolledUp || scrolledDown) {
      lastScrollTopRef.current = currentScrollTop;
    }
  }, [autoScroll, isExecuting]);

  // Function to scroll programmatically
  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      programmaticScrollRef.current = true;
      const scrollElement = scrollRef.current;
      scrollElement.scrollTop = scrollElement.scrollHeight;
      lastScrollTopRef.current = scrollElement.scrollTop;
    }
  }, []);

  // Scroll to bottom when streaming output updates (only if auto-scroll is enabled)
  useEffect(() => {
    if (scrollRef.current && output && autoScroll && !userScrolledRef.current) {
      const currentOutputLength = output.length;

      // Scroll only when new content is added
      if (currentOutputLength > previousOutputLength.current) {
        // Scroll after DOM update using requestAnimationFrame
        requestAnimationFrame(() => {
          if (autoScroll && !userScrolledRef.current) {
            scrollToBottom();
          }
        });

        previousOutputLength.current = currentOutputLength;
      }
    }
  }, [output, autoScroll, scrollToBottom]);

  // Enable auto-scroll and reset state when execution starts
  useEffect(() => {
    if (isExecuting) {
      setAutoScroll(true);
      userScrolledRef.current = false;
      previousOutputLength.current = 0;
      lastScrollTopRef.current = 0;
      // Scroll to bottom when execution starts
      setTimeout(() => scrollToBottom(), 100);
    }
  }, [isExecuting, scrollToBottom]);

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
            console.log('Auto-scroll resume button clicked');
            setAutoScroll(true);
            userScrolledRef.current = false;
            // Scroll down immediately on click
            scrollToBottom();
          }}>
            ⏸️ Auto-scroll paused (click to resume)
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
          scrollBehavior: 'smooth', // Smooth all scrolling
          WebkitOverflowScrolling: 'touch' // Smooth scrolling on iOS
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

// Completed result display component (with auto-scroll feature)
interface CompletedResultDisplayProps {
  content: string;
  nodeType: string;
  isNewResult?: boolean; // Whether this is a newly completed result
}

const CompletedResultDisplay: React.FC<CompletedResultDisplayProps> = memo(({ content, nodeType, isNewResult = false }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom each time result is rendered
  useEffect(() => {
    if (scrollRef.current && content) {
      // Scroll after DOM is fully rendered
      const timer = setTimeout(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      }, isNewResult ? 200 : 100); // Add more delay for new results

      return () => clearTimeout(timer);
    }
  }, [content, isNewResult]);

  // Scroll once more after component mounts (handle late-loading content)
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
        scrollBehavior: 'auto' // Scroll immediately
      }}
    >
      <MarkdownWithDownload content={content} />
    </div>
  );
});

// Table download component
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
            Table download:
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
          View Larger
        </Button>
      </div>
      <Modal
        title={`View Larger (Table ${tableIndex + 1})`}
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

// Markdown renderer with download feature
interface MarkdownWithDownloadProps {
  content: string;
}

const MarkdownWithDownload: React.FC<MarkdownWithDownloadProps> = memo(({ content }) => {
  const renderContentWithDownload = useCallback(() => {
    if (!content) return null;

    // Check if table exists
    const hasTable = content.includes('|');

    // Use existing formatMarkdown if no table
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
          // Table ends - render table and download buttons together
          const table = renderTableWithDownload(tableLines, currentTableIndex++);
          if (table) elements.push(table);
          inTable = false;
          tableLines = [];
        }

        // Process normal text
        if (line.trim()) {
          elements.push(
            <div key={`text-${i}`} style={{ marginBottom: '8px' }}>
              <span dangerouslySetInnerHTML={{ __html: formatMarkdown(line) }} />
            </div>
          );
        } else {
          // Handle empty line
          elements.push(<div key={`empty-${i}`} style={{ height: '8px' }} />);
        }
      }
    }

    // Handle table at the end
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

    // Find and skip separator row
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

  // Track previous execution state to detect newly completed nodes
  const previousExecutionStates = useRef<Record<string, string>>({});
  const [newlyCompletedNodes, setNewlyCompletedNodes] = useState<Set<string>>(new Set());

  // Detect execution state changes
  useEffect(() => {
    const currentStates = { ...nodeExecutionStates };
    const newlyCompleted = new Set<string>();

    Object.keys(currentStates).forEach(nodeId => {
      const currentState = currentStates[nodeId];
      const previousState = previousExecutionStates.current[nodeId];

      // Newly completed if previous state was 'executing' and current state is 'completed'
      if (previousState === 'executing' && currentState === 'completed') {
        newlyCompleted.add(nodeId);
      }
    });

    if (newlyCompleted.size > 0) {
      setNewlyCompletedNodes(newlyCompleted);

      // Remove newly completed flag after a certain time
      const timer = setTimeout(() => {
        setNewlyCompletedNodes(new Set());
      }, 1000);

      return () => clearTimeout(timer);
    }

    previousExecutionStates.current = currentStates;
  }, [nodeExecutionStates]);

  // Sort by node execution start order (maintain fixed order) - optimized with memoization
  const orderedNodes = useMemo(() => {
    // Include only nodes with execution results or execution state set
    const startedNodes = nodes.filter(node => {
      const state = nodeExecutionStates[node.id];
      const hasResult = nodeExecutionResults[node.id];
      return hasResult || (state && state !== 'idle');
    });

    // Sort based on start order if available
    if (nodeStartOrder.length > 0) {
      const orderedNodes: any[] = [];

      // Place nodes according to start order
      nodeStartOrder.forEach(nodeId => {
        const node = startedNodes.find(n => n.id === nodeId);
        if (node) {
          orderedNodes.push(node);
        }
      });

      // Add remaining executed nodes not in start order (by ID)
      const remainingNodes = startedNodes
        .filter(node => !nodeStartOrder.includes(node.id))
        .sort((a, b) => a.id.localeCompare(b.id));

      return [...orderedNodes, ...remainingNodes];
    }

    // Simply sort by ID if no start order info
    return startedNodes.sort((a, b) => a.id.localeCompare(b.id));
  }, [nodes, nodeExecutionStates, nodeExecutionResults, nodeStartOrder]);

  return (
    <div style={{ padding: '16px', height: '100%' }}>
      <Title level={4} style={{ marginBottom: 16 }}>
        Execution Results
      </Title>

      {/* Executing indicator */}
      {isExecuting && (
        <Alert
          message="Workflow executing..."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Node execution results */}
      {orderedNodes.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {orderedNodes.map(node => {
            const executionState = nodeExecutionStates[node.id];
            const streamingOutput = nodeStreamingOutputs[node.id];
            const executionResult = nodeExecutionResults[node.id];

            const getStatusColor = () => {
              switch (executionState) {
                case 'executing': return '#ff4d4f'; // Red only for executing
                case 'completed': return '#52c41a';
                case 'error': return '#ff4d4f';
                default: return '#666';
              }
            };

            const getBorderColor = () => {
              // Red border only for executing node, default for others
              return executionState === 'executing' ? '#ff4d4f' : '#d9d9d9';
            };

            const getStatusText = () => {
              switch (executionState) {
                case 'executing': return 'Executing...';
                case 'completed': return 'Completed';
                case 'error': return 'Error';
                default: return 'Pending';
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
                {/* Streaming output (only shown while executing) */}
                {executionState === 'executing' && (
                  <StreamingOutput
                    output={streamingOutput || ''}
                    isExecuting={true}
                  />
                )}

                {/* Display execution result (only when completed) */}
                {executionResult && executionState === 'completed' && (
                  <div style={{ fontSize: 11 }}>
                    {executionResult.success ? (
                      <div>
                        {/* Show final result only when completed */}
                        {executionResult.description && (
                          <div>
                            {/* For output-node, extract content within <output></output> or <출력></출력> tags and display scrollably */}
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
                              // For input-node and general nodes, display full content scrollably
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
                                        📄 Input data content: {content ? `(${content.length} chars)` : '(no content)'}
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
                                        {isInputNode ? 'No content set in input node.' : 'No output content.'}
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
                        {executionResult.error || 'An unknown error occurred.'}
                      </Text>
                    )}
                  </div>
                )}

                {/* Display error state */}
                {executionState === 'error' && executionResult && (
                  <div style={{ fontSize: 11 }}>
                    <Text style={{ color: '#ff4d4f' }}>
                      {executionResult.error || 'An unknown error occurred.'}
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
          Workflow execution results will be displayed here.
        </div>
      )}

      {/* Overall execution result summary */}
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
              {executionResult.success ? 'Workflow execution completed!' : 'Workflow execution failed'}
            </Text>
          }
        >
          <Text style={{ fontSize: 12 }}>
            Total execution time: {(executionResult.total_execution_time || 0).toFixed(2)}s
          </Text>
          {executionResult.execution_order && executionResult.execution_order.length > 0 && (
            <>
              <br />
              <Text style={{ fontSize: 12 }}>
                Execution order: {executionResult.execution_order.map(nodeId => {
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
