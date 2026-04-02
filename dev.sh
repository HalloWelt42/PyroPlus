#!/bin/bash
# PyroPlus — Live-Entwicklung starten
# Startet den Vite Dev-Server mit Hot-Reload
# Erreichbar vom Mac unter: http://192.168.178.49:5173
#
# Backend läuft weiter im Docker-Container auf Port 8071
# API-Calls werden automatisch dorthin weitergeleitet

cd "$(dirname "$0")/frontend"

echo "═══════════════════════════════════════"
echo "  PyroPlus — Live-Entwicklung"
echo "═══════════════════════════════════════"
echo ""
echo "  Dev-Server: http://192.168.178.49:5173"
echo "  Produktion: http://192.168.178.49:8070"
echo ""
echo "  Jede Änderung an .svelte/.css/.js"
echo "  wird sofort im Browser sichtbar."
echo ""
echo "  Beenden mit Strg+C"
echo "═══════════════════════════════════════"
echo ""

npx vite
