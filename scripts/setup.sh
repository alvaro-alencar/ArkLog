#!/usr/bin/env bash
set -euo pipefail

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ArkLog - Setup Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Python 3.12+
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED="3.12"
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)"; then
    echo "Python $PYTHON_VERSION OK"
else
    echo "Python 3.12+ required. Found: $PYTHON_VERSION"
    exit 1
fi

# Virtual environment
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Virtual environment created"
fi

source .venv/bin/activate
pip install -e ".[dev]" --quiet
echo "Dependencies installed"

# Config files
[ ! -f ".env" ] && cp .env.example .env && echo ".env created — add your API keys"
[ ! -f "projects.yaml" ] && cp projects.yaml.example projects.yaml && echo "projects.yaml created — configure your projects"

# Runtime directories
mkdir -p data logs

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done. Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Edit projects.yaml with your projects"
echo "  3. source .venv/bin/activate"
echo "  4. uvicorn app.main:app --reload"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
