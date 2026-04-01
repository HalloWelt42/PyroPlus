# PironMan Deluxe v2.3.0 — Installationsanleitung

© HalloWelt42 — Nur für private Nutzung

## Übersicht

PironMan Deluxe ist ein umfassendes Steuerungs- und Monitoring-System für den
SunFounder PironMan 5 Case auf dem Raspberry Pi 5. Es besteht aus drei Komponenten:

| Komponente | Typ | Port | Funktion |
|------------|-----|------|----------|
| **Hardware-Proxy** | Nativer systemd-Service | 8072 | Direktzugriff auf GPIO, SPI, I²C |
| **Backend** | Docker-Container | 8071 | REST-API, WebSocket, Effekt-Engine |
| **Frontend** | Docker-Container | 8070 | Svelte 5 Web-Interface |

### Architektur

```
Svelte 5 Frontend (Port 8070, Nginx)
        ↕ HTTP / WebSocket
Docker Backend (Port 8071, FastAPI)
        ↕ HTTP (host.docker.internal:8072)
Hardware-Proxy (systemd, Port 8072, nativ)
        ↕ direkt
GPIO / I²C / SPI (Raspberry Pi 5)
```

---

## Voraussetzungen

- Raspberry Pi 5 (getestet mit 8 GB RAM)
- SunFounder PironMan 5 Case
- Raspberry Pi OS (Bookworm, 64-Bit)
- Docker und Docker Compose installiert
- Python 3.11+ (für Hardware-Proxy)

### Docker installieren (falls noch nicht vorhanden)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Neu einloggen!
```

---

## Schritt 1: SunFounder-Service deaktivieren

Der offizielle pironman5-Service muss gestoppt werden, da PironMan Deluxe
die Hardware selbst steuert. Die beiden Services kollidieren sonst.

```bash
sudo systemctl stop pironman5.service
sudo systemctl disable pironman5.service
```

**Prüfen:**
```bash
systemctl is-active pironman5.service
# Erwartet: inactive
```

**Hinweis:** Der pironman5-Service kann jederzeit wieder aktiviert werden:
```bash
sudo systemctl enable pironman5.service
sudo systemctl start pironman5.service
```

---

## Schritt 2: Dateien auf den Pi übertragen

Vom Entwicklungsrechner (Mac/PC):

```bash
scp ~/Downloads/pironman-deluxe-v2.3.0.zip pi@192.168.178.49:/tmp/
```

Auf dem Pi:

```bash
cd ~ && rm -rf pironman-deluxe
unzip /tmp/pironman-deluxe-v2.3.0.zip
rm /tmp/pironman-deluxe-v2.3.0.zip
```

---

## Schritt 3: Hardware-Proxy installieren

Der Hardware-Proxy läuft als nativer systemd-Service, weil Docker keinen
direkten Zugriff auf GPIO, SPI und I²C hat.

```bash
cd ~/pironman-deluxe/hardware-proxy
sudo bash install.sh
```

Das Install-Script:
- Installiert Systemabhängigkeiten (python3-venv, libgpiod2)
- Erstellt ein Python-venv unter `/opt/pironman-deluxe-hw/`
- Installiert die Python-Bibliotheken (gpiozero, neopixel_spi, luma.oled)
- Richtet den systemd-Service ein und startet ihn
- Stoppt den pironman5-Service (falls aktiv)

**Prüfen:**

```bash
curl http://localhost:8072/health
```

Erwartete Ausgabe:
```json
{"status":"ok","version":"2.2.0","fan":true,"fan_pwm":true,"oled":true,"leds":true}
```

**Logs anschauen:**
```bash
sudo journalctl -u pironman-deluxe-hw -f
```

---

## Schritt 4: Docker-Services starten

```bash
cd ~/pironman-deluxe
docker compose up -d --build
```

Beim ersten Start:
- Backend erzeugt automatisch einen API-Token
- Token wird in `/app/data/api_token.txt` gespeichert (Docker-Volume `pironman-data`)

**Prüfen:**

```bash
# Backend Health
curl http://localhost:8071/health

