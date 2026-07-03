#!/usr/bin/env bash
# One-command local run (no Docker): build the frontend, then start the backend
# which serves it single-origin at http://127.0.0.1:8765.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Building frontend"
cd frontend
if command -v pnpm >/dev/null 2>&1; then
  pnpm install
  pnpm build
else
  npm install
  npm run build
fi
cd ..

echo "==> Preparing backend"
cd backend
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -e .

echo "==> Starting server on http://127.0.0.1:8765"
python run.py
