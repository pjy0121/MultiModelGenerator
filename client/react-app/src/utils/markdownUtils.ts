// 간단한 마크다운 포맷팅 함수
export const formatMarkdown = (text: string): string => {
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
export const formatTables = (text: string): string => {
  const lines = text.split('\n');
  let result: string[] = [];
  let inTable = false;
  let tableRows: string[] = [];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const isTableLine = line.includes('|') && line.trim().length > 0;
    
    if (isTableLine) {
      if (!inTable) {
        inTable = true;
        tableRows = [];
      }
      tableRows.push(line);
    } else {
      if (inTable) {
        // 테이블 종료 - HTML 테이블로 변환
        const tableHtml = convertToHtmlTable(tableRows);
        result.push(tableHtml);
        inTable = false;
        tableRows = [];
      }
      
      if (line.trim().length > 0) {
        result.push(line);
      }
    }
  }
  
  // 마지막이 테이블이었다면 처리
  if (inTable && tableRows.length > 0) {
    const tableHtml = convertToHtmlTable(tableRows);
    result.push(tableHtml);
  }
  
  return result.join('\n');
};

// 마크다운 테이블을 HTML 테이블로 변환
const convertToHtmlTable = (tableRows: string[]): string => {
  if (tableRows.length < 2) return tableRows.join('\n');
  
  let html = '<table style="border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 11px; border: 1px solid #d9d9d9;">';
  
  for (let i = 0; i < tableRows.length; i++) {
    const row = tableRows[i];
    const cells = row.split('|').map(cell => cell.trim()).filter(cell => cell.length > 0);
    
    if (i === 1 && cells.every(cell => cell.match(/^[-:]+$/))) {
      // 구분자 행은 건너뜀
      continue;
    }
    
    const isHeader = i === 0;
    const tag = isHeader ? 'th' : 'td';
    const style = isHeader 
      ? 'border: 1px solid #d9d9d9; padding: 8px; background: #f5f5f5; font-weight: 600; text-align: left;'
      : 'border: 1px solid #d9d9d9; padding: 8px; vertical-align: top;';
    
    html += '<tr>';
    cells.forEach(cell => {
      html += `<${tag} style="${style}">${cell}</${tag}>`;
    });
    html += '</tr>';
  }
  
  html += '</table>';
  return html;
};