# MultiModelGenerator

Multi-model AI system for requirements extraction from technical documents using a node-based workflow architecture.

## Testing

This project uses pytest for comprehensive testing of the API and workflow functionality.

### Test Structure

- `tests/` - Main test directory with pytest test cases
- `tests/conftest.py` - Pytest configuration and fixtures
- `tests/test_api_endpoints.py` - Basic API endpoint tests
- `tests/test_workflow_execution.py` - Workflow execution tests
- `tests/test_context_node.py` - Context node and knowledge base tests
- `tests/test_streaming.py` - Streaming execution tests
- `legacy_tests/` - Old test scripts (deprecated)

### Running Tests

#### Prerequisites

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

#### Quick Run

```bash
# Windows
run_tests.bat

# Unix/Linux/Mac
./run_tests.sh
```

#### Manual Testing

```bash
# Start server first
cd server
python main.py

# In another terminal, run tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api_endpoints.py -v

# Run with coverage
pytest tests/ --cov=server --cov-report=html
```

#### Test Categories

```bash
# Run only unit tests
pytest tests/ -m unit

# Run only integration tests  
pytest tests/ -m integration

# Skip slow tests
pytest tests/ -m "not slow"
```

### Test Configuration

Tests are configured via `pyproject.toml` and use the following fixtures:

- `api_client` - HTTP client with automatic server health check
- `api_base_url` - Base URL for API endpoints  
- `sample_workflow` - Basic workflow for testing
- Environment variables: `API_HOST`, `API_PORT`

### Writing New Tests

Follow pytest conventions:

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Use fixtures from `conftest.py`
- Mark slow/integration tests appropriately