#!/bin/bash
# PyroPlus Hardware-Proxy installieren oder aktualisieren.
# Aufruf im Projektordner: sudo bash hardware-proxy/install.sh
set -e

HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WURZEL="$(cd "$HIER/.." && pwd)"
INSTALL_DIR="/opt/pyroplus-hw"
SERVICE_NAME="pyroplus-hw"
ALTE_DIENSTE="pironman-deluxe-hw pironman5"

if [ "$EUID" -ne 0 ]; then
    echo "Bitte als root ausführen: sudo bash hardware-proxy/install.sh"
    exit 1
fi

echo "PyroPlus Hardware-Proxy: Installation nach $INSTALL_DIR"

# Frühere Dienste stoppen; sie greifen auf dieselbe Hardware zu
for dienst in $ALTE_DIENSTE; do
    if systemctl list-unit-files "$dienst.service" >/dev/null 2>&1 && systemctl is-enabled --quiet "$dienst" 2>/dev/null; then
        echo "Alter Dienst $dienst wird gestoppt und deaktiviert"
        systemctl stop "$dienst" || true
        systemctl disable "$dienst" || true
    fi
done
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    systemctl stop "$SERVICE_NAME"
fi

echo "Systempakete prüfen"
apt-get install -y -q python3-venv python3-dev libgpiod2 >/dev/null 2>&1 || true

mkdir -p "$INSTALL_DIR/data"
cp "$HIER/main.py" "$HIER/led_engine.py" "$HIER/requirements.txt" "$INSTALL_DIR/"
cp "$WURZEL/version.json" "$INSTALL_DIR/version.json"

# Vorhandene Umgebung eines früheren Standorts übernehmen, spart Minuten auf dem Pi
if [ ! -d "$INSTALL_DIR/venv" ] && [ -d /opt/pironman-deluxe-hw/venv ]; then
    echo "Übernehme Python-Umgebung des früheren Dienstes"
    mv /opt/pironman-deluxe-hw/venv "$INSTALL_DIR/venv"
fi
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "Erstelle Python-Umgebung (einige Minuten)"
    python3 -m venv "$INSTALL_DIR/venv"
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
fi
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

cp "$HIER/pyroplus-hw.service" /etc/systemd/system/
rm -f /etc/systemd/system/pironman-deluxe-hw.service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME" >/dev/null
systemctl restart "$SERVICE_NAME"

sleep 3
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "Hardware-Proxy läuft: $(curl -s http://localhost:8072/health)"
else
    echo "Dienst gestartet, aber nicht aktiv. Protokoll: journalctl -u $SERVICE_NAME -n 30"
    exit 1
fi