# Frontend
curl -s http://localhost:8070 | head -1
```

---

## Schritt 5: Frontend aufrufen

Im Browser öffnen:

```
http://192.168.178.49:8070
```

Das Frontend holt sich den API-Token automatisch beim Start.

---

## API-Token

Jede API-Anfrage (außer `/api/token` und `/health`) erfordert den Token.

### Token auslesen

```bash
docker exec pironman-deluxe-backend cat /app/data/api_token.txt
```

Oder im Frontend unter **Einstellungen → API-Zugang**.

### Token in Anfragen verwenden

```bash
TOKEN=$(docker exec pironman-deluxe-backend cat /app/data/api_token.txt)

curl -H "X-API-Token: $TOKEN" http://localhost:8071/api/state
```

### Token zurücksetzen

```bash
docker exec pironman-deluxe-backend rm /app/data/api_token.txt
docker compose restart backend
# Neuer Token wird generiert
```

---

## Custom Data API (Plugin-System)

Externe Scripte können eigene Daten ins Dashboard einblenden.
Die Daten werden per PUT registriert und im Frontend angezeigt.

### Beispiel: CPU-Temperatur-Logger

```bash
#!/bin/bash
TOKEN=$(docker exec pironman-deluxe-backend cat /app/data/api_token.txt)
TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
TEMP_C=$(echo "scale=1; $TEMP / 1000" | bc)

curl -s -X PUT http://localhost:8071/api/custom/cpu_temp_ext \
  -H "Content-Type: application/json" \
  -H "X-API-Token: $TOKEN" \
  -d "{\"label\":\"Externe Temp\",\"value\":\"$TEMP_C\",\"unit\":\"°C\",\"icon\":\"🌡️\"}"
