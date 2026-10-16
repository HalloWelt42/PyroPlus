# PyroPlus: Architektur ab Version 5

Dieses Dokument beschreibt den Zielzustand nach dem Umbau in Stufen. Es ist die
Arbeitsgrundlage; Abweichungen im Code sind Fehler, nicht Interpretationsspielraum.

## Leitsatz

Eine Wahrheit je Sache. Das Backend besitzt alle Daten des Displays und rendert
alle Bilder. Das Frontend bearbeitet das Modell über die Schnittstelle und zeigt,
was das Backend gerendert hat. Es gibt keinen zweiten Renderer, keine zweite
Schriftart, keinen zweiten Datenkatalog.

## Schichten

```
Oberfläche (Svelte 5, TypeScript)      bearbeitet Modell, zeigt Backend-Vorschau
        | HTTP (JSON) + WebSocket (Live-Zustand)
Backend (FastAPI)                      Modell, Katalog, Rendering, Persistenz
        | HTTP (JSON, Bilder)
Hardware-Proxy (nativ, systemd)        GPIO, I2C, SPI; LED-Animation lokal
```

## Backend: Bereich OLED

| Modul | Verantwortung |
|-------|---------------|
| `oled/models.py` | Pydantic-Modelle: Aufzählungen, Widget, Bildschirm, Einstellungen, Vorlage, Profil, Wetterort, Katalog, Render-Anfrage und -Antwort |
| `oled/values.py` | Registrierung der Datenquellen (`cpu.temp`, `wetter.temp`, ...) und Auflösung zu Werten; Simulation |
| `oled/modes.py` | Registrierung der Darstellungsarten (`zahl`, `balken`, `gauge`, ...) mit Vorgaben und Zeichenfunktion |
| `oled/compose.py` | Rendert einen Bildschirm: Widgets einzeln zeichnen, Rahmen messen, drehen, zusammensetzen |
| `oled/renderer.py`, `font.py`, `icons.py`, `sprites.py` | Pixel-Primitive auf dem 1-Bit-Puffer |
| `oled/builtin.py` | Fertige Bildschirmarten (Wetter kompakt, stündlich, täglich) |
| `oled/symbole.py`, `oled/symbole_daten.py` | Symbolbibliothek: Katalog (Kennung, Name, Gruppe, Glyphe) und erzeugte Pixeldaten in 8, 16, 24 und 32 Pixeln; Lüfter als 32 Drehbilder |
| `oled/templates.py` | Mitgelieferte Bildschirmvorlagen und Bausteine (Widgetvorlagen) |
| `oled/weather.py` | Wetteranbieter hinter einer Schnittstelle, mehrere Orte, Zwischenspeicher |
| `oled/store.py` | Persistenz als JSON-Dateien, atomar geschrieben; Migration alter Dateien |
| `oled/engine.py` | Render-Schleife, Rotation, Modus, Vorschau, Änderungszähler |
| `oled/api.py` | Router `/api/oled/...` |

### Datenmodell

- `Widget`: `id` (UUID), `source`, `display`, `x`, `y`, `name`, `opts`.
- `WidgetOpts`: Skalierung, Präfix, Suffix, Dezimalstellen, Tausendertrenner,
  invertiert, Rahmen, Ausrichtung, Boxbreite, Breite, Höhe, Radius, Größe, Text,
  Drehung, Wetterort, Bitmap, Symbol, Fläche, Stufen. Nur fachliche Werte, keine
  Editor-Hilfswerte.
- `Screen`: `id` (UUID), `name`, `kind` (widgets, weather_compact, weather_hourly,
  weather_daily), `widgets`, `locationId`, `enabled`, `duration`.
- `OledSettings`: Modus, Helligkeit, Rotationsintervall, aktiver Bildschirm,
  Bildschirme, Schemaversion.
- `WidgetPreset`, `Profile`, `WeatherLocation` sind eigene Dateien.

JSON-Feldnamen sind camelCase (Alias), Python-Attribute snake_case.

### Rendering

