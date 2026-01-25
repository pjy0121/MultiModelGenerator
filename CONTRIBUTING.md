# Contributing to MultiModelGenerator

First off, thank you for considering contributing to MultiModelGenerator! It's people like you that make this project a great tool for the community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Style Guidelines](#style-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.9 or higher
- Node.js 18 or higher
- npm or yarn
- Git

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/MultiModelGenerator.git
   cd MultiModelGenerator
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/MultiModelGenerator.git
   ```

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** (code snippets, screenshots, etc.)
- **Describe the behavior you observed and what you expected**
- **Include your environment details** (OS, Python version, Node.js version, browser)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description of the proposed enhancement**
- **Explain why this enhancement would be useful**
- **List any alternatives you've considered**

### Your First Code Contribution

Unsure where to begin? Look for issues labeled:

- `good first issue` - Simple issues suitable for beginners
- `help wanted` - Issues that need attention from contributors
- `documentation` - Documentation improvements needed

### Pull Requests

1. Follow the [style guidelines](#style-guidelines)
2. Include appropriate test cases
3. Update documentation as needed
4. Follow the [commit message guidelines](#commit-messages)

## Development Setup

### Backend Setup

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start the development server
cd server
python main.py
```

### Frontend Setup

```bash
cd client/react-app

# Install dependencies
npm install

# Start development server
npm run dev

# Run linting
npm run lint

# Run type checking
npm run type-check
```

### Running Tests

```bash
# Backend tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=server --cov-report=html

# Frontend tests (if available)
cd client/react-app
npm run test
```

## Style Guidelines

### Python Code Style

We follow [PEP 8](https://peps.python.org/pep-0008/) with some modifications:

- **Line length**: Maximum 100 characters
- **Imports**: Use `isort` for import sorting
- **Formatting**: Use `black` for code formatting
- **Type hints**: Use type hints for function parameters and return values
- **Docstrings**: Use Google-style docstrings

```python
def process_node(node_id: str, data: dict[str, Any]) -> NodeResult:
    """Process a single node in the workflow.

    Args:
        node_id: The unique identifier of the node.
        data: The input data for the node.

    Returns:
        NodeResult containing the processed output.

    Raises:
        NodeExecutionError: If the node fails to execute.
    """
    pass
```

### TypeScript/React Code Style

- **Formatting**: Use Prettier with default settings
- **Linting**: Follow ESLint rules defined in the project
- **Components**: Use functional components with hooks
- **Types**: Prefer interfaces over type aliases for object shapes
- **Naming**:
  - Components: PascalCase (`NodeWorkflowCanvas.tsx`)
  - Utilities: camelCase (`formatResponse.ts`)
  - Constants: UPPER_SNAKE_CASE

```typescript
interface NodeProps {
  id: string;
  data: NodeData;
  onUpdate: (id: string, data: Partial<NodeData>) => void;
}

export const CustomNode: React.FC<NodeProps> = ({ id, data, onUpdate }) => {
  // Component implementation
};
```

### CSS/Styling

- Use CSS variables for theming
- Follow BEM naming convention for class names
- Keep styles modular and component-scoped

## Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Adding or modifying tests
- `chore`: Build process or auxiliary tool changes

### Examples

```
feat(nodes): add support for custom LLM endpoints

Add the ability to configure custom LLM API endpoints for
enterprise deployments. Users can now specify their own
endpoint URL in the node configuration.

Closes #123
```

```
fix(execution): resolve streaming timeout issue

Fixed an issue where long-running LLM responses would
timeout before completion. Increased default timeout
and added configurable timeout option.
```

## Pull Request Process

### Before Submitting

1. **Update your fork**:
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes** following the style guidelines

4. **Test your changes**:
   ```bash
   # Run backend tests
   pytest tests/ -v

   # Run frontend linting
   cd client/react-app && npm run lint
   ```

5. **Commit your changes** following commit message guidelines

### Submitting

1. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a Pull Request on GitHub

3. Fill out the PR template completely

4. Wait for review - maintainers will review your PR and may request changes

### PR Requirements

- [ ] Code follows the project's style guidelines
- [ ] Tests pass locally
- [ ] New code has appropriate test coverage
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventions
- [ ] PR description clearly explains the changes

### Review Process

1. At least one maintainer must approve the PR
2. All CI checks must pass
3. Any requested changes must be addressed
4. The PR will be merged using "Squash and merge"

## Project Structure

```
MultiModelGenerator/
├── client/                    # Frontend application
│   └── react-app/
│       ├── src/
│       │   ├── components/    # React components
│       │   ├── store/         # State management
│       │   ├── services/      # API services
│       │   ├── types/         # TypeScript types
│       │   └── utils/         # Utility functions
│       └── package.json
├── server/                    # Backend application
│   ├── src/
│   │   ├── api/              # API endpoints
│   │   ├── models/           # Data models
│   │   ├── services/         # Business logic
│   │   ├── workflow/         # Workflow engine
│   │   └── utils/            # Utilities
│   └── main.py
├── tests/                     # Test suite
├── docs/                      # Documentation
└── knowledge_bases/           # KB storage (gitignored)
```

## Community

### Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and community discussions
- **Documentation**: Check the [docs](docs/) folder

### Recognition

Contributors will be recognized in:
- The project's README
- Release notes for significant contributions
- GitHub's contributor graph

---

Thank you for contributing to MultiModelGenerator! Your efforts help make AI workflow building accessible to everyone.
