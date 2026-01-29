# MultiModelGenerator Copilot Instructions

## Project Overview
Multi-model AI system for requirements extraction from technical documents using a node-based workflow architecture. Supports 5 node types connected in directed graphs: input → generation → ensemble → validation → output + context nodes for RAG integration.

**Tech Stack**: Python/FastAPI backend (uvicorn on :5001), React 19/TypeScript frontend (Vite dev server on :5173), ChromaDB for vector storage, Zustand for state management.

## Architecture Patterns

### Node-Based Workflow System (5 Core Types)
- **Input Nodes**: Plain-text content sources (no pre-nodes, multiple post-nodes allowed)
- **Generation Nodes**: LLM-powered initial requirement generation (input-node → generation-node)
- **Ensemble Nodes**: Combines multiple pre-node outputs (multiple pre-nodes → single output)
- **Validation Nodes**: Sequential validation/refinement of requirements (can chain: validation → validation)
- **Output Nodes**: Final result display (no post-nodes, single instance per workflow)
- **Context Nodes**: RAG integration with ChromaDB knowledge bases (must have input-node as pre-node)

### Critical Connection Rules (Enforced by `workflow_validator.py`)
- Only ensemble-nodes can have multiple pre-nodes
- Only input-nodes and context-nodes can have multiple post-nodes  
- Context-nodes MUST have input-node as pre-node (fails validation otherwise)
- All nodes need pre/post connections except input (no pre) and output (no post)
- Validation-node → validation-node chains are explicitly allowed
- Workflow requires exactly one output-node (enforced by validator)

### Real-Time Streaming Execution
Server-side async streaming with dependency resolution in `node_execution_engine.py`:
```python
# Event-driven parallel execution with real-time updates via SSE
for chunk in response_stream:
    if chunk.type == 'node_start': # Node begins execution
    elif chunk.type == 'stream':   # Real-time LLM token streaming  
    elif chunk.type == 'node_complete': # Node finished
    elif chunk.type == 'complete': # Workflow finished
```

**SSE Transport** (Server-Sent Events in `api_server.py`):
- Backend: `StreamingResponse` with `Content-Type: text/event-stream`
- Frontend: Native `fetch()` with `ReadableStream` parsing (not EventSource)
- Format: `data: {json}\n\n` (SSE standard, parsed line-by-line in `api.ts`)

**Execution Algorithm** (from `node_execution_engine.py`):
1. Find all input-nodes, add to execution queue
2. Execute nodes in parallel when all pre-nodes complete (check via `completed_nodes` set)
3. On completion, register post-nodes to queue
4. Repeat until queue empty or `is_stopping` flag set

Frontend receives real-time updates via `nodeWorkflowStore.ts` managing:
- `nodeExecutionStates`: Track 'idle' | 'executing' | 'completed' | 'error'
- `nodeStreamingOutputs`: Live token-by-token output accumulation
- `nodeExecutionResults`: Final results with success/error/execution_time
- `nodeStartOrder`: Tracks execution sequence for debugging

### State Management Anti-Patterns (CRITICAL)
Avoid infinite React re-render loops in streaming updates:
```typescript
// ❌ WRONG - causes Maximum update depth exceeded
set(state => ({ ...state, newData }))

// ✅ CORRECT - safe functional updates with change detection
set(state => {
  if (currentOutput === newOutput) return state; // No change = no render
  return { ...state, nodeStreamingOutputs: { ...state.nodeStreamingOutputs, [nodeId]: newOutput }};
});
```

**Batch Update Pattern** (in `nodeWorkflowStore.ts` streaming handler):
- Accumulate streaming chunks in `streamBatch` object
- Flush every 50ms max (MIN_FLUSH_INTERVAL) to throttle React updates to 20 FPS
- Check `hasChanges` before calling `set()` to prevent unnecessary renders
- Critical for handling high-frequency token streams without UI freezes

### Context-Node RAG Integration
Context-nodes perform vector similarity search + optional reranking:
```typescript
// Context-node configuration
{
  knowledge_base: "sentence-nvme_2-2", // ChromaDB collection
  search_intensity: "standard", // exact | standard | comprehensive
  rerank_provider: "openai", // Optional: LLM-based reranking
  rerank_model: "gpt-4o-mini", // Model for reranking
  additional_context: "Custom context..." // Optional: append to search results
}
```

