import * as XLSX from 'xlsx';

// 현재 타임스탬프 생성
export const getCurrentTimestamp = (): string => {
  const now = new Date();
  return now.toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');
};

// 파일 다운로드 유틸리티 함수들
export const downloadUtils = {
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