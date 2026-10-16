# PyroPlus: Anleitung

PyroPlus steuert das Zubehör eines Raspberry-Pi-5-Gehäuses: den Lüfter, vier
adressierbare LEDs und ein kleines Display mit 128 mal 64 Pixeln. Die Oberfläche
läuft im Browser, auch am Telefon.

## Aufbau

| Teil | Art | Port | Aufgabe |
|------|-----|------|---------|
| Hardware-Proxy | nativer systemd-Dienst | 8072 | Zugriff auf GPIO, I2C und SPI; LED-Animation läuft hier |
| Backend | Docker-Container | 8071 | Schnittstelle, WebSocket, Lüfterregelung, Display-Rendering |
| Oberfläche | Docker-Container | 8070 | Weboberfläche |

Das Backend besitzt alle Daten (Bildschirme, Bausteine, Profile, Wetterorte) und
rendert jedes Bild für das Display. Die Oberfläche zeigt nur, was das Backend
liefert. Alle Daten liegen unter `data/` im Projektordner.

## Voraussetzungen

- Raspberry Pi 5 mit Raspberry Pi OS (64 Bit)
- Docker und Docker Compose
- Python 3.11 oder neuer für den Hardware-Proxy
- SPI und I2C aktiviert (`raspi-config`, Schnittstellen)

## Installation

```bash
git clone <Adresse-des-Repos> ~/PyroPlus
cd ~/PyroPlus
sudo bash hardware-proxy/install.sh
docker compose up -d --build
```

Der Installer des Hardware-Proxys stoppt frühere Dienste, die dieselbe Hardware
ansprechen, legt die Python-Umgebung unter `/opt/pyroplus-hw` an und richtet den
Dienst `pyroplus-hw` ein.

Danach die Oberfläche im Browser öffnen: `http://<Adresse-des-Pi>:8070`.

Beim ersten Start mit einem Bestand einer früheren Version wandelt das Backend
die Datei `data/oled_settings.json` einmalig in das neue Format um; die alte Datei
bleibt unverändert liegen. Hat die frühere Oberfläche Daten im Browser gespeichert,
bietet das Fenster "Profile" an, sie zu übernehmen.

## Aktualisieren

```bash
cd ~/PyroPlus
git pull
docker compose up -d --build
sudo bash hardware-proxy/install.sh
```

Der letzte Schritt ist nur nötig, wenn sich der Hardware-Proxy geändert hat.
Die laufende Version steht in der Seitenleiste der Oberfläche und unter
`http://<Adresse-des-Pi>:8071/health`.

## Bedienung

Die Hilfe in der Oberfläche (Fragezeichen oben rechts) erklärt jeden Bereich und
ist durchsuchbar. Kurz:

- **Lüfter**: Gehäuselüfter schaltet nach Schwellwerten, der CPU-Lüfter folgt einer
  Temperaturkurve mit Profilen. Simulation prüft das Verhalten bei angenommener
  Temperatur.
- **LEDs**: Temperaturfarbe oder Effekte; Helligkeit, Tempo, Farben je LED.
- **Display**: Bildschirme aus Widgets zusammenstellen, Vorlagen und Bausteine
  einfügen, Pixelbilder zeichnen, Wetterorte verwalten, Profile sichern.

## Schnittstelle

Die Dokumentation der Schnittstelle liegt unter `http://<Adresse-des-Pi>:8071/docs`.
Jede Anfrage außer `/api/token` und `/health` braucht den Kopf `X-API-Token`.
Der Token steht in `data/api_token.txt`; löschen und Backend neu starten erzeugt
einen neuen.

Beispiel: alle Bildschirme abrufen

```bash
TOKEN=$(cat data/api_token.txt)
curl -H "X-API-Token: $TOKEN" http://localhost:8071/api/oled/screens
```

Externe Skripte können über `PUT /api/custom/{schluessel}` eigene Werte melden.

## Sicherung

Im Fenster "Profile" exportiert die Oberfläche alle Display-Daten als eine Datei
und liest sie wieder ein. Unabhängig davon genügt eine Kopie des Ordners `data/`.

## Hardware

- **Lüfter**: PWM über den Kernel (`/sys/devices/platform/cooling_fan`), Drehzahl aus
  `fan1_input`; Gehäuselüfter über GPIO 6 (An/Aus), Statusleuchte GPIO 5.
- **LEDs**: vier WS2812B über SPI (`/dev/spidev0.0`), Farbfolge GRB.
- **Display**: SSD1306 mit 128 mal 64 Pixeln über I2C, Adresse 0x3C.
- Auf dem Pi 5 erwartet die GPIO-Bibliothek `gpiochip0`; der Proxy legt bei Bedarf
  einen Verweis auf `gpiochip4` an.

## Entwicklung

```bash
tools/entwicklung.sh
```

Startet das Backend lokal ohne Hardware (Datenordner `backend/data`) und die
Oberfläche mit Vite unter `http://localhost:5173`. Tests:

```bash
cd backend && .venv/bin/python -m pytest
cd frontend && npm run check && npm run build
```

Die Version wird nur in `version.json` gepflegt (`tools/version.sh`); ein Git-Hook
erhöht sie bei jedem Commit. Mockups der Oberfläche liegen unter `mockups/`,
die Architektur ist in `docs/ARCHITEKTUR.md` beschrieben.

Die Symbole des Displays werden aus der Symbolschrift der Oberfläche erzeugt.
Nach einer Änderung am Katalog in `backend/oled/symbole.py`:

```bash
backend/.venv/bin/python tools/symbole-erzeugen.py
```

Das schreibt `backend/oled/symbole_daten.py` neu; die Werkzeuge dafür stehen in
`backend/requirements-dev.txt`.

Die Bilder der README entstehen reproduzierbar aus der laufenden Oberfläche:
`tools/bilder/vorbereiten.py` stellt Beispielbildschirme aus den Vorlagen zusammen
(nur lesend, der Bestand auf dem Pi bleibt unberührt), `tools/bilder/aufnehmen.mjs`
nimmt die Szenen kopflos auf, `tools/bilder/zusammensetzen.py` montiert die Tafeln
nach `.github/bilder`. `tools/bilder/qa-shot.mjs` macht eine einzelne Prüfaufnahme.

## Fehlersuche

- `journalctl -u pyroplus-hw -n 50` zeigt das Protokoll des Hardware-Proxys.
- `docker compose logs -f backend` zeigt das Backend.
- Meldet die Oberfläche "Kein Display" oder "Keine LEDs", antwortet der Proxy nicht:
  `curl http://localhost:8072/health` auf dem Pi prüfen.
- Läuft noch ein anderer Dienst für dasselbe Gehäuse, kollidieren beide am Bus;
  der Installer deaktiviert bekannte Dienste.

## Lizenz

Siehe Datei `LICENSE`. Die Displaysymbole werden aus der mitgelieferten
Symbolschrift (Font Awesome Free, Symbole CC BY 4.0, Schrift SIL OFL 1.1)
gerastert.
