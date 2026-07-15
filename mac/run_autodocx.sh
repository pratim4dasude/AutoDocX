#!/bin/bash
# AutoDocX lifecycle manager for macOS
# Handles: first-run setup, start servers, open browser, cleanup on exit

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$PROJECT_ROOT/runtime/venv/bin/python"
SETUP_SCRIPT="$PROJECT_ROOT/mac/setup_runtime.sh"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
BACKEND_PORT=7832
FRONTEND_PORT=7833
BACKEND_URL="http://127.0.0.1:$BACKEND_PORT"
FRONTEND_URL="http://localhost:$FRONTEND_PORT"

BACKEND_PID=""
FRONTEND_PID=""

print_banner() {
    echo ""
    echo "============================================"
    echo "                 AutoDocX"
    echo "============================================"
    echo ""
}

stop_servers() {
    echo ""
    echo "Stopping AutoDocX..."

    [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null

    # Kill anything still holding the ports
    for PORT in $BACKEND_PORT $FRONTEND_PORT; do
        PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null)
        [ -n "$PIDS" ] && echo "$PIDS" | xargs kill -9 2>/dev/null
    done

    echo "AutoDocX stopped."
}

# Run cleanup on exit or Ctrl+C
trap stop_servers EXIT INT TERM

print_banner

# Step 1: Install runtime on first run
if [ ! -f "$VENV_PYTHON" ]; then
    echo "[Setup] First-time setup: creating private Python environment."
    echo "        This takes about 2 minutes and only happens once."
    echo ""

    if [ ! -f "$SETUP_SCRIPT" ]; then
        echo "[ERROR] Setup script not found: $SETUP_SCRIPT"
        exit 1
    fi

    bash "$SETUP_SCRIPT"

    if [ $? -ne 0 ]; then
        echo "[ERROR] Runtime setup failed."
        exit 1
    fi

    if [ ! -f "$VENV_PYTHON" ]; then
        echo "[ERROR] Python runtime was not created at: $VENV_PYTHON"
        exit 1
    fi

    echo ""
    echo "[Setup] Runtime ready."
    echo ""
fi

# Step 2: Create .env from example if missing
if [ ! -f "$ENV_FILE" ]; then
    if [ ! -f "$ENV_EXAMPLE" ]; then
        echo "[ERROR] .env.example not found."
        echo "        Create a .env file in the project root with your LLM API key."
        read -p "Press Enter to exit..."
        exit 1
    fi
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "[Setup] .env file created. Streamlit will guide you to add your API key."
    echo ""
fi

# Step 3: Start both servers
echo "[1/3] Starting FastAPI backend  (port $BACKEND_PORT)..."
cd "$PROJECT_ROOT"
"$VENV_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" &>/dev/null &
BACKEND_PID=$!

echo "[2/3] Starting Streamlit UI     (port $FRONTEND_PORT)..."
"$VENV_PYTHON" -m streamlit run ui/streamlit_app.py \
    --server.port "$FRONTEND_PORT" \
    --server.headless true \
    --server.fileWatcherType none &>/dev/null &
FRONTEND_PID=$!

# Step 4: Wait for backend then open browser
echo "[3/3] Waiting for backend to be ready..."

ATTEMPTS=0
READY=0

while [ $ATTEMPTS -lt 40 ]; do
    sleep 1

    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo ""
        echo "[ERROR] Backend process exited unexpectedly."
        echo "        Check your .env file and make sure your API key is set correctly."
        exit 1
    fi

    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "$BACKEND_URL/health" 2>/dev/null)
    if [ "$STATUS" = "200" ]; then
        READY=1
        break
    fi

    ATTEMPTS=$((ATTEMPTS + 1))
done

if [ $READY -eq 0 ]; then
    echo ""
    echo "[ERROR] Backend did not respond after 40 seconds."
    echo "        It may still be starting. Try opening $FRONTEND_URL manually."
    echo ""
fi

echo ""
echo "  AutoDocX is running."
echo ""
echo "  UI  : $FRONTEND_URL"
echo "  API : $BACKEND_URL"
echo "  Docs: $BACKEND_URL/docs"
echo ""
echo "  Press Ctrl+C to stop everything."
echo ""

open "$FRONTEND_URL"

# Step 5: Keep alive and monitor
while true; do
    sleep 2

    if ! kill -0 "$BACKEND_PID" 2>/dev/null || ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo ""
        echo "[AutoDocX] A server process exited unexpectedly. Shutting down."
        break
    fi
done
