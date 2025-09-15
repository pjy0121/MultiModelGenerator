# MultiModelGenerator AI Coding Instructions

## Project Overview
This is a **multi-layer LLM workflow system** that extracts requirements from specification documents using RAG (Retrieval-Augmented Generation) and multiple AI models. The architecture consists of a **FastAPI backend** with LangChain integration and a **React + TypeScript frontend** with visual workflow editing.

## Core Architecture

### Three-Layer Workflow System
- **Generation Layer**: Multiple LLM nodes generate requirements from retrieved document chunks
- **Ensemble Layer**: Combines and reconciles outputs from generation nodes  
- **Validation Layer**: Validates and scores the final consolidated requirements

### Backend Structure (`/server`)
- **Entry Point**: `main.py` - Uvicorn server on port 5001
- **API Layer**: `src/api/api_server.py` - FastAPI endpoints with CORS enabled
- **Execution Engines**: 
  - `src/api/layer_executors.py` - Layer-specific execution logic
  - `src/api/chain_executors.py` - LangChain-based workflow chains
- **Core Models**: `src/core/models.py` - Pydantic models for requests/responses
- **Vector Storage**: `src/services/vector_store.py` - ChromaDB for document chunks
- **LLM Integration**: `src/services/langchain_llm_factory.py` - Multi-provider LLM factory

### Frontend Structure (`/client/react-app`)
- **State Management**: `src/store/workflowStore.ts` - Zustand store for workflow state
- **Visual Editor**: `src/components/WorkflowCanvas.tsx` - React Flow-based node editor
- **Node Types**: CustomNode (workflow nodes) and PlaceholderNode (layer placeholders)
- **API Client**: `src/services/api.ts` - Axios-based backend communication

## Development Workflows

### Server Development
```bash
cd server
pip install -r requirements.txt
python main.py  # Starts on http://localhost:5001
```

### Client Development  
```bash
cd client/react-app
npm install
npm run dev  # Starts on http://localhost:5173
```

### Knowledge Base Management
```bash
# From server directory
python -m src.admin.admin list                    # List knowledge bases
python -m src.admin.admin build <name> <pdf_path> # Build from PDF
python -m src.admin.admin delete <name>           # Delete knowledge base
```

## Critical Patterns

### LangChain Integration
- **Output Parsing**: Use `src/langchain_parsers/output_parsers.py` for structured LLM outputs
- **Chain Execution**: Layer executors use LangChain LCEL (LangChain Expression Language)
- **Model Factory**: `LangChainLLMFactory.get_llm_by_model_id()` for multi-provider LLM access

### State Management (Frontend)
- **Workflow Store**: Central Zustand store in `workflowStore.ts`
- **Node Updates**: Use `updateNode()` for node modifications
- **Execution Tracking**: `isExecuting` flag prevents concurrent workflow runs

### API Communication
- **Stepwise Execution**: `/search-context`, `/execute-layer-prompt` endpoints for granular control
- **Workflow Execution**: `/execute-workflow` for full pipeline execution
- **Model Management**: `/models/available` for dynamic model selection

### Error Handling
- **LangChain Fallbacks**: `layer_executors.py` includes fallback parsing for malformed LLM outputs
- **Frontend Resilience**: API errors are caught and displayed via Ant Design notifications
- **Vector Store**: Graceful handling of missing knowledge bases

## File Naming Conventions
- **Backend**: Snake_case for Python modules (`layer_executors.py`)
- **Frontend**: PascalCase for React components (`WorkflowCanvas.tsx`)
- **Types**: Shared interfaces in `src/types/index.ts` with enum definitions

## Testing & Debugging
- **API Testing**: FastAPI auto-docs at `http://localhost:5001/docs`
- **Frontend DevTools**: React Flow devtools for node debugging
- **Logs**: Server logs show LangChain execution details and vector search results

## Environment Setup
- **Required**: `.env` file in `/server` with `OPENAI_API_KEY` and `GOOGLE_API_KEY`
- **Dependencies**: ChromaDB for vector storage, LangChain for LLM orchestration
- **Ports**: Server (5001), Client (5173), ensure no conflicts

## Common Tasks
- **Adding New LLM Providers**: Extend `LangChainLLMFactory` and update `Config.SUPPORTED_LLM_PROVIDERS`
- **New Layer Types**: Add to `LayerType` enum in both frontend/backend, implement in layer executors
- **Node Customization**: Modify `CustomNode.tsx` and corresponding backend execution logic
- **Prompt Engineering**: Default prompts in `client/react-app/src/config/defaultPrompts.ts`