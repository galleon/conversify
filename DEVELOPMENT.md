# Development Guide

This document outlines the development workflow, code quality standards, and best practices for the Conversify project.

## 🚀 Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd conversify

# Setup development environment
make dev-setup

# Run quality checks
make quality
```

## 🛠️ Code Quality Tools

### Ruff - Fast Python Linter & Formatter

Conversify uses [Ruff](https://github.com/astral-sh/ruff) as the primary code quality tool. Ruff is an extremely fast Python linter and code formatter written in Rust.

**Features:**
- ⚡ 10-100x faster than existing tools
- 🔧 Auto-fixes many issues
- 📦 Combines functionality of flake8, isort, pydocstyle, and more
- 🎯 Zero configuration required (but highly configurable)

**Enabled Rules:**
- `E` - pycodestyle errors
- `W` - pycodestyle warnings
- `F` - pyflakes
- `I` - isort (import sorting)
- `B` - flake8-bugbear
- `C4` - flake8-comprehensions
- `UP` - pyupgrade (modern Python syntax)
- `N` - pep8-naming
- `SIM` - flake8-simplify
- `RUF` - ruff-specific rules

### Pre-commit Hooks

Automatic code quality checks before each commit:

```bash
# Install hooks (included in dev-setup)
make setup-hooks

# Run hooks manually
pre-commit run --all-files
```

## 📋 Development Commands

### Make Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make install` | Install production dependencies |
| `make install-dev` | Install development dependencies |
| `make setup-hooks` | Setup pre-commit hooks |
| `make format` | Auto-format code with Ruff |
| `make lint` | Run linting checks |
| `make test` | Run all tests |
| `make quality` | Run comprehensive quality checks |
| `make clean` | Clean up temporary files |

### Manual Quality Commands

```bash
# Linting
ruff check .                    # Check for issues
ruff check . --fix             # Auto-fix issues
ruff check . --watch           # Watch for changes

# Formatting
ruff format .                   # Format all files
ruff format --check .          # Check formatting without changes
ruff format --diff .           # Show what would be changed

# Combined quality check
./scripts/quality.sh           # Run comprehensive checks
```

## 🏗️ Project Structure

```
conversify/
├── conversify/              # Main package
│   ├── core/               # Core agent logic
│   ├── models/             # STT, TTS, LLM integrations
│   ├── utils/              # Shared utilities
│   └── main.py             # Application entrypoint
├── tests/                  # Test files
├── scripts/                # Development scripts
│   ├── quality.sh          # Quality check script
│   ├── format.sh           # Formatting script
│   └── run_*.sh            # Runtime scripts
├── config.toml             # Application configuration
├── config.example.toml     # Example configuration
├── pyproject.toml          # Python project config
├── Makefile                # Development commands
└── DEVELOPMENT.md          # This file
```

## 🔧 Configuration Files

### pyproject.toml - Ruff Configuration

```toml
[tool.ruff]
target-version = "py311"
line-length = 88
indent-width = 4

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "N", "SIM", "RUF"]
ignore = [
    "E501",  # line too long (handled by formatter)
    "B008",  # do not perform function calls in argument defaults
    "N803",  # argument name should be lowercase
    "N806",  # variable in function should be lowercase
]
```

### .pre-commit-config.yaml

Pre-commit hooks automatically run quality checks before commits:
- Ruff linting and formatting
- Basic file checks (trailing whitespace, YAML validation, etc.)
- MyPy type checking (when enabled)
- Bandit security scanning

## 🧪 Testing

```bash
# Run all tests
make test
pytest tests/

# Run specific test
pytest tests/test_stt_whisper.py

# Run with coverage
pytest --cov=conversify tests/
```

## 📏 Code Style Guidelines

### General Principles

1. **Consistency**: Follow the existing code style
2. **Readability**: Write code that tells a story
3. **Simplicity**: Prefer simple, explicit solutions
4. **Documentation**: Document complex logic and public APIs

### Python Style

- **Line Length**: 88 characters (Black/Ruff default)
- **Imports**: Sorted and grouped by Ruff/isort
- **Quotes**: Double quotes for strings
- **Naming**:
  - `snake_case` for variables and functions
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Example