`compose.render_screen(screen, context)` zeichnet jedes Widget zuerst in einen
eigenen Puffer, misst den belegten Rahmen pixelgenau, dreht bei Bedarf und
kopiert in den Bildschirmpuffer. Ergebnis: Bild plus Liste `WidgetBox` je Widget.
Dieselbe Funktion bedient die Render-Schleife und den Entwurfs-Endpunkt
`POST /api/oled/render`; der Editor bekommt so exakte Trefferflächen.

### Vorschau einzelner Widgets

`POST /api/oled/render/widget` rendert ein Widget bei 0/0 und liefert das Bild
genau in der Größe seines Rahmens (`WidgetRenderResponse`: Bild, Breite, Höhe,
Rahmen). Jede Vorschau in der Oberfläche (Bausteinkacheln, Hinzufügen,
Symbolwahl) nimmt diesen Weg; die Oberfläche vergrößert nur ganzzahlig und
verzerrt nie. Ein Pixelbild belegt immer seine Zeichenfläche, auch leer, damit
es wählbar bleibt.

### Symbole

Alle Symbole haben eine Quelle: die Symbolschrift der Oberfläche
(`frontend/static/fonts/fa-solid-900.woff2`). `tools/symbole-erzeugen.py`
rastert die im Katalog (`oled/symbole.py`) genannten Glyphen in die festen
Größen und schreibt `oled/symbole_daten.py`; die Datei wird nicht von Hand
geändert. Das Lüftersymbol wird zusätzlich in 32 Drehbildern erzeugt. Zwei
Darstellungsarten nutzen die Bibliothek (`symbol`, `symbol_wert`), die
Wetterbildschirme ebenso. "Symbol + Wert" wählt ohne eigene Angabe das zur
Quelle passende Symbol (`vorgabe_fuer_quelle`).

### Persistenz

Dateien unter `data/`: `oled.json`, `oled_presets.json`, `oled_profiles.json`,
`weather.json`. Beim ersten Start mit altem Bestand wird `oled_settings.json`
(Schema 1) einmalig migriert; die alte Datei bleibt unangetastet.

### Live-Kanal

Der WebSocket sendet je Sekunde einen leichten Zustand: Modus, Helligkeit,
aktiver Bildschirm, Vorschaubild, `screensVersion`. Ändert sich die Version,
holt die Oberfläche die Bildschirme per HTTP. Polling ist nur Rückfall bei
getrenntem WebSocket.

## Versionierung

`version.json` im Wurzelverzeichnis ist die einzige Quelle. `tools/version.sh`
zählt hoch und spiegelt nach `frontend/package.json`. Der Git-Hook unter
`tools/git-hooks/pre-commit` erzwingt bei jedem Commit eine neue Version.
Backend, Frontend und Hardware-Proxy lesen die Datei zur Laufzeit.

## Oberfläche

`frontend/src` in Svelte 5 mit TypeScript. `lib/api` hält Typen und Client,
`lib/stores` den Live-Zustand (WebSocket) und den Display-Store (Entwurf,
Auswahl, Verlauf, Rendern, Speichern), `lib/display` den Editor, `lib/luefter`
und `lib/leds` die beiden anderen Bereiche, `lib/mobil` die eigenständige
Telefonansicht, `lib/hilfe` das schwebende Hilfefenster. `app.css` ist das
Design-System und entspricht `mockups/stil.css`.

Die Oberfläche rendert nichts selbst: jedes Bild kommt über `POST /api/oled/render`
vom Backend, zusammen mit den Rahmen der Widgets für Auswahl und Ziehen. Die
LED-Farben in der Seitenleiste sind die Farben, die die Hardware meldet.

## Stufen

1. Backend wird alleinige Wahrheit: Modell, Katalog, Render-Endpunkt, Migration. Erledigt.
2. Mockups, danach neuer Editor in Svelte 5 mit TypeScript, Lüfter und LEDs in derselben
   Gestaltung, Telefonansicht. Erledigt.
3. Betrieb bereinigen: Hardware-Proxy aus dem Repo, Dienstname, Compose, Anleitung.
