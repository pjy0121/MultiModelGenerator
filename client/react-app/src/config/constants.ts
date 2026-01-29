// API related constants
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

// UI related constants
export const UI_CONFIG = {
  MESSAGE_DURATION: 3, // seconds
  MODAL_WIDTH: 800,
  REACT_FLOW: {
    BACKGROUND_COLOR: '#fafafa',
    FIT_VIEW_PADDING: 0.2,
  }
};

// Node related constants
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

  // Node type labels
  LABELS: {
    'input-node': 'Input Node',
    'generation-node': 'Generation Node',
    'ensemble-node': 'Ensemble Node',
    'validation-node': 'Validation Node',
    'output-node': 'Output Node',
    'context-node': 'Context Node'
  },

  // Search mode display mapping (result value helper)
  get SEARCH_INTENSITY_LABELS() {
    return {
      'exact': SEARCH_INTENSITY_CONFIG.exact.label,
      'standard': SEARCH_INTENSITY_CONFIG.standard.label,
      'comprehensive': SEARCH_INTENSITY_CONFIG.comprehensive.label
    };
  }
};

// BGE-M3 optimization settings (Token-based - single source of truth)
export const BGE_M3_CONFIG = {
  CHUNK_TOKENS: 512,          // Chunk size (tokens)
  OVERLAP_RATIO: 0.15,        // Overlap ratio
  CHARS_PER_TOKEN: 4,         // Average characters per token (for calculation)
  TOKENIZER_MODEL: 'BAAI/bge-m3',
  RERANK_MODEL: 'BAAI/bge-reranker-v2-m3',
  EMBEDDING_DIMENSION: 1024
};

// Search intensity settings (Top-K + Similarity Threshold)
// Threshold: Based on BGE-M3 actual similarity distribution (measured values in 0.2~0.4 range)
// - Theoretical recommended values (0.8/0.65/0.5) are too high in practice and filter out most results
// - Adjusted to practical values (0.3/0.2/0.1) to ensure appropriate search results
export const SEARCH_INTENSITY_CONFIG = {
  exact: {
    init: 10,
    final: 5,
    similarity_threshold: 0.3,
    label: 'Exact Search'
  },
  standard: {
    init: 20,
    final: 12,
    similarity_threshold: 0.2,
    label: 'Standard Search'
  },
  comprehensive: {
    init: 40,
    final: 25,
    similarity_threshold: 0.1,
    label: 'Comprehensive Search'
  }
};

// UI color constants
export const UI_COLORS = {
  // Edge colors
  EDGE: {
    SELECTED: '#1890ff',
    DEFAULT: '#b1b1b7'
  },

  // Panel colors
  PANEL: {
    HEADER_BACKGROUND: '#fff',
    HEADER_BORDER: '#eee',
    CONTENT_BACKGROUND: '#f6f6f6',
    BORDER: '#d9d9d9'
  },

  // Text colors
  TEXT: {
    MUTED: '#999',
    WARNING: '#ff8c00',
    SECONDARY: '#666',
    PRIMARY: '#333',
    DARK: '#262626'
  },

  // Interface colors
  UI: {
    INFO: '#1890ff',
    BACKGROUND_LIGHT: '#f5f5f5'
  }
};
