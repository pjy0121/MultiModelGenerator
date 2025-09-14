import React from 'react';
import { Typography, Button, Space } from 'antd';
import { FileExcelOutlined, FileTextOutlined } from '@ant-design/icons';
import * as XLSX from 'xlsx';
import { useWorkflowStore } from '../store/workflowStore';

const { Text } = Typography;

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
    XLSX.utils.book_append_sheet(wb, ws, '요구사항');
    
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

  // TSV (Tab-Separated Values) 형식으로 변환
  tableToTSV: (headerRow: string[], dataRows: string[][]) => {
    const escapeTsvCell = (cell: string) => {
      return cell.replace(/\t/g, ' ').replace(/\n/g, ' ').replace(/\r/g, ' ');
    };

    const tsvHeader = headerRow.map(escapeTsvCell).join('\t');
    const tsvData = dataRows.map(row => 
      row.map(escapeTsvCell).join('\t')
    ).join('\n');
    
    return `${tsvHeader}\n${tsvData}`;
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

// 다운로드 버튼 컴포넌트
const TableDownloadButtons: React.FC<{
  headerRow: string[];
  dataRows: string[][];
  tableIndex: number;
}> = ({ headerRow, dataRows, tableIndex }) => {
  const getCurrentTimestamp = () => {
    const now = new Date();
    return now.toISOString().replace(/[:.]/g, '-').slice(0, 19);
  };

  const handleDownloadExcel = () => {
    const filename = `requirements_table_${tableIndex + 1}_${getCurrentTimestamp()}.xlsx`;
    downloadUtils.downloadExcel(headerRow, dataRows, filename);
  };

  const handleDownloadTSV = () => {
    const tsvContent = downloadUtils.tableToTSV(headerRow, dataRows);
    const filename = `requirements_table_${tableIndex + 1}_${getCurrentTimestamp()}.txt`;
    downloadUtils.downloadFile(tsvContent, filename, 'text/plain;charset=utf-8;');
  };

  return (
    <div style={{ 
      margin: '8px 0',
      padding: '8px',
      backgroundColor: '#f8f9fa',
      borderRadius: '4px',
      border: '1px solid #e9ecef'
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
          onClick={handleDownloadTSV}
          style={{ padding: '2px 8px', height: 'auto', fontSize: '11px' }}
        >
          텍스트
        </Button>
      </Space>
    </div>
  );
};

// 강력한 테이블 전용 마크다운 렌더러
const MarkdownRenderer: React.FC<{ content: string }> = ({ content }) => {
  if (!content || content.trim() === '') {
    return <Text type="secondary">실행 결과가 없습니다.</Text>;
  }

  const renderContent = (text: string) => {
    // \\n을 실제 줄바꿈으로 변환
    const normalizedText = text.replace(/\\n/g, '\n');
    const lines = normalizedText.split('\n');
    const elements: React.ReactElement[] = [];
    let tableLines: string[] = [];
    let inTable = false;
    let key = 0;

    const renderTable = (tableData: string[]) => {
      if (tableData.length < 2) return null;
      
      // 개선된 테이블 파싱 - 셀 침범 방지 및 줄바꿈 처리
      const parseRow = (row: string) => {
        // \\n을 실제 줄바꿈으로 변환
        const normalizedRow = row.replace(/\\n/g, '\n');
        
        // 파이프로 분할하되, 이스케이프된 파이프는 보호
        let cells = normalizedRow.split('|').map(cell => cell.trim());
        
        // 첫 번째와 마지막 빈 셀 제거
        if (cells.length > 2 && cells[0] === '' && cells[cells.length - 1] === '') {
          cells = cells.slice(1, -1);
        }
        
        // 빈 셀 필터링하되 최소 열 수는 보장
        const filteredCells = cells.filter(cell => cell !== '');
        return filteredCells.length > 0 ? filteredCells : cells;
      };

      // 모든 테이블 행에서 \\n을 실제 줄바꿈으로 변환
      const normalizedTableData = tableData.map(row => row.replace(/\\n/g, '\n'));
      
      const headerRow = parseRow(normalizedTableData[0]);
      const expectedColumnCount = headerRow.length;
      let dataRows: string[][] = [];
      
      // 구분선(---) 건너뛰고 데이터 행 추출
      for (let i = 1; i < normalizedTableData.length; i++) {
        const row = normalizedTableData[i];
        if (row.includes('---') || row.includes('===')) continue;
        
        const parsedRow = parseRow(row);
        if (parsedRow.length > 0) {
          // 열 수 정규화 - 부족하면 빈 셀 추가, 넘치면 마지막 셀에 병합
          if (parsedRow.length < expectedColumnCount) {
            // 부족한 열은 빈 문자열로 채움
            while (parsedRow.length < expectedColumnCount) {
              parsedRow.push('');
            }
          } else if (parsedRow.length > expectedColumnCount) {
            // 넘치는 내용은 마지막 열에 병합
            const extraContent = parsedRow.slice(expectedColumnCount - 1).join(' | ');
            parsedRow.splice(expectedColumnCount - 1, parsedRow.length - expectedColumnCount + 1, extraContent);
          }
          dataRows.push(parsedRow);
        }
      }

      if (headerRow.length === 0 || dataRows.length === 0) return null;

      // 열 너비 계산 - 요구사항 테이블 특화
      const getColumnStyle = (colIndex: number, totalCols: number) => {
        if (totalCols >= 4) {
          // 4열일 때 (검증 상태 포함된 요구사항 테이블)
          switch (colIndex) {
            case 0: return { width: '15%', minWidth: '80px' }; // ID
            case 1: return { width: '40%', minWidth: '180px' }; // 요구사항
            case 2: return { width: '25%', minWidth: '120px' }; // 근거
            case 3: return { width: '20%', minWidth: '100px' }; // 검증 상태
            default: return { width: 'auto', minWidth: '80px' };
          }
        } else if (totalCols >= 3) {
          // 3열일 때 (상세설명 없는 Generation Layer)
          switch (colIndex) {
            case 0: return { width: '15%', minWidth: '80px' }; // ID
            case 1: return { width: '50%', minWidth: '200px' }; // 요구사항
            case 2: return { width: '35%', minWidth: '150px' }; // 근거
            default: return { width: 'auto', minWidth: '100px' };
          }
        } else {
          // 2열 이하일 때는 균등 분배
          return { width: `${100/totalCols}%`, minWidth: '100px' };
        }
      };

      return (
        <div key={`table-container-${key++}`}>
          {/* 다운로드 버튼 */}
          <TableDownloadButtons 
            headerRow={headerRow} 
            dataRows={dataRows} 
            tableIndex={key} 
          />
          
          {/* 테이블 */}
          <table style={{
            borderCollapse: 'collapse',
            width: '100%',
            fontSize: '12px',
            border: '2px solid #722ed1',
            marginBottom: '16px',
            backgroundColor: '#fff',
            tableLayout: 'fixed' // 고정 레이아웃으로 열 너비 강제
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
                  color: '#722ed1',
                  wordBreak: 'break-word',
                  overflow: 'hidden',
                  ...getColumnStyle(idx, headerRow.length)
                }}>
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {row.map((cell, cellIdx) => {
                  // 검증 상태 컬럼인지 확인 (4번째 컬럼이고 4개 컬럼 테이블일 때)
                  const isValidationStatusColumn = row.length >= 4 && cellIdx === 3;
                  
                  // 검증 상태에 따른 스타일링
                  const getValidationCellStyle = (status: string) => {
                    const normalizedStatus = status.toLowerCase().trim();
                    switch (normalizedStatus) {
                      case 'pass':
                      case '통과':
                        return { backgroundColor: '#f6ffed', color: '#52c41a', fontWeight: 'bold' };
                      case 'fail':
                      case '실패':
                        return { backgroundColor: '#fff2f0', color: '#ff4d4f', fontWeight: 'bold' };
                      case 'unchecked':
                      case '확인 필요':
                        return { backgroundColor: '#fff7e6', color: '#fa8c16', fontWeight: 'bold' };
                      case 'duplicated':
                      case '중복':
                        return { backgroundColor: '#f9f0ff', color: '#722ed1', fontWeight: 'bold' };
                      default:
                        return {};
                    }
                  };

                  const validationStyle = isValidationStatusColumn ? getValidationCellStyle(cell) : {};

                  return (
                    <td key={cellIdx} style={{
                      border: '1px solid #722ed1',
                      padding: '8px 12px',
                      verticalAlign: 'top',
                      backgroundColor: '#fff',
                      wordBreak: 'break-word',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      ...getColumnStyle(cellIdx, row.length),
                      ...validationStyle
                    }}>
                      <div style={{
                        maxHeight: cellIdx === 1 ? 'none' : '120px', // 요구사항 열은 높이 제한 없음
                        overflow: cellIdx === 1 ? 'visible' : 'auto',
                        lineHeight: '1.4',
                        whiteSpace: 'pre-wrap'
                      }}>
                        {isValidationStatusColumn ? (
                          <div style={{ textAlign: 'center', fontSize: '11px' }}>
                            {cell}
                          </div>
                        ) : (
                          cell
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      );
    };

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
                fontSize: '16px',
                color: '#722ed1',
                margin: '16px 0 8px 0'
              }}>
                {line.replace(/\*\*/g, '')}
              </div>
            );
          } else if (line.startsWith('###')) {
            elements.push(
              <div key={`h3-${key++}`} style={{
                fontWeight: 'bold',
                fontSize: '14px',
                color: '#722ed1',
                margin: '12px 0 6px 0'
              }}>
                {line.replace(/^###\s*/, '')}
              </div>
            );
          } else if (line.startsWith('##')) {
            elements.push(
              <div key={`h2-${key++}`} style={{
                fontWeight: 'bold',
                fontSize: '15px',
                color: '#722ed1',
                margin: '14px 0 8px 0'
              }}>
                {line.replace(/^##\s*/, '')}
              </div>
            );
          } else if (line.startsWith('#')) {
            elements.push(
              <div key={`h1-${key++}`} style={{
                fontWeight: 'bold',
                fontSize: '16px',
                color: '#722ed1',
                margin: '16px 0 8px 0'
              }}>
                {line.replace(/^#\s*/, '')}
              </div>
            );
          } else {
            elements.push(
              <div key={`text-${key++}`} style={{
                margin: '4px 0',
                lineHeight: '1.6'
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

    return elements;
  };

  return (
    <div style={{ fontSize: '13px', lineHeight: '1.5' }}>
      {renderContent(content)}
    </div>
  );
};

const ExecutionResultPanel: React.FC = () => {
  // 실시간 상태 구독을 위해 useWorkflowStore 사용
  const { layerResults, layerInputs, currentExecution } = useWorkflowStore();
  
  // 실행 결과 - 최근 실행된 layer의 forward_data만 표시
  const getExecutionResult = (): { content: string; layerType: string | null } => {
    // 0. 오류 상태 확인
    if (currentExecution?.status === 'error' && currentExecution.error) {
      return { 
        content: `❌ **워크플로우 실행 오류**\n\n${currentExecution.error}\n\n다시 시도해주세요.`, 
        layerType: 'Error' 
      };
    }
    
    // 개별 레이어 실행 후에는 해당 레이어의 결과를 최우선으로 표시
    // 전체 워크플로우 실행 중이 아닐 때는 가장 최근 실행된 레이어의 결과를 표시
    const isStepwiseExecution = currentExecution !== null;
    
    // 가장 마지막에 실행된 layer의 forward_data 추출
    const getLastLayerInput = () => {
      // 개별 실행 시에는 결과가 있는 레이어 중 가장 최근 것을 우선
      if (!isStepwiseExecution) {
        // Validation Layer 개별 실행 결과가 있으면 우선 표시
        if (layerResults.validation) {
          const validationResult = layerResults.validation;
          const forwardData = validationResult.node_outputs?.forward_data || '';
          if (forwardData.trim()) {
            return { content: forwardData, layerType: 'Validation' };
          }
        }
        
        // Ensemble Layer 개별 실행 결과가 있으면 표시
        if (layerResults.ensemble) {
          const ensembleResult = layerResults.ensemble;
          const forwardData = ensembleResult.node_outputs?.forward_data || '';
          if (forwardData.trim()) {
            return { content: forwardData, layerType: 'Ensemble' };
          }
        }
        
        // Generation Layer 개별 실행 결과가 있으면 표시
        if (layerResults.generation) {
          const generationResult = layerResults.generation;
          const forwardData = generationResult.node_outputs?.forward_data || '';
          if (forwardData.trim()) {
            return { content: forwardData, layerType: 'Generation' };
          }
        }
      } else {
        // 전체 워크플로우 실행 중일 때는 기존 로직 사용
        
        // 1. Validation Layer 완료 시 - 최종 결과
        if (layerResults.validation) {
          const validationResult = layerResults.validation;
          const forwardData = validationResult.node_outputs?.forward_data || '';
          if (forwardData.trim()) {
            return { content: forwardData, layerType: 'Validation' };
          }
        }
        
        // 2. Ensemble Layer 완료 시 - Validation Layer input 표시 (있는 경우) 또는 Ensemble 결과 직접 표시
        if (layerResults.ensemble) {
          if (layerInputs.validation) {
            // Validation Layer가 있는 경우: Validation Layer input 표시
            return { content: layerInputs.validation, layerType: 'Ensemble' };
          } else {
            // Validation Layer가 없는 경우: Ensemble Layer의 forward_data 직접 표시
            const ensembleResult = layerResults.ensemble;
            const forwardData = ensembleResult.node_outputs?.forward_data || '';
            if (forwardData.trim()) {
              return { content: forwardData, layerType: 'Ensemble' };
            }
          }
        }
        
        // 3. Generation Layer 완료 시 - Generation Layer의 forward_data 표시
        if (layerResults.generation) {
          const generationResult = layerResults.generation;
          const forwardData = generationResult.node_outputs?.forward_data || '';
          if (forwardData.trim()) {
            return { content: forwardData, layerType: 'Generation' };
          }
          // forward_data가 없거나 비어있다면 ensemble input 확인
          if (layerInputs.ensemble) {
            return { content: layerInputs.ensemble, layerType: 'Generation' };
          }
        }
      }
      
      return { content: '', layerType: null };
    };
    
    const lastLayerResult = getLastLayerInput();
    
    if (lastLayerResult.content) {
      return lastLayerResult;
    } else if (!layerResults.generation && !layerResults.ensemble && !layerResults.validation) {
      return { content: '👆 워크플로우를 실행해주세요.', layerType: null };
    } else {
      return { content: '실행 중이거나 결과를 처리하는 중입니다...', layerType: null };
    }
  };

  const executionResult = getExecutionResult();

  return (
    <div style={{
      height: '100%',
      padding: '12px',
      overflow: 'auto',
      border: '1px solid #d9d9d9',
      borderRadius: '6px',
      backgroundColor: '#fff'
    }}>
      <div style={{
        marginBottom: '8px',
        fontWeight: 'bold',
        fontSize: '14px',
        color: '#722ed1'
      }}>
        실행 결과{executionResult.layerType ? ` (${executionResult.layerType} Layer)` : ''}
      </div>
      <div style={{
        height: 'calc(100% - 32px)',
        overflow: 'auto'
      }}>
        <MarkdownRenderer content={executionResult.content} />
      </div>
    </div>
  );
};

export default ExecutionResultPanel;
