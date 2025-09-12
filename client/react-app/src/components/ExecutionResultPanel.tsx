import React from 'react';
import { Card, Typography } from 'antd';
import { useWorkflowStore } from '../store/workflowStore';

const { Text } = Typography;

// 강력한 테이블 전용 마크다운 렌더러
const MarkdownRenderer: React.FC<{ content: string }> = ({ content }) => {
  if (!content || content.trim() === '') {
    return <Text type="secondary">실행 결과가 없습니다.</Text>;
  }

  const renderContent = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactElement[] = [];
    let tableLines: string[] = [];
    let inTable = false;
    let key = 0;

    const renderTable = (tableData: string[]) => {
      if (tableData.length < 2) return null;
      
      // 개선된 테이블 파싱 - 셀 침범 방지
      const parseRow = (row: string) => {
        // 파이프로 분할하되, 이스케이프된 파이프는 보호
        let cells = row.split('|').map(cell => cell.trim());
        
        // 첫 번째와 마지막 빈 셀 제거
        if (cells.length > 2 && cells[0] === '' && cells[cells.length - 1] === '') {
          cells = cells.slice(1, -1);
        }
        
        // 빈 셀 필터링하되 최소 열 수는 보장
        const filteredCells = cells.filter(cell => cell !== '');
        return filteredCells.length > 0 ? filteredCells : cells;
      };

      const headerRow = parseRow(tableData[0]);
      const expectedColumnCount = headerRow.length;
      let dataRows: string[][] = [];
      
      // 구분선(---) 건너뛰고 데이터 행 추출
      for (let i = 1; i < tableData.length; i++) {
        const row = tableData[i];
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
          // 4열 이상일 때 (일반적인 요구사항 테이블)
          switch (colIndex) {
            case 0: return { width: '15%', minWidth: '80px' }; // ID
            case 1: return { width: '25%', minWidth: '120px' }; // 요구사항
            case 2: return { width: '20%', minWidth: '100px' }; // 문서 내 위치
            case 3: return { width: '40%', minWidth: '200px' }; // 상세 설명
            default: return { width: 'auto', minWidth: '100px' };
          }
        } else {
          // 3열 이하일 때는 균등 분배
          return { width: `${100/totalCols}%`, minWidth: '100px' };
        }
      };

      return (
        <table key={`exec-table-${key++}`} style={{
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
                {row.map((cell, cellIdx) => (
                  <td key={cellIdx} style={{
                    border: '1px solid #722ed1',
                    padding: '8px 12px',
                    verticalAlign: 'top',
                    backgroundColor: '#fff',
                    wordBreak: 'break-word',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    ...getColumnStyle(cellIdx, row.length)
                  }}>
                    <div style={{
                      maxHeight: cellIdx === 3 ? 'none' : '120px', // 상세 설명 열은 높이 제한 없음
                      overflow: cellIdx === 3 ? 'visible' : 'auto',
                      lineHeight: '1.4',
                      whiteSpace: 'pre-wrap'
                    }}>
                      {cell}
                    </div>
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
  const { layerResults } = useWorkflowStore();

  // 최종 요구사항 표만 추출하는 함수
  const extractFinalRequirementsTable = (content: string): string => {
    if (!content) return '';

    // 다양한 패턴으로 최종 요구사항 표 찾기
    const tablePatterns = [
      // "최종 요구사항 표:" 또는 "필터링된 요구사항 표:" 다음의 표
      /(?:\*\*(?:최종 요구사항 표|필터링된 요구사항 표|검증된 요구사항 표):\*\*)([\s\S]*?)(?=\*\*|$)/i,
      // 단순히 마크다운 표만 추출 (다른 텍스트 제외)
      /(\|[^|\n]*\|[\s\S]*?\|[^|\n]*\|)/g,
      // "요구사항" 키워드가 포함된 표
      /(\|[\s\S]*?요구사항[\s\S]*?\|[\s\S]*?\|)/gi
    ];

    for (const pattern of tablePatterns) {
      const match = content.match(pattern);
      if (match && match[1]) {
        const tableContent = match[1].trim();
        
        // 표가 실제로 요구사항 내용을 포함하는지 확인
        if (tableContent.includes('|') && tableContent.split('\n').length >= 3) {
          return `**최종 요구사항**\n\n${tableContent}`;
        }
      }
    }

    // 패턴으로 찾지 못한 경우, 마지막 완전한 표를 찾기
    const lines = content.split('\n');
    let tableStart = -1;
    let tableEnd = -1;
    
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i].trim();
      if (line.startsWith('|') && line.endsWith('|') && line.includes('요구사항')) {
        if (tableEnd === -1) tableEnd = i;
        tableStart = i;
        
        // 헤더 구분선 찾기
        if (i > 0 && lines[i-1].includes('---')) {
          tableStart = i - 2; // 헤더까지 포함
          break;
        }
      } else if (tableEnd !== -1 && line.startsWith('|') && line.endsWith('|')) {
        tableStart = i;
      } else if (tableEnd !== -1 && !line.startsWith('|')) {
        break;
      }
    }
    
    if (tableStart !== -1 && tableEnd !== -1) {
      const tableLines = lines.slice(tableStart, tableEnd + 1);
      const tableContent = tableLines.join('\n');
      return `**최종 요구사항**\n\n${tableContent}`;
    }

    // 그래도 찾지 못한 경우 원본 반환
    return content;
  };

  // 최종 결과는 서버에서 제공하는 final_result를 우선 사용
  const getFinalResult = (): string => {
    // 1. 서버에서 제공하는 final_result 우선 사용
    if (layerResults.validation && typeof layerResults.validation !== 'string' && layerResults.validation.final_result) {
      return layerResults.validation.final_result;
    }
    
    if (layerResults.ensemble && layerResults.ensemble.final_result) {
      return layerResults.ensemble.final_result;
    }
    
    if (layerResults.generation && layerResults.generation.final_result) {
      return layerResults.generation.final_result;
    }
    
    // 2. final_result가 없으면 기존 방식으로 fallback
    let rawResult = '';
    
    if (layerResults.validation) {
      if (typeof layerResults.validation === 'string') {
        rawResult = layerResults.validation;
      } else if (layerResults.validation.combined_result) {
        rawResult = layerResults.validation.combined_result;
      } else if (layerResults.validation.final_validated_result) {
        rawResult = layerResults.validation.final_validated_result;
      }
    }
    
    if (!rawResult && layerResults.ensemble?.combined_result) {
      rawResult = layerResults.ensemble.combined_result;
    }
    
    if (!rawResult && layerResults.generation?.combined_result) {
      rawResult = layerResults.generation.combined_result;
    }
    
    // 클라이언트에서 추출 (fallback 용도)
    return extractFinalRequirementsTable(rawResult);
  };

  const finalResult = getFinalResult();

  return (
    <Card 
      title="실행 결과" 
      size="small"
      style={{ 
        height: '100%',
        border: '1px solid #d9d9d9'
      }}
      bodyStyle={{ 
        padding: '12px', 
        height: 'calc(100% - 57px)',
        overflow: 'hidden'
      }}
    >
      <div style={{
        height: 'calc(100% - 24px)',
        overflow: 'auto'
      }}>
        <MarkdownRenderer content={finalResult} />
      </div>
    </Card>
  );
};

export default ExecutionResultPanel;
