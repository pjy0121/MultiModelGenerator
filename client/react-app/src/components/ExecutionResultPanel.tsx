import React from 'react';
import { Card, Typography } from 'antd';
import { useWorkflowStore } from '../store/workflowStore';
import ReactMarkdown from 'react-markdown';

const { Text } = Typography;

// 강화된 Markdown 렌더러 - 테이블을 명확하게 렌더링
const MarkdownRenderer: React.FC<{ content: string }> = ({ content }) => {
  // 빈 내용이나 undefined인 경우 처리
  if (!content || content.trim() === '') {
    return <Text type="secondary">실행 결과가 없습니다.</Text>;
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
            <strong style={{ color: '#1890ff', fontWeight: 'bold' }}>
              {children}
            </strong>
          ),
          code: ({ children }) => (
            <code style={{ 
              backgroundColor: '#f0f0f0', 
              padding: '2px 6px', 
              borderRadius: '3px',
              fontSize: '11px',
              border: '1px solid #d9d9d9',
              color: '#d4380d'
            }}>
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '12px', 
              borderRadius: '4px',
              border: '1px solid #d9d9d9',
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

export const ExecutionResultPanel: React.FC = () => {
  const { layerResults } = useWorkflowStore();

  // 통과한 요구사항 표만 추출하는 함수
  const extractPassedRequirements = (content: string): string => {
    if (!content) return '';

    // "필터링된 요구사항 목록 (통과):" 또는 "검증된 요구사항 표:" 부분 찾기
    const passedSectionRegex = /(?:\*\*필터링된 요구사항 목록 \(통과\):\*\*|\*\*검증된 요구사항 표:\*\*)([\s\S]*?)(?:\*\*(?:제거된 요구사항|필터링 결과|검증 과정)|$)/i;
    const match = content.match(passedSectionRegex);
    
    if (match && match[1]) {
      const passedContent = match[1].trim();
      
      // 테이블이 있는지 확인
      if (passedContent.includes('|')) {
        return `**통과한 요구사항:**\n\n${passedContent}`;
      }
    }
    
    // 매칭되지 않으면 원본 반환
    return content;
  };

  // 최종 결과 찾기 (Validation Layer 결과 우선)
  const getFinalResult = (): string => {
    // Validation Layer 결과가 있으면 그것을 사용하고 통과 부분만 추출
    if (layerResults.validation && 'final_validated_result' in layerResults.validation) {
      const fullResult = (layerResults.validation as any).final_validated_result || '';
      return extractPassedRequirements(fullResult);
    }
    
    // Validation Layer가 없으면 Ensemble 결과 사용 (전체)
    if (layerResults.ensemble && layerResults.ensemble.combined_result) {
      return layerResults.ensemble.combined_result;
    }
    
    // Ensemble도 없으면 Generation 결과 사용 (전체)
    if (layerResults.generation && layerResults.generation.combined_result) {
      return layerResults.generation.combined_result;
    }
    
    return '';
  };

  const finalResult = getFinalResult();

  return (
    <Card 
      title={
        <span style={{ color: '#52c41a' }}>
          🎯 실행 결과
        </span>
      } 
      size="small"
      style={{ height: '100%' }}
    >
      <div style={{ 
        padding: 12, 
        backgroundColor: finalResult ? '#f6ffed' : '#fafafa', 
        border: `1px solid ${finalResult ? '#b7eb8f' : '#d9d9d9'}`, 
        borderRadius: 4,
        height: 'calc(100% - 24px)',
        overflow: 'auto'
      }}>
        <MarkdownRenderer content={finalResult} />
      </div>
    </Card>
  );
};

export default ExecutionResultPanel;
