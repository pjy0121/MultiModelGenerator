// API 관련 상수
export const API_CONFIG = {
  BASE_URL: 'http://localhost:5001',
  ENDPOINTS: {
    EXECUTE_WORKFLOW_STREAM: '/execute-workflow-stream',
    STOP_WORKFLOW: '/stop-workflow',
    VALIDATE_WORKFLOW: '/validate-workflow',
    KNOWLEDGE_BASES: '/knowledge-bases',
    SEARCH_KNOWLEDGE_BASE: '/search-knowledge-base',
    AVAILABLE_MODELS: '/available-models',
  }
};

// UI 관련 상수
export const UI_CONFIG = {
  MESSAGE_DURATION: 3, // 초
  MODAL_WIDTH: 800,
  REACT_FLOW: {
    BACKGROUND_COLOR: '#fafafa',
    FIT_VIEW_PADDING: 0.2,
  }
};

// 노드 관련 상수
export const NODE_CONFIG = {
  COLORS: {
    'input-node': { background: '#e6f7ff', border: '#1890ff', tag: 'blue' },
    'generation-node': { background: '#f6ffed', border: '#52c41a', tag: 'green' },
    'ensemble-node': { background: '#f9f0ff', border: '#722ed1', tag: 'purple' },
    'validation-node': { background: '#fff7e6', border: '#fa8c16', tag: 'orange' },
    'context-node': { background: '#f0f5ff', border: '#2f54eb', tag: 'blue' },
    'output-node': { background: '#fff1f0', border: '#ff4d4f', tag: 'red' },
    default: { background: '#f5f5f5', border: '#d9d9d9', tag: 'default' }
  },
  
  // 노드 타입별 한국어 라벨
  LABELS: {
    'input-node': '입력 노드',
    'generation-node': '생성 노드', 
    'ensemble-node': '앙상블 노드',
    'validation-node': '검증 노드',
    'output-node': '출력 노드',
    'context-node': '컨텍스트 노드'
  },
  
  // 검색 모드 표시 매핑
  SEARCH_INTENSITY_LABELS: {
    'exact': '정확 검색',
    'standard': '표준 검색',
    'comprehensive': '포괄 검색'
  }
};

// UI 색상 상수
export const UI_COLORS = {
  // Edge 색상
  EDGE: {
    SELECTED: '#1890ff',
    DEFAULT: '#b1b1b7'
  },
  
  // 패널 색상
  PANEL: {
    HEADER_BACKGROUND: '#fff',
    HEADER_BORDER: '#eee',
    CONTENT_BACKGROUND: '#f6f6f6',
    BORDER: '#d9d9d9'
  },
  
  // 텍스트 색상
  TEXT: {
    MUTED: '#999',
    WARNING: '#ff8c00',
    SECONDARY: '#666',
    PRIMARY: '#333',
    DARK: '#262626'
  },
  
  // 인터페이스 색상
  UI: {
    INFO: '#1890ff',
    BACKGROUND_LIGHT: '#f5f5f5'
  }
};