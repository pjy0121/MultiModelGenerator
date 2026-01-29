import * as XLSX from 'xlsx';

// Generate current timestamp
export const getCurrentTimestamp = (): string => {
  const now = new Date();
  return now.toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');
};

// File download utility functions
export const downloadUtils = {
  // Create and download Excel file
  downloadExcel: (headerRow: string[], dataRows: string[][], filename: string) => {
    // Combine header and data into one array
    const wsData = [headerRow, ...dataRows];

    // Create worksheet
    const ws = XLSX.utils.aoa_to_sheet(wsData);

    // Create workbook
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Data');

    // Auto-adjust column widths
    const colWidths = headerRow.map((_, colIndex) => {
      const maxLength = Math.max(
        headerRow[colIndex]?.length || 0,
        ...dataRows.map(row => row[colIndex]?.length || 0)
      );
      return { width: Math.min(Math.max(maxLength + 2, 10), 50) };
    });
    ws['!cols'] = colWidths;

    // Download file
    XLSX.writeFile(wb, filename);
  },

  // Create TXT file (tab-separated)
  tableToTXT: (headerRow: string[], dataRows: string[][]): string => {
    const allRows = [headerRow, ...dataRows];
    return allRows.map(row => row.join('\t')).join('\n');
  },

  // Create markdown table
  tableToMarkdown: (headerRow: string[], dataRows: string[][]): string => {
    const headerLine = '| ' + headerRow.join(' | ') + ' |';
    const separatorLine = '| ' + headerRow.map(() => '---').join(' | ') + ' |';
    const dataLines = dataRows.map(row => '| ' + row.join(' | ') + ' |');

    return [headerLine, separatorLine, ...dataLines].join('\n');
  },

  // Download file
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