**Context-Node Execution Flow** (from `node_executors.py`):
1. Receive input from pre-nodes (usually input-node content)
2. Search knowledge base via `VectorStoreService.search()` with intensity params
3. Optional: Rerank results using LLM if `rerank_provider` specified
4. Append `additional_context` if provided (manual context injection)
5. Output combined context string for downstream LLM nodes
6. Downstream nodes access via `{context}` template variable

Context search results inject via `{context}` template variable in downstream LLM prompts.

**VectorStore Service Pattern** (Critical for ChromaDB concurrency):
- `VectorStoreService` maintains per-instance cache (`_store_cache`) to avoid ChromaDB locking
- On error, cache is cleared and instance recreated (connection recovery pattern)
- DO NOT use global singleton - each request creates new `VectorStoreService` instance
- Context-nodes perform: initial search → optional LLM reranking → return top_k results

**ChromaDB readonly/locked Error Prevention** (from `vector_store.py`):
- SQLite WAL mode enabled: `PRAGMA journal_mode=WAL` for concurrent read-write access
- Busy timeout set to 30s: `PRAGMA busy_timeout=30000` to wait instead of failing
- Exponential backoff retry (5 attempts): 0.2s, 0.4s, 0.8s, 1.6s, 3.2s delays
- WAL checkpoint on close: `PRAGMA wal_checkpoint(FULL)` ensures write completion
- Context manager (`with VectorStore(...)`) guarantees proper cleanup
- API server lock minimized: only file system operations protected, heavy processing outside lock

**Search Intensity Algorithm** (Top-K + Similarity Threshold from `SearchIntensity` enum in `models.py`):
```python
# Based on BGE-M3 actual similarity distribution (measured values in 0.2~0.4 range)
EXACT:        init=10, final=5, threshold=0.3   # Clearly related documents (30%+ similarity)
STANDARD:     init=20, final=12, threshold=0.2  # Moderately related (20%+ similarity, default)
COMPREHENSIVE: init=40, final=25, threshold=0.1 # Any relevance (10%+ similarity)
```
**Threshold Rationale**: BGE-M3 actual similarity for related documents is typically 0.2~0.4. Theoretical recommended values (0.8/0.65/0.5) are too high and filter out most results. Practical values (0.3/0.2/0.1) ensure adequate search results. When using reranking, LLM re-evaluates results, so lower thresholds are safe.

**Pipeline**: ChromaDB retrieves `init` results → similarity threshold filtering → optional LLM reranker → return `final` results. Threshold prevents irrelevant results (minimum 1 result guaranteed). Reranker uses LLM to re-score and sort filtered results by relevance.

**Chunk Configuration** (Token-based from `config.py`):
```python
VECTOR_DB_CONFIG = {
    "chunk_tokens": 512,        # Chunk size (tokens)
    "overlap_ratio": 0.15,      # Overlap ratio (15%)
    "chars_per_token": 4        # For character fallback calculation
}
```
Character-based values (`chunk_size`, `chunk_overlap`) calculated dynamically: `chunk_tokens * chars_per_token`. Single source of truth: token count + ratio.

## Essential Development Workflows

### Testing with pytest (REQUIRED)
All tests run from **project root** (not `server/` directory) using pytest:
```powershell
# Run all tests from project root
pytest tests/ -v

# Specific test categories  
pytest tests/test_streaming.py -v          # Streaming execution
pytest tests/test_context_node.py -v      # RAG functionality
pytest tests/test_validation_chain_bug.py # Connection validation

# Quick test runner scripts (from project root)
.\run_tests.bat  # Windows
./run_tests.sh   # Unix/Linux

# Tests with coverage
pytest tests/ --cov=server --cov-report=html
```

**Test Configuration**: Tests use fixtures from `tests/conftest.py`:
- `api_client`: HTTP client with server health check (waits up to 10s for server startup)
- `sample_workflow`: Basic input → generation → output workflow
- Server must be running on :5001 before tests (or set `API_HOST`/`API_PORT` env vars)