```

### Beispiel: Pi-hole Statistiken

```bash
#!/bin/bash
TOKEN=$(docker exec pironman-deluxe-backend cat /app/data/api_token.txt)
BLOCKED=$(curl -s http://localhost/admin/api.php | python3 -c "import sys,json;print(json.load(sys.stdin)['ads_blocked_today'])")

curl -s -X PUT http://localhost:8071/api/custom/pihole \
  -H "Content-Type: application/json" \
  -H "X-API-Token: $TOKEN" \
  -d "{\"label\":\"Pi-hole Blocked\",\"value\":\"$BLOCKED\",\"unit\":\"heute\",\"icon\":\"🛡️\"}"
```

### Als Cronjob einrichten

```bash
crontab -e
# Alle 5 Minuten:
*/5 * * * * /home/pi/scripts/pihole-stats.sh
```

---

## Hardware-Details

### Lüfter (PWM Fan)

- **Typ:** Kernel-gesteuerter PWM-Fan mit 4 Stufen
- **GPIO:** Pin 6 (On/Off) + Pin 5 (Status-LED)
- **Kernel-Interface:** `/sys/class/thermal/cooling_device0/cur_state` (0-3)
- **RPM-Sensor:** `/sys/devices/platform/cooling_fan/hwmon/*/fan1_input`
- **Stufen:** 0=Aus, 1=Leise (~30%), 2=Mittel (~60%), 3=Voll (100%)

### WS2812B LEDs (4 Stück)

- **Ansteuerung:** `neopixel_spi` über `/dev/spidev0.0`
- **Pixel-Order:** GRB
- **Frequenz:** 6.4 MHz (800 kHz NeoPixels)
- **Helligkeit:** Muss explizit gesetzt werden (Default: 0)

### OLED Display (SSD1306)

- **Auflösung:** 128×64 Pixel
- **Interface:** I²C (Adresse 0x3C)
- **Bibliothek:** luma.oled

### Wichtig: gpiochip-Symlink

Der Pi 5 nutzt den RP1-Chip auf `gpiochip4`, aber `gpiozero` erwartet
`gpiochip0`. Der Hardware-Proxy erstellt automatisch einen Symlink:

```bash
ln -sf /dev/gpiochip4 /dev/gpiochip0
```

---

## Ports und Services

| Port | Service | Beschreibung |
|------|---------|--------------|
| 8070 | Frontend (Nginx) | Web-Interface |
| 8071 | Backend (FastAPI) | REST-API + WebSocket |
| 8072 | Hardware-Proxy | Nativer Hardware-Zugriff |
| 8060 | WeatherCache (optional) | Wetter-Daten |

---

## API-Referenz (Auszug)

Vollständige Dokumentation: `http://PI_IP:8071/docs` (Swagger-UI)

### System
- `GET /api/state` — Kompletter Systemstatus
- `GET /api/stats` — Nur Systemstatistiken

### Lüfter
- `POST /api/fan/mode/{auto|manual|off}` — Modus setzen
- `POST /api/fan/profile/{silent|balanced|performance|night}` — Profil wählen
- `POST /api/fan/manual-speed` — Manuell (Body: `{"speed": 60}`)

### LEDs
- `GET /api/leds/effects` — Verfügbare Effekte
- `POST /api/leds/effect/{name}` — Effekt aktivieren
- `POST /api/leds/color` — Farbe (Body: `{"r":255,"g":0,"b":128}`)
- `POST /api/leds/brightness/{0-255}` — Helligkeit

### OLED
- `POST /api/oled/mode/{auto|manual|off}` — Modus
- `POST /api/oled/brightness/{0-255}` — Helligkeit
- `POST /api/oled/rotation/{sekunden}` — Rotations-Intervall

### Custom Data
- `PUT /api/custom/{key}` — Datenquelle registrieren
- `GET /api/custom` — Alle Datenquellen abrufen
- `DELETE /api/custom/{key}` — Datenquelle entfernen

---

## Updates

### Nur Frontend/Backend aktualisieren (Docker)

```bash
# ZIP hochladen und entpacken
cd ~/pironman-deluxe
docker compose down
# Neue Dateien entpacken...
docker compose up -d --build
```

**Achtung:** Das `pironman-data` Docker-Volume bleibt erhalten (Einstellungen,
API-Token, Profile). Es wird NICHT gelöscht.

### Hardware-Proxy aktualisieren

```bash
cd ~/pironman-deluxe/hardware-proxy
sudo bash install.sh
```

---

## Fehlerbehebung

### Hardware-Proxy startet nicht

```bash
sudo journalctl -u pironman-deluxe-hw -n 50
```

Häufige Ursachen:
- pironman5-Service läuft noch → `sudo systemctl stop pironman5.service`
- SPI nicht aktiviert → `sudo raspi-config` → Interfacing Options → SPI → Enable
- I²C nicht aktiviert → `sudo raspi-config` → Interfacing Options → I²C → Enable

### LEDs leuchten nicht

1. Helligkeit prüfen (Default kann 0 sein):
   ```bash
   curl -X POST http://localhost:8072/leds/brightness -d '{"value":128}'
   ```
2. Dann Farbe setzen:
   ```bash
   curl -X POST http://localhost:8072/leds/set -d '{"leds":[{"r":255,"g":0,"b":0},{"r":0,"g":255,"b":0},{"r":0,"g":0,"b":255},{"r":255,"g":255,"b":0}]}'
   ```

### Backend kann Hardware-Proxy nicht erreichen

```bash
docker exec pironman-deluxe-backend python3 -c "
import httpx
print(httpx.get('http://host.docker.internal:8072/health').json())
"
```

Falls "Connection refused": Hardware-Proxy muss auf `0.0.0.0` hören (nicht `127.0.0.1`).

```bash
grep "host=" /opt/pironman-deluxe-hw/main.py
# Muss sein: host="0.0.0.0"
```

### Docker-Container Logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

---

## Deinstallation

```bash
# Docker-Services stoppen
cd ~/pironman-deluxe
docker compose down -v  # -v löscht auch das Volume!

# Hardware-Proxy entfernen
sudo systemctl stop pironman-deluxe-hw
sudo systemctl disable pironman-deluxe-hw
sudo rm /etc/systemd/system/pironman-deluxe-hw.service
sudo rm -rf /opt/pironman-deluxe-hw

# Optional: SunFounder-Service wieder aktivieren
sudo systemctl enable pironman5.service
sudo systemctl start pironman5.service

# Projektordner entfernen
rm -rf ~/pironman-deluxe
```

---

## Lizenz

Private Nutzung. Keine kommerzielle Nutzung gestattet.
© HalloWelt42
