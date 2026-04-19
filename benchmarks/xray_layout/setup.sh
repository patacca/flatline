#!/usr/bin/env bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv-bench"

# Idempotent: check if venv exists
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at $VENV_DIR"
    echo "To recreate, remove it first: rm -rf $VENV_DIR"
    exit 0
fi

echo "Creating virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "Installing flatline from parent repo (editable)..."
"$VENV_DIR/bin/pip" install -e "../.."

echo "Installing core dependencies..."
"$VENV_DIR/bin/pip" install -e ".[core]"

echo ""
echo "Setup complete! Activate with:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "Verify with:"
echo "  python -c \"import flatline, networkx, jsonschema, cairosvg, PIL; print('OK')\""
