#!/bin/bash
# PyroPlus — Hardware-Proxy Installer
# Muss als root ausgeführt werden: sudo bash install.sh
set -e

INSTALL_DIR="/opt/pyroplus-hw"
SERVICE_NAME="pyroplus-hw"

echo "╔══════════════════════════════════════════╗"
echo "║    PyroPlus Hardware-Proxy Install       ║"
echo "╚══════════════════════════════════════════╝"

if [ "$EUID" -ne 0 ]; then
    echo "Bitte als root ausführen: sudo bash install.sh"
    exit 1
fi

# Pironman5 deaktivieren falls aktiv
if systemctl is-active --quiet pironman5 2>/dev/null; then
    echo "→ pironman5 Service wird deaktiviert..."
    systemctl stop pironman5
    systemctl disable pironman5
    echo "  ✓ pironman5 gestoppt und deaktiviert"
fi

# Alten Proxy stoppen falls vorhanden
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "→ Alter Proxy wird gestoppt..."
    systemctl stop "$SERVICE_NAME"
fi

# System-Dependencies
echo "→ System-Dependencies prüfen..."
apt-get install -y -q python3-venv python3-dev libgpiod2 2>/dev/null || true

# Installationsverzeichnis
echo "→ Installiere nach $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/data"
cp main.py "$INSTALL_DIR/"
cp led_engine.py "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

# Virtualenv (nur erstellen wenn nicht vorhanden)
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "→ Erstelle Virtual Environment..."
    python3 -m venv "$INSTALL_DIR/venv"
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
    echo "→ Installiere Pakete (kann 2-4 Min dauern)..."
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
else
    echo "→ Venv existiert, aktualisiere Pakete..."
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
fi

# systemd Service
echo "→ Installiere systemd Service..."
cp pyroplus-hw.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

# Kurz warten und Status prüfen
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo ""
    echo "✓ Hardware-Proxy installiert und läuft"
else
    echo ""
    echo "✗ Service gestartet aber möglicherweise Fehler"
    echo "  Logs prüfen: journalctl -u $SERVICE_NAME --no-pager -n 20"
fi

echo ""
echo "  Status:  systemctl status $SERVICE_NAME"
echo "  Logs:    journalctl -u $SERVICE_NAME -f"
echo "  Test:    curl http://localhost:8072/health"
echo ""
