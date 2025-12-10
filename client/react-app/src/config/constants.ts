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
  
  // 검색 모드 표시 매핑 (결과값 helper)
  get SEARCH_INTENSITY_LABELS() {
    return {
      'exact': SEARCH_INTENSITY_CONFIG.exact.label,
      'standard': SEARCH_INTENSITY_CONFIG.standard.label,
      'comprehensive': SEARCH_INTENSITY_CONFIG.comprehensive.label
    };
  }
};

// BGE-M3 최적화 설정 (Token 기반 - 단일 진실 공급원)
export const BGE_M3_CONFIG = {
  CHUNK_TOKENS: 512,          // 청크 크기 (tokens)
  OVERLAP_RATIO: 0.15,        // 오버랩 비율
  CHARS_PER_TOKEN: 4,         // 토큰당 평균 문자 수 (계산용)
  TOKENIZER_MODEL: 'BAAI/bge-m3',
  RERANK_MODEL: 'BAAI/bge-reranker-v2-m3',
  EMBEDDING_DIMENSION: 1024
};

// 검색 강도 설정 (Top-K + Similarity Threshold)
// 임계값: BGE-M3 실제 유사도 분포 기반 (실측값 0.2~0.4 범위)
// - 이론적 권장값(0.8/0.65/0.5)은 실제로는 너무 높아 대부분 필터링됨
// - 실용적 값(0.3/0.2/0.1)으로 조정하여 적절한 검색 결과 확보
export const SEARCH_INTENSITY_CONFIG = {
  exact: {
    init: 10,
    final: 5,
    similarity_threshold: 0.3,
    label: '정확 검색'
  },
  standard: {
    init: 20,
    final: 12,
    similarity_threshold: 0.2,
    label: '표준 검색'
  },
  comprehensive: {
    init: 40,
    final: 25,
    similarity_threshold: 0.1,
    label: '포괄 검색'
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