#!/bin/bash
# First-run setup for macOS: creates a private venv and installs all packages

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/runtime/venv"
REQUIREMENTS="$PROJECT_ROOT/requirements.txt"

echo ""
echo "============================================"
echo "         AutoDocX Runtime Setup"
echo "============================================"
echo ""

# Check for Python 3
PYTHON=""
for candidate in python3.11 python3.12 python3.10 python3; do
    if command -v "$candidate" &>/dev/null; then
        VERSION=$("$candidate" -c "import sys; print(sys.version_info[:2])")
        MAJOR=$("$candidate" -c "import sys; print(sys.version_info.major)")
        MINOR=$("$candidate" -c "import sys; print(sys.version_info.minor)")
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python 3.10 or higher was not found on your system."
    echo ""
    echo "Install it from: https://www.python.org/downloads/"
    echo "Or with Homebrew: brew install python@3.11"
    echo ""
    exit 1
fi

echo "[Setup] Using Python: $($PYTHON --version)"
echo "[Setup] Creating private virtual environment at:"
echo "        $VENV_DIR"
echo ""

mkdir -p "$PROJECT_ROOT/runtime"
"$PYTHON" -m venv "$VENV_DIR"

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to create virtual environment."
    exit 1
fi

echo "[Setup] Installing packages from requirements.txt..."
echo ""

"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$REQUIREMENTS"

if [ $? -ne 0 ]; then
    echo "[ERROR] Package installation failed."
    echo "        Check your internet connection and try again."
    exit 1
fi

echo ""
echo "============================================"
echo "     AutoDocX Runtime Ready"
echo "============================================"
echo ""
