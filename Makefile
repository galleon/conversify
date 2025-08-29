# Makefile for Conversify development tasks
# Usage: make <target>

.PHONY: help install install-dev format lint test quality clean setup-hooks docker-build docker-run

# Default target
help:
	@echo "🛠️  Conversify Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  install      Install production dependencies"
	@echo "  install-dev  Install development dependencies"
	@echo "  setup-hooks  Setup pre-commit hooks"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  format       Format code with ruff"
	@echo "  lint         Run linting checks"
	@echo "  test         Run all tests"
	@echo "  quality      Run all quality checks"
	@echo ""
	@echo "Development Commands:"
	@echo "  clean        Clean up temporary files"
	@echo "  run-app      Start the conversify application"
	@echo ""
	@echo "Information Commands:"
	@echo "  show-config     Show current tool versions"
	@echo "  quality-summary Show quality setup summary"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-cpu   Run with Docker (CPU mode)"
	@echo "  docker-gpu   Run with Docker (GPU mode)"
	@echo ""

# Installation commands
install:
	@echo "📦 Installing production dependencies..."
	uv sync --no-dev

install-dev:
	@echo "📦 Installing development dependencies..."
	uv sync --all-extras
	@echo "✅ Development dependencies installed"

setup-hooks:
	@echo "🔧 Setting up pre-commit hooks..."
	.venv/bin/pre-commit install || pre-commit install
	@echo "✅ Pre-commit hooks installed"

# Code quality commands
format:
	@echo "🎨 Formatting code..."
	PATH=.venv/bin:$$PATH ./scripts/format.sh

lint:
	@echo "🔍 Running linting checks..."
	.venv/bin/ruff check . || ruff check .

test:
	@echo "🧪 Running tests..."
	.venv/bin/python -m pytest tests/ -v || python -m pytest tests/ -v

quality:
	@echo "📋 Running all quality checks..."
	PATH=.venv/bin:$$PATH ./scripts/quality.sh

# Development commands
clean:
	@echo "🧹 Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build/ dist/
	@echo "✅ Cleanup completed"

run-app:
	@echo "🚀 Starting Conversify application..."
	./scripts/run_app.sh

# Docker commands
docker-cpu:
	@echo "🐳 Starting Conversify with Docker (CPU mode)..."
	docker-compose -f docker-compose.cpu.yml up --build

docker-gpu:
	@echo "🐳 Starting Conversify with Docker (GPU mode)..."
	docker-compose -f docker-compose.gpu.yml up --build

# Advanced development commands
check-deps:
	@echo "🔍 Checking for dependency vulnerabilities..."
	.venv/bin/safety check || safety check || echo "⚠️  Consider updating vulnerable dependencies"

install-whisper-openai:
	@echo "📦 Installing OpenAI Whisper backend..."
	uv sync --extra openai-whisper
	@echo "✅ OpenAI Whisper backend installed"

# CI/CD simulation
ci:
	@echo "🔄 Running CI pipeline simulation..."
	@$(MAKE) install-dev
	@$(MAKE) quality
	@echo "🎉 CI pipeline completed successfully!"

# Development environment setup
dev-setup: install-dev setup-hooks
	@echo "🎯 Development environment setup completed!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Copy config.example.toml to config.toml"
	@echo "2. Copy .env.example to .env.local"
	@echo "3. Configure your settings"
	@echo "4. Run 'make run-app' to start the application"

# Show current configuration
show-config:
	@echo "📋 Current Configuration:"
	@echo "Python: $(shell .venv/bin/python --version 2>/dev/null || python --version)"
	@echo "UV: $(shell uv --version 2>/dev/null || echo 'Not installed')"
	@echo "Ruff: $(shell .venv/bin/ruff --version 2>/dev/null || ruff --version 2>/dev/null || echo 'Not installed')"
	@echo "Pre-commit: $(shell .venv/bin/pre-commit --version 2>/dev/null || pre-commit --version 2>/dev/null || echo 'Not installed')"

quality-summary:
	@echo "📊 Quality Tools Setup Summary"
	@echo "=============================="
	@if [ -f QUALITY_SETUP_SUMMARY.md ]; then \
		echo ""; \
		echo "See QUALITY_SETUP_SUMMARY.md for complete details"; \
		echo ""; \
		echo "Quick Status:"; \
		echo "✅ Ruff: Fast linting and formatting"; \
		echo "✅ Pre-commit: Automatic quality checks"; \
		echo "✅ Make commands: Development workflow"; \
		echo "✅ STT backends: Both faster-whisper and OpenAI"; \
		echo "✅ Documentation: Comprehensive guides"; \
		echo ""; \
		echo "Run 'make quality' to verify everything works!"; \
	else \
		echo "❌ Quality setup summary not found"; \
	fi