### Google AI Streaming Issues (Common Problem)
Google AI API streaming requires ThreadPoolExecutor workaround due to sync-only SDK. Implementation in `google_llm_client.py`:
```python
# Use ThreadPoolExecutor + asyncio.Queue for real-time streaming
def _sync_generate_to_queue():
    response = genai_model.generate_content(prompt, stream=True)
    for chunk in response:
        if hasattr(chunk, 'text') and chunk.text:
            asyncio.run_coroutine_threadsafe(chunk_queue.put(chunk.text), main_loop)
    asyncio.run_coroutine_threadsafe(chunk_queue.put(None), main_loop)

# Run in separate thread, yield from queue
executor.submit(_sync_generate_to_queue)
while True:
    chunk = await chunk_queue.get()
    if chunk is None: break
    yield chunk
```

**Common errors**: `finish_message` or `Unknown field` indicate Google AI API schema changes.

### Frontend Development (React + Zustand)
```powershell
cd client/react-app
npm install && npm run dev
```

Key React patterns:
- `useNodeWorkflowStore()`: Central state for workflow execution
- `NodeWorkflowCanvas`: ReactFlow-based visual editor with drag-drop
- `NodeExecutionResultPanel`: Real-time streaming output display with auto-scroll
- Viewport persistence via localStorage for UX continuity

**Output Parsing Pattern** (from `output_parser.py`):
LLM responses parsed via `<output>...</output>` tags (Korean `<출력>...</출력>` also supported):
- If tags present: content inside tags becomes final output
- If tags missing: entire response becomes output (fallback behavior)
- Used by generation/ensemble/validation nodes to extract structured results
- Enable via `output_format` field in node configuration (adds instruction to prompt)

## File Architecture & Key Locations

### Server Structure
- `src/core/models.py`: Pydantic models for workflow definition (NodeType, SearchIntensity enums)
- `src/core/workflow_validator.py`: Connection rule enforcement (Korean error messages)
- `src/core/node_execution_engine.py`: Async parallel execution engine with SSE streaming
- `src/api/node_executors.py`: Node-specific execution logic (context/LLM separation)
- `src/services/google_llm_client.py`: Google AI integration (ThreadPoolExecutor workaround)
- `src/services/vector_store_service.py`: VectorStore wrapper with instance caching
- `src/services/rerank.py`: LLM-based reranking for context-node results
- `tests/`: pytest test suite (run from **project root**, not server/)

### React Frontend Structure
- `src/store/nodeWorkflowStore.ts`: Central Zustand state management
- `src/components/NodeWorkflowCanvas.tsx`: ReactFlow visual editor
- `src/components/NodeExecutionResultPanel.tsx`: Streaming results display
- `src/types/nodeWorkflow.ts`: TypeScript type definitions

### Configuration Patterns
Node configuration via unified interface:
```typescript
// LLM nodes (generation/ensemble/validation)
{ nodeType: 'generation-node', llm_provider: 'google', model_type: 'gemini-1.5-flash' }

// Context nodes (RAG)  
{ nodeType: 'context-node', knowledge_base: 'nvme_kb', search_intensity: 'high' }
```

## Environment Dependencies
- API Keys: `OPENAI_API_KEY`, `GOOGLE_API_KEY` in server/.env
- ChromaDB for vector storage (auto-managed)
- FastAPI server on :5001, React dev server on :5173
- Knowledge bases in server/knowledge_bases/ (git-ignored)

## Debugging Workflow Issues
1. **Validation Errors**: Check `workflow_validator.py` connection rules
2. **Streaming Hangs**: Verify context-node has input-node pre-connection  
3. **Google AI Failures**: Check `google_llm_client.py` MAX_TOKENS handling
4. **React Infinite Loops**: Review state updates in `nodeWorkflowStore.ts`
5. **Missing Knowledge Bases**: Use `python -m src.admin.admin` to add data

## Starting the Application
```powershell
# Backend (from project root or server/ directory)
cd server
python main.py  # Starts uvicorn on :5001 with auto-reload

# Frontend (separate terminal)
cd client/react-app
npm install  # First time only
npm run dev  # Starts Vite dev server on :5173
```

When working with this codebase, prioritize the real-time streaming execution pipeline, understand the strict node connection validation rules, and be aware of the Google AI streaming workarounds.