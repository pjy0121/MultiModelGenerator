# MultiModelGenerator Copilot Instructions

## Project Overview
Multi-model AI system for requirements extraction from technical documents using a node-based workflow architecture. Supports 5 node types connected in directed graphs: input → generation → ensemble → validation → output + context nodes for RAG integration.

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

### Real-Time Streaming Execution
Server-side async streaming with dependency resolution in `node_execution_engine.py`:
```python
# Event-driven parallel execution with real-time updates
for chunk in response_stream:
    if chunk.type == 'node_start': # Node begins execution
    elif chunk.type == 'stream':   # Real-time LLM token streaming  
    elif chunk.type == 'node_complete': # Node finished
    elif chunk.type == 'complete': # Workflow finished
```

Frontend receives real-time updates via `nodeWorkflowStore.ts` managing:
- `nodeExecutionStates`: Track 'idle' | 'executing' | 'completed' | 'error'
- `nodeStreamingOutputs`: Live token-by-token output accumulation
- `nodeExecutionResults`: Final results with success/error/execution_time

### State Management Anti-Patterns (CRITICAL)
Avoid infinite React re-render loops in streaming updates:
```typescript
// ❌ WRONG - causes Maximum update depth exceeded
set(state => ({ ...state, newData }))

// ✅ CORRECT - safe functional updates
set(state => {
  if (currentOutput === newOutput) return state; // No change
  return { ...state, nodeStreamingOutputs: { ...state.nodeStreamingOutputs, [nodeId]: newOutput }};
});
```

### Context-Node RAG Integration
Context-nodes perform vector similarity search + optional reranking:
```typescript
// Context-node configuration
{
  knowledge_base: "sentence-nvme_2-2", // ChromaDB collection
  search_intensity: "medium", // Controls top_k results
  rerank_provider: "openai", // Optional: LLM-based reranking
  rerank_model: "gpt-4o-mini" // Model for reranking
}
```

Context search results inject via `{context}` template variable in downstream LLM prompts.

## Essential Development Workflows

### Testing with pytest (REQUIRED)
All tests run from `server/tests/` directory using pytest:
```powershell
# Run all tests
cd server && pytest tests/ -v

# Specific test categories  
pytest tests/test_streaming.py -v          # Streaming execution
pytest tests/test_context_node.py -v      # RAG functionality
pytest tests/test_validation_chain_bug.py # Connection validation

# Quick test runner scripts
.\run_tests.bat  # Windows
./run_tests.sh   # Unix/Linux
```

### Google AI Streaming Issues (Common Problem)
Google AI API streaming often fails with `StopIteration` errors. Current workaround in `google_llm_client.py`:
```python
# Use non-streaming API, simulate streaming on client side
response = genai_model.generate_content(prompt, stream=False)
if response.text:
    words = response.text.split()
    for word in words:
        yield word + " "
        await asyncio.sleep(0.05)  # Simulate streaming delay
```

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

## File Architecture & Key Locations

### Server Structure
- `src/core/models.py`: Pydantic models for workflow definition
- `src/core/workflow_validator.py`: Connection rule enforcement
- `src/core/node_execution_engine.py`: Async parallel execution engine
- `src/api/node_executors.py`: Node-specific execution logic
- `src/services/google_llm_client.py`: Google AI integration (streaming workarounds)
- `tests/`: pytest test suite (run from server/ directory)

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

When working with this codebase, prioritize the real-time streaming execution pipeline, understand the strict node connection validation rules, and be aware of the Google AI streaming workarounds.