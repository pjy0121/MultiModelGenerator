# MultiModelGenerator Copilot Instructions

## Project Overview
Multi-model AI system for requirements extraction from technical documents using a node-based workflow architecture. Supports 5 node types connected in directed graphs: input → generation → ensemble → validation → output.

## Architecture Patterns

### Node-Based Workflow System
- **Input Nodes**: Plain-text content sources (no pre-nodes, multiple post-nodes allowed)
- **Generation Nodes**: LLM-powered initial requirement generation (input-node → generation-node)
- **Ensemble Nodes**: Combines multiple pre-node outputs (multiple pre-nodes → single output)
- **Validation Nodes**: Sequential validation/refinement of requirements
- **Output Nodes**: Final result display (no post-nodes, single instance per workflow)

### Workflow Connection Rules
Critical constraints enforced in `project_reference.md`:
- Only ensemble-nodes can have multiple pre-nodes
- Only input-nodes can have multiple post-nodes  
- All nodes need pre/post connections except input (no pre) and output (no post)
- Workflow execution blocked if connection rules violated

### Workflow Execution Engine
Server-side execution follows dependency resolution pattern in `src/api/`:
```python
# Workflow execution algorithm
1. Find all input-nodes, add to execution queue
2. While queue has nodes:
   - Find nodes where all pre-nodes completed
   - Execute those nodes in parallel
   - Add their post-nodes to queue
   - Remove completed nodes from queue
```

### Output Parsing Pattern
LLM nodes can use markdown tag-based output extraction via `<output>...</output>` tags:
```markdown
Node response with description...

<output>
Data passed to next node
</output>
```
If no tags found, entire response becomes output. Parser in `src/core/output_parser.py` handles extraction.

### Context Injection Pattern
LLM nodes receive templated prompts with variable substitution:
```python
# Template variables in prompts
'{input_data}' → concatenated pre-node outputs
'{context}' → vector store search results  
```
Search intensity determines vector store `top_k` parameter for context retrieval.

## Key Development Patterns

### Multi-Provider LLM Factory
Supports OpenAI and Google models via unified interface in `src/services/llm_factory.py`:
```python
client = LLMFactory.get_client(provider)
models = LLMFactory.get_available_models(provider)
```

### Node Configuration System
Nodes are configured with model, provider, prompt, and node type in `src/core/models.py`:
```python
class NodeConfig(BaseModel):
    id: str
    model_type: str  # LLM model identifier
    llm_provider: str  # openai/google
    content: str  # for input/output nodes
    # Node types: input-node, generation-node, ensemble-node, validation-node, output-node
```

### API Layer Separation
- `api_server.py`: REST endpoints and request/response models
- `node_executors.py`: Node-specific execution logic with LLM integration
- `node_execution_engine.py`: Core workflow execution engine with dependency resolution

### Client Integration Pattern
Python client (`client/client_example.py`) demonstrates GET-based workflow execution with file output:
```python
# Save validation results to timestamped files
filename = f"validation_result_{kb_name}_{keyword}_{timestamp}.txt"
```

## Essential Commands

### Server Operations (from server/ directory)
```powershell
# Install dependencies
pip install -r requirements.txt

# Start server
python main.py

# Add knowledge base (admin tool)
python -m src.admin.admin

# Environment setup (.env file required)
# OPENAI_API_KEY=your_key
# GOOGLE_API_KEY=your_key
```



### Testing Workflow
```powershell
# Test full workflow (from client/ directory)  
python client_example.py

# Check knowledge bases
curl http://localhost:5001/knowledge-bases

# React frontend (from client/react-app/ directory)
npm install
npm run dev
```

## File Organization Conventions

### Server Structure
- `src/core/`: Data models, configuration, and execution engines
- `src/api/`: REST endpoints and layer execution logic
- `src/services/`: External integrations (LLM clients, vector store, document processing)
- `knowledge_bases/`: ChromaDB instances (git-ignored)

### React Frontend Structure  
- `src/components/`: Workflow canvas, execution panels, node editors
- `src/store/`: Zustand store managing workflow state and execution
- `src/services/`: API client for backend communication

### Frontend Workflow Canvas
ReactFlow-based visual workflow editor with drag-and-drop nodes:
```tsx
// Node types in src/components/
CustomNode: WorkflowNode (Generation/Ensemble/Validation)
PlaceholderNode: Template for adding new nodes
NodeEditModal: Model selection and configuration
```
Canvas automatically connects nodes: Generation → Ensemble → Validation chain.

## Critical Integration Points

### Node Input/Output Chain
Generation outputs feed Ensemble input → Ensemble output feeds first Validation input → Each Validation output feeds next Validation input

### Context Management
Vector store searches are enhanced during Validation by extracting requirement keywords and performing additional similarity searches to ensure comprehensive context coverage

### State Management (Frontend)
React store (`src/store/nodeWorkflowStore.ts`) manages complex execution state with step tracking, node results, and real-time updates during workflow execution

## Environment Dependencies
- Requires API keys: `OPENAI_API_KEY`, `GOOGLE_API_KEY`
- ChromaDB for vector storage
- FastAPI with CORS for React integration
- File outputs saved to timestamped `.txt` files (not markdown display)

When working with this codebase, focus on the node execution pipeline, markdown tag-based output parsing, and the dependency-driven execution order defined by pre-node/post-node relationships.