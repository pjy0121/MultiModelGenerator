# MultiModelGenerator Server

Requirements extraction server using Vector DB-based Multi-Model Validation

## Project Structure

```text
server/
├── main.py                 # Server entry point
├── admin_tool.py          # Admin tool CLI
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (API keys, etc.)
├── .gitignore            # Git ignore file
├── admin_reference.md    # Admin tool reference document
├── server_reference.md   # Server reference document
├── knowledge_bases/      # Vector DB storage (excluded from Git)
└── src/                  # Source code
    ├── api/              # FastAPI endpoints
    │   └── api_server.py
    ├── core/             # Core modules
    │   ├── config.py     # Configuration management
    │   ├── models.py     # Data models
    │   └── layer_engine.py  # Layer execution engine
    ├── services/         # External service integration
    │   ├── document_processor.py  # Document processing
    │   └── vector_store.py        # Vector DB management
    └── admin/            # Admin tools
        └── admin.py      # Knowledge base management
```

## Key Features

### 1. Multi-Layer Architecture

- **Generation Layer**: Generate responses from multiple LLM models
- **Ensemble Layer**: Integrate model responses
- **Validation Layer**: Validate integrated responses

### 2. Knowledge Base Management

- Build Vector DB from PDF documents
- View knowledge base list, check status
- Add/delete knowledge bases

### 3. REST API

- Requirements extraction API
- Knowledge base management API
- LLM model query API

## Installation and Running

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Set API keys in `.env` file:

```env
PERPLEXITY_API_KEY=your_api_key_here
```

### 3. Run Server

```bash
python main.py
```

### 4. Admin Tool Usage

```bash
# List knowledge bases
python admin_tool.py list

# Build knowledge base
python admin_tool.py build <kb_name> <pdf_path>

# Delete knowledge base
python admin_tool.py delete <kb_name>

# Check knowledge base status
python admin_tool.py status <kb_name>
```

## API Endpoints

### 1. **New Step-by-Step Workflow API** (Recommended)

#### Context Search
```http
POST /search-context
```
- Search related chunks from knowledge base
- Used at workflow start from frontend

#### Execute Single Node
```http
POST /execute-node
```
- Execute individual Generation Layer nodes
- Can call separately for each model

#### Execute Ensemble
```http
POST /execute-ensemble
```
- Integrate multiple Generation results
- Call after all Generation nodes complete

#### Execute Validation
```http
POST /execute-validation
```
- Execute individual Validation Layer nodes
- Includes change tracking feature

### 2. **Knowledge Base Management API**

#### Knowledge Base List
```http
GET /knowledge-bases
```

#### Knowledge Base Status
```http
GET /knowledge-bases/{kb_name}/status
```

### 4. **Model and Configuration API**

#### Available Models List
```http
GET /available-models
```

## Layer-Based Execution Flow

### Frontend Execution Flow:

1. **Context Search**: Get related chunks via `/search-context`
2. **Generation Layer**: Call `/execute-node` for each node
3. **Real-time Feedback**: Display each Generation result to user
4. **Ensemble**: Call `/execute-ensemble` after all Generations complete
5. **Validation**: Call `/execute-validation` for each Validation node
6. **Display Changes**: Show which requirements changed at each Validation step

### Benefits:
- ✅ Real-time progress display
- ✅ View results at each step
- ✅ Improved user experience
- ✅ Stop/modify at intermediate steps
- ✅ Change tracking and display

## Development Notes

- All source code is organized by function under `src/` directory
- Relative imports used for module dependency management
- `__pycache__` and `knowledge_bases/` are excluded from Git
