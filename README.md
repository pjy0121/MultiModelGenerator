# MultiModelGenerator

<div align="center">

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Node](https://img.shields.io/badge/node-18%2B-green)
![React](https://img.shields.io/badge/react-18-61dafb)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)

**A visual node-based AI workflow builder for orchestrating multiple LLM models with RAG integration.**

[Features](#key-features) | [Installation](#installation) | [Documentation](#usage) | [Contributing](#contributing)

[한국어 README](README_ko.md)

</div>

---

## Overview

MultiModelGenerator is a powerful visual workflow builder for orchestrating multiple LLM models to extract, validate, and synthesize requirements from technical documents. Using a node-based graph interface, users can design complex AI pipelines that leverage multiple AI providers and integrate with knowledge bases for Retrieval-Augmented Generation (RAG).

<div align="center">

<!-- TODO: Add main screenshot here -->
<!-- ![MultiModelGenerator Screenshot](docs/assets/screenshot-main.png) -->

</div>

## Who Is This For?

| User | Benefit |
|------|---------|
| **System Analysts & PMs** | Automatically extract requirements from technical documents - analyze hundreds of pages in minutes |
| **AI/ML Researchers** | Compare LLM models (GPT-4, Gemini, etc.) side by side and experiment with prompts |
| **Technical Writers** | Automate document summarization with RAG-powered context-aware Q&A |
| **Developers & Engineers** | Visually build complex AI pipelines without coding, export to JSON for automation |

## Key Features

### Visual Workflow Builder
- **Node-based Graph Interface**: Design AI pipelines using intuitive drag-and-drop
- **Real-time Streaming**: Watch LLM responses stream in real-time
- **Parallel Execution**: Independent nodes execute concurrently for optimal performance
- **Workflow Management**: Save, restore, export (JSON), and import workflows

### Multi-Model Support
| Provider | Models |
|----------|--------|
| OpenAI | GPT-4, GPT-4 Turbo, GPT-3.5 Turbo |
| Google | Gemini Pro, Gemini Ultra |
| Internal | Custom/Enterprise LLM endpoints |

### Knowledge Base (RAG) Integration
- **Vector Store**: ChromaDB-based document embedding and retrieval
- **BGE-M3**: Multilingual embedding model for 100+ languages
- **Intelligent Reranking**: BAAI/bge-reranker-v2-m3 for improved relevance
- **Folder Organization**: Hierarchical structure with password protection

### Node Types

| Node | Icon | Description |
|------|------|-------------|
| Input | 📥 | Entry point for text data |
| Generation | 🤖 | LLM-powered content generation |
| Ensemble | 🔀 | Combines outputs from multiple nodes |
| Validation | ✅ | Validates results against knowledge base |
| Context | 🔍 | RAG-based context retrieval |
| Output | 📤 | Final result display |

## Installation

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm or yarn

### Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/MultiModelGenerator.git
cd MultiModelGenerator

# Backend setup
pip install -r requirements.txt
cp .env.example .env  # Configure your API keys

# Start backend
cd server && python main.py

# Frontend setup (new terminal)
cd client/react-app
npm install
npm run dev
```

### Environment Variables

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
INTERNAL_API_KEY=your_internal_api_key        # Optional
INTERNAL_API_ENDPOINT=your_internal_endpoint  # Optional
```

## Usage

### Creating a Workflow

1. **Add Nodes**: Click node buttons to add to canvas
2. **Connect Nodes**: Drag handles to create connections
3. **Configure**: Click nodes to set LLM provider, model, and prompts
4. **Execute**: Click "Execute Workflow" for streaming results

### Prompt Variables

Use these placeholders in your prompts:
- `{input_data}` - Input from connected upstream node
- `{context}` - Retrieved context from knowledge base (Context nodes)

### Knowledge Base

```
Upload PDF/TXT → Auto-embed with BGE-M3 → Store in ChromaDB → Query via Context nodes
```

## Architecture

```
MultiModelGenerator/
├── client/                    # Frontend (React + TypeScript)
│   └── react-app/
│       ├── src/
│       │   ├── components/    # React components
│       │   ├── store/         # Zustand state management
│       │   ├── services/      # API communication
│       │   └── types/         # TypeScript definitions
│       └── package.json
├── server/                    # Backend (Python + FastAPI)
│   ├── src/
│   │   ├── api/              # FastAPI endpoints
│   │   ├── models/           # Pydantic models
│   │   ├── services/         # LLM clients, vector store
│   │   └── workflow/         # Execution engine
│   └── main.py
├── tests/                     # Pytest test suite
└── docs/                      # Documentation
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/execute-workflow-stream` | POST | Execute workflow with streaming |
| `/stop-workflow/{id}` | POST | Stop running workflow |
| `/knowledge-bases` | GET | List knowledge bases |
| `/knowledge-bases/create` | POST | Create knowledge base |
| `/search-knowledge-base` | POST | Search knowledge base |
| `/available-models/{provider}` | GET | Get available models |

## Tech Stack

<table>
<tr>
<td valign="top" width="50%">

### Frontend
- React 18 + TypeScript
- React Flow (graph editor)
- Ant Design (UI)
- Zustand (state)
- Vite (build)

</td>
<td valign="top" width="50%">

### Backend
- FastAPI (async REST)
- ChromaDB (vector store)
- BGE-M3 (embeddings)
- Pydantic (validation)

</td>
</tr>
</table>

## Testing

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=server --cov-report=html
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Commit: `git commit -m 'feat: add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## Security

For security issues, please see our [Security Policy](SECURITY.md).

**Do not report security vulnerabilities through public GitHub issues.**

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [React Flow](https://reactflow.dev/) for the graph editor
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [BGE-M3](https://huggingface.co/BAAI/bge-m3) for multilingual embeddings
- All our [contributors](https://github.com/YOUR_USERNAME/MultiModelGenerator/graphs/contributors)

---

<div align="center">

**[Documentation](docs/)** | **[Report Bug](.github/ISSUE_TEMPLATE/bug_report.md)** | **[Request Feature](.github/ISSUE_TEMPLATE/feature_request.md)**

Made with dedication by the MultiModelGenerator team

</div>
