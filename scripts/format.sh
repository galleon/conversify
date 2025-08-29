#!/bin/bash
# Code formatting script for Conversify project
# This script automatically fixes code style issues

set -e  # Exit on any error

echo "🎨 Formatting Conversify Code..."
echo "================================"

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

# Ruff - Auto-fix linting issues
print_section "Auto-fixing Linting Issues"
if (.venv/bin/ruff check . --fix || ruff check . --fix); then
    echo "✅ Linting issues fixed"
else
    echo "⚠️  Some linting issues could not be auto-fixed"
fi

# Ruff - Format code
print_section "Formatting Code"
if (.venv/bin/ruff format . || ruff format .); then
    echo "✅ Code formatted successfully"
else
    echo "❌ Code formatting failed"
    exit 1
fi

# Check if there are any remaining issues
print_section "Checking for Remaining Issues"
if (.venv/bin/ruff check . || ruff check .); then
    echo "✅ No remaining linting issues"
else
    echo "⚠️  Some issues still remain (may require manual fixing)"
fi

echo ""
echo "🎉 Code formatting completed!"
echo "============================="
echo ""
echo "💡 Tips:"
echo "  - Run './scripts/quality.sh' to check code quality"
echo "  - Consider setting up pre-commit hooks for automatic formatting"
echo "  - Your editor can be configured to run ruff on save"
