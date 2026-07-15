#!/bin/bash
# Force reinstall the AutoDocX private Python environment (macOS)

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETUP_SCRIPT="$PROJECT_ROOT/mac/setup_runtime.sh"
VENV_DIR="$PROJECT_ROOT/runtime/venv"

echo ""
echo "============================================"
echo "          AutoDocX Reinstaller"
echo "============================================"
echo ""
echo "This will delete and recreate the private Python environment."
echo "It will NOT touch your system Python or any global packages."
echo ""

read -p "Continue? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Cancelled."
    exit 0
fi

if [ -d "$VENV_DIR" ]; then
    echo "Removing existing environment..."
    rm -rf "$VENV_DIR"
fi

bash "$SETUP_SCRIPT"

if [ $? -eq 0 ]; then
    echo ""
    echo "Done. Run AutoDocX_for_mac.sh to launch AutoDocX."
    echo ""
else
    echo ""
    echo "[ERROR] Reinstall failed. Check your internet connection and try again."
    echo ""
    exit 1
fi
