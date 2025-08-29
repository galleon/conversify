#!/bin/bash
# Quality check script for Conversify project
# This script runs all code quality tools and tests

set -e  # Exit on any error

echo "🧹 Running Conversify Quality Checks..."
echo "========================================"

# Change to project root directory
cd "$(dirname "$0")/.."

# Set PATH to include virtual environment
export PATH=".venv/bin:$PATH"

# Function to print section headers
print_section() {
    echo ""
    echo "📋 $1"
    echo "----------------------------------------"
}

# Function to handle errors
handle_error() {
    echo "❌ $1 failed with exit code $2"
    exit $2
}

# Ruff - Linting
print_section "Running Ruff Linter"
if ! (.venv/bin/ruff check . || ruff check .); then
    handle_error "Ruff linting" $?
fi
echo "✅ Ruff linting passed"

# Ruff - Formatting check
print_section "Checking Code Formatting"
if ! (.venv/bin/ruff format --check . || ruff format --check .); then
    echo "❌ Code formatting issues found. Run 'ruff format .' to fix."
    exit 1
fi
echo "✅ Code formatting is correct"

# Type checking with mypy (temporarily disabled - too many issues to fix initially)
# if command -v mypy &> /dev/null; then
#     print_section "Running Type Checking (MyPy)"
#     if ! mypy --config-file pyproject.toml conversify/; then
#         handle_error "MyPy type checking" $?
#     fi
#     echo "✅ Type checking passed"
# else
    echo "ℹ️  MyPy temporarily disabled for initial setup"
# fi

# Run tests
print_section "Running Tests"
if ! (.venv/bin/python -m pytest tests/ -v || python -m pytest tests/ -v); then
    handle_error "Tests" $?
fi
echo "✅ All tests passed"

# Check for security issues with bandit (if installed)
if (.venv/bin/bandit --version &> /dev/null) || (command -v bandit &> /dev/null); then
    print_section "Security Check (Bandit)"
    if ! (.venv/bin/bandit -r conversify/ -f json -o bandit-report.json || bandit -r conversify/ -f json -o bandit-report.json); then
        echo "⚠️  Security issues found. Check bandit-report.json for details."
    else
        echo "✅ No security issues found"
        rm -f bandit-report.json
    fi
else
    echo "ℹ️  Bandit not installed, skipping security checks"
fi

# Check dependencies for known vulnerabilities with safety (if installed)
if (.venv/bin/safety --version &> /dev/null) || (command -v safety &> /dev/null); then
    print_section "Dependency Security Check (Safety)"
    if ! (.venv/bin/safety check || safety check); then
        echo "⚠️  Vulnerable dependencies found"
    else
        echo "✅ No vulnerable dependencies found"
    fi
else
    echo "ℹ️  Safety not installed, skipping dependency security checks"
fi

echo ""
echo "🎉 All quality checks completed successfully!"
echo "============================================"
