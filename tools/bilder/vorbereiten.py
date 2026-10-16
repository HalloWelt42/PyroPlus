"""Bereitet die Szenen für die README-Aufnahmen vor.

Aufruf: backend/.venv/bin/python tools/bilder/vorbereiten.py http://<pi>:8071

Holt den echten Zustand vom Pi, ersetzt nur in der Antwort (nie auf dem Pi) die
Bildschirme durch Vorlagen plus ein Pixel-Logo und ermittelt über den Render-Endpunkt
die Rahmen der Widgets, damit die Aufnahme gezielt klicken kann.
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WURZEL / "backend"))

from oled import templates  # noqa: E402
from oled.modes import pack_bitmap  # noqa: E402
from oled.models import Widget, Screen, DisplayMode  # noqa: E402

PI = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else sys.exit("Adresse des Backends angeben, zum Beispiel http://<pi>:8071")
ZIEL = Path(__file__).parent / "szenen.json"


def api(pfad: str, token: str | None = None, daten: dict | None = None) -> dict | list:
    req = urllib.request.Request(PI + pfad, method="POST" if daten is not None else "GET")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-API-Token", token)
    body = json.dumps(daten).encode() if daten is not None else None
    with urllib.request.urlopen(req, body, timeout=15) as antwort:
        return json.load(antwort)


def flamme() -> tuple[str, int, int]:
    """Die Flamme des Tab-Symbols als 1-Bit-Pixelbild, auf den Inhalt zugeschnitten."""
    from PIL import Image

    bild = Image.open(WURZEL / "frontend/static/icon-192.png").convert("L").resize((44, 44), Image.LANCZOS)
    rows = [[1 if bild.getpixel((x, y)) > 200 else 0 for x in range(bild.width)] for y in range(bild.height)]
    ys = [y for y, z in enumerate(rows) if any(z)]
    xs = [x for z in rows for x, p in enumerate(z) if p]
    rows = [z[min(xs):max(xs) + 1] for z in rows[min(ys):max(ys) + 1]]
    return pack_bitmap(rows), len(rows[0]), len(rows)


def logo_bildschirm(text_quelle: str) -> Screen:
    daten, breite, hoehe = flamme()
    s = templates.screen_template("minimal")
    assert s is not None
    s.name = "Logo"
    s.widgets = [
        Widget(source="layout.bitmap", display=DisplayMode.bitmap, x=8, y=6, name="Flamme",
               opts={"width": breite, "height": hoehe, "bitmap": daten}),
        Widget(source=text_quelle, display=DisplayMode.text, x=34, y=14, name="Titel",
               opts={"text": "PyroPlus", "scaleX": 2, "scaleY": 2}),
        Widget(source=text_quelle, display=DisplayMode.text, x=4, y=50, name="Untertitel",
               opts={"text": "Display Luefter LEDs", "scaleX": 1, "scaleY": 1}),
    ]
    return templates._frische_ids(s)


def main() -> None:
    token = api("/api/token")["token"]
    zustand = api("/api/oled", token)
    titel = templates.widget_template("titelzeile")
    assert titel is not None
    text_quelle = titel.source
    print("Textquelle:", text_quelle)

    auswahl = [("system", "System"), ("grosse_uhr", "Uhr"), ("messuhren", "Messuhren"),
               ("luefter", "Lüfter"), ("laufwerke", "Laufwerke")]
    screens: list[Screen] = []
    for vorlage, name in auswahl:
        s = templates.screen_template(vorlage)
        assert s is not None, vorlage
        s.name = name
        if vorlage == "system":
            s.widgets = [w for w in s.widgets if not w.source.startswith("net.")]
            last = templates.widget_template("last")
            assert last is not None
            last.x, last.y, last.opts.size, last.opts.prefix = 0, 56, 8, "Last "
            s.widgets.append(last)
        screens.append(s)
    screens.append(logo_bildschirm(text_quelle))
    # Der erste Bildschirm übernimmt die Kennung des Bildschirms, der gerade auf dem Display liegt,
    # damit Rechner und Telefon ihn als aktiv zeigen.
    if zustand.get("currentScreenId"):
        screens[0].id = zustand["currentScreenId"]

    klickziele: dict[str, dict] = {}
    vorschau = ""
    gewuenscht = {"System": "Temp-Balken", "Logo": "Flamme"}
    for s in screens:
        antwort = api("/api/oled/render", token, {"screen": s.model_dump(by_alias=True, mode="json")})
        boxen = antwort["boxes"]
        print(f"{s.name}: " + ", ".join(f"{(w.name or w.source)}@{b['x']},{b['y']} {b['w']}x{b['h']}" for w, b in zip(s.widgets, boxen)))
        if s.name == "System":
            vorschau = antwort["imageBase64"]
        if s.name in gewuenscht:
            ziel_name = gewuenscht[s.name]
            widget = next((w for w in s.widgets if ziel_name.lower() in (w.name or "").lower()), None)
            if widget is None:
                widget = next((w for w in s.widgets if ziel_name.lower() in w.source.lower()), s.widgets[0])
            box = next(b for b in boxen if b["id"] == widget.id)
            klickziele[s.name] = {"widget": widget.id, "cx": box["x"] + box["w"] / 2, "cy": box["y"] + box["h"] / 2}
            print(f"Klickziel {s.name}: {widget.name or widget.source} bei {box}")
    zustand["screens"] = [s.model_dump(by_alias=True, mode="json") for s in screens]
    zustand["preview"] = vorschau
    ZIEL.write_text(json.dumps({"zustand": zustand, "klickziele": klickziele, "vorschau": vorschau}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(screens)} Bildschirme nach {ZIEL}")


if __name__ == "__main__":
    main()
