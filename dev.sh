#!/bin/bash
# PyroPlus — Entwicklungsumgebung starten
set -e
cd "$(dirname "$0")"

echo "═══════════════════════════════════════"
echo "  PyroPlus — Entwicklungsumgebung"
echo "═══════════════════════════════════════"

# Backend prüfen/starten
if ! curl -s http://localhost:8071/health > /dev/null 2>&1; then
    echo "  Backend starten..."
    docker compose up -d --build
    echo "  Warte auf Backend..."
    for i in $(seq 1 15); do
        curl -s http://localhost:8071/health > /dev/null 2>&1 && break
        sleep 1
    done
fi
echo "  Backend:  http://localhost:8071 ✓"

# Hardware-Proxy prüfen
if curl -s http://localhost:8072/health > /dev/null 2>&1; then
    echo "  Hardware: http://localhost:8072 ✓"
else
    echo "  Hardware: nicht erreichbar ✗"
fi

echo ""
echo "  Dev-Server: http://192.168.178.49:5173"
echo "  Produktion: http://192.168.178.49:8070"
echo ""
echo "  WebSocket verbindet direkt auf :8071"
echo "  Docker-Rebuilds unterbrechen NICHT die Entwicklung"
echo ""
echo "  Beenden mit Strg+C"
echo "═══════════════════════════════════════"
echo ""

cd frontend
exec npx vite