```python
"""Module docstring describing the purpose."""

import logging
from typing import Any

from livekit.agents import stt
from conversify.models.utils import WhisperModels

logger = logging.getLogger(__name__)


class ExampleSTT(stt.STT):
    """Example STT implementation following our style guide."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the STT instance.

        Args:
            config: Configuration dictionary from config.toml
        """
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=False,
                interim_results=False
            )
        )
        self._config = config
        logger.info("STT instance initialized")
```

## 🚦 Continuous Integration

The project uses GitHub Actions (or similar) for CI/CD:

1. **Linting**: `ruff check .`
2. **Formatting**: `ruff format --check .`
3. **Testing**: `pytest tests/`
4. **Security**: `bandit -r conversify/`
5. **Dependencies**: `safety check`

Simulate CI locally:
```bash
make ci  # Runs the full CI pipeline
```

## 🔒 Security

### Security Tools

- **Bandit**: Scans for common security issues
- **Safety**: Checks dependencies for known vulnerabilities

### Security Best Practices

1. **No hardcoded secrets**: Use environment variables
2. **Input validation**: Validate all external inputs
3. **Dependency updates**: Keep dependencies updated
4. **Secure defaults**: Use secure configurations by default

## 🎯 STT Backend Support

The project supports multiple Whisper backends:

### faster-whisper (Default)
```toml
[stt.whisper]
backend = "faster-whisper"
model = "deepdml/faster-whisper-large-v3-turbo-ct2"
device = "cpu"  # or "cuda", "metal" (Apple Silicon)
```

### OpenAI Whisper
```toml
[stt.whisper]
backend = "openai"
model = "large-v3"  # simpler model names
device = "cpu"  # or "cuda" (no Metal support)
```

Install OpenAI Whisper backend:
```bash
make install-whisper-openai
# or
uv sync --extra openai-whisper
```

## 📈 Performance Monitoring

### Timing Utilities

Use the `FindTime` context manager for performance monitoring:

```python
from conversify.models.utils import FindTime

# Time critical operations
with FindTime("model_inference"):
    result = model.process(data)
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes following the style guide
4. **Test** your changes: `make quality`
5. **Commit** using conventional commits: `git commit -m "feat: add amazing feature"`
6. **Push** to the branch: `git push origin feature/amazing-feature`
7. **Open** a Pull Request

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` new features
- `fix:` bug fixes
- `docs:` documentation changes
- `style:` formatting changes
- `refactor:` code refactoring
- `test:` test additions/changes
- `chore:` maintenance tasks

## 🐛 Troubleshooting

### Common Issues

**Ruff not found**
```bash
make install-dev  # Reinstall dev dependencies
```

**Pre-commit hooks failing**
```bash
pre-commit clean    # Clean hook cache
pre-commit install  # Reinstall hooks
```

**Import errors in tests**
```bash
# Make sure you're in the project root
cd /path/to/conversify
python -m pytest tests/
```

**Type checking errors**
```bash
# MyPy is currently disabled for initial setup
# Enable gradually by updating pyproject.toml [tool.mypy] section
```

**LiveKit dependency conflicts**
```bash
# If you get dependency resolution errors with livekit packages:
# 1. Check for yanked versions in the error message
# 2. Pin all livekit packages to compatible versions in pyproject.toml
# 3. Run: uv sync to update dependencies
# 4. For Docker builds, ensure you commit the updated uv.lock file
```

**Docker build fails with dependency errors**
```bash
# Make sure uv.lock is committed after dependency changes
git add uv.lock pyproject.toml
git commit -m "fix: update dependencies"

# Clear Docker cache and rebuild
docker system prune -f
docker compose --profile ollama -f docker-compose.cpu.yml up --build
```

**AgentSession TypeError with unexpected keyword arguments**
```bash
# Error: AgentSession.__init__() got an unexpected keyword argument 'resume_false_interruption'
# Fix: Check AgentSession parameters for your LiveKit version:
cd /path/to/conversify
python -c "from livekit.agents import AgentSession; import inspect; print(inspect.signature(AgentSession.__init__))"

# Remove invalid parameters from main.py AgentSession initialization
# Common issues: resume_false_interruption doesn't exist in livekit-agents 1.2.6
```

### Getting Help

1. Check this documentation
2. Run `make help` for available commands
3. Check the issues in the repository
4. Ask in the project's communication channels

## 📚 Additional Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
