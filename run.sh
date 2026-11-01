#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export DB_CONNECTION=sqlite
export DATABASE_PATH="${DATABASE_PATH:-$PWD/data/app.db}"
if ! command -v python3 >/dev/null; then echo 'Instale Python 3.12+.'; exit 1; fi
if [ ! -f .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
if [ "${1:-}" = '--seed' ]; then .venv/bin/python -m flask --app app init-db --seed; else .venv/bin/python -m flask --app app init-db; fi
command -v npm >/dev/null || { echo 'Instale Node.js 22+.'; exit 1; }
if [ ! -d frontend/node_modules/vite ]; then (cd frontend && npm install --no-audit --no-fund); fi
.venv/bin/python -m flask --app app run --host 127.0.0.1 --port 5000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT
printf 'Cozinha Mais: http://localhost:8080 (LAN: http://IP_DO_PC:8080)\n'
(cd frontend && npm run dev)
