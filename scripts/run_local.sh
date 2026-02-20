#!/usr/bin/env bash
set -euo pipefail

echo "Starting Rebot local stack..."

if [ ! -d "./backend/.venv" ]; then
  echo "Creating venv..."
  python -m venv ./backend/.venv
fi

echo "Installing backend requirements..."
./backend/.venv/bin/pip install -r ./backend/requirements.txt

echo "Starting backend..."
cd backend
./.venv/bin/python -m app.main &
BACKEND_PID=$!

echo "Starting worker..."
./.venv/bin/python -m app.worker &
WORKER_PID=$!
cd ..

if [ -f "./frontend/package.json" ]; then
  echo "Starting frontend..."
  cd frontend
  npm install
  npm run dev &
  FRONTEND_PID=$!
  cd ..
else
  echo "Frontend not found. Generate a workspace first."
fi

echo "Rebot running. Press Ctrl+C to stop."
wait $BACKEND_PID $WORKER_PID ${FRONTEND_PID:-}
