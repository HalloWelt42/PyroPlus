#!/usr/bin/env bash
# Entwicklung am Rechner: Backend ohne Hardware und Oberfläche mit Vite.
# Aufruf: tools/entwicklung.sh [Datenordner]
set -euo pipefail
WURZEL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATEN="${1:-$WURZEL/backend/data}"
mkdir -p "$DATEN"

if [ ! -x "$WURZEL/backend/.venv/bin/python" ]; then
  echo "Python-Umgebung anlegen ..."
  (cd "$WURZEL/backend" && python3 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt)
fi
if [ ! -d "$WURZEL/frontend/node_modules" ]; then
  echo "Pakete der Oberfläche installieren ..."
  (cd "$WURZEL/frontend" && npm install --no-audit --no-fund)
fi

echo "Backend ohne Hardware auf :8071, Daten unter $DATEN"
(cd "$WURZEL/backend" && HW_PROXY_URL=none DATA_DIR="$DATEN" .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8071 --log-level warning) &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null || true' EXIT

echo "Oberfläche auf http://localhost:5173 (Strg+C beendet beides)"
cd "$WURZEL/frontend" && npx vite
