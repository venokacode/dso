#!/usr/bin/env bash
set -e

echo "==> Starting DSO Order System backend..."
cd "$(dirname "$0")/backend"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "==> Starting DSO Order System frontend..."
cd "$(dirname "$0")/frontend"
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo ""
echo "Backend  : http://localhost:8000"
echo "Frontend : http://localhost:5173"
echo "API Docs : http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
