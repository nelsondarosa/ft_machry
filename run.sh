#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
PYTHON=""
if [[ ! -x .venv/bin/python ]]; then
  for candidate in python3.13 python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; assert sys.version_info >= (3,12)' >/dev/null 2>&1; then
      PYTHON="$candidate"; break
    fi
  done
  if [[ -z "$PYTHON" ]]; then echo '[ERRO] Python 3.12+ necessario.' >&2; exit 1; fi
  echo '[1/4] Criando ambiente virtual...'
  "$PYTHON" -m venv .venv
fi
echo '[2/4] Instalando dependencias...'
.venv/bin/python -m pip install -r requirements.txt
export DATABASE_PATH="${DATABASE_PATH:-$(pwd)/data/app.db}"
echo '[3/4] Verificando banco SQLite...'
if [[ "${1:-}" == '--seed' ]]; then
  .venv/bin/python -m flask --app app init-db --seed
else
  .venv/bin/python -m flask --app app init-db
fi
echo '[4/4] Iniciando API em http://127.0.0.1:5000 (Ctrl+C para parar)'
echo 'Frontend: execute "pnpm dev" dentro da pasta frontend'
exec .venv/bin/python -m flask --app app run --host 127.0.0.1 --port 5000
