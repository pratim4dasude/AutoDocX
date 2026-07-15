#!/bin/bash
# Force stop all AutoDocX processes on macOS

BACKEND_PORT=7832
FRONTEND_PORT=7833
FOUND=0

echo ""
echo "============================================"
echo "           Stopping AutoDocX"
echo "============================================"
echo ""

for PORT in $BACKEND_PORT $FRONTEND_PORT; do
    PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null)
    if [ -n "$PIDS" ]; then
        FOUND=1
        echo "Stopping process on port $PORT (PID $PIDS)..."
        echo "$PIDS" | xargs kill -9 2>/dev/null
    fi
done

if [ $FOUND -eq 0 ]; then
    echo "No AutoDocX processes found on ports $BACKEND_PORT or $FRONTEND_PORT."
else
    echo "Done."
fi

echo ""
