"""
PyroPlus: Migration des alten Bestands (Schema 1) in das Modell ab Version 5.

Alt: oled_settings.json mit Bildschirmtypen system, clock, weather_*, pixel_art,
marquee; Widgets entweder als source+display+opts oder als type-basierte
Altwidgets. Dazu optional frontend_backup.json (Städte, Vorlagen, Profile) und
pixel_screens/*.json (Pixelbilder).

Neu: Bildschirme mit UUID, Widgets mit vereinheitlichten Darstellungsarten,
Pixelbilder als Bitmap-Widgets, Wetterorte und Vorlagen im Backend.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from oled.models import (
    DisplayMode, OledMode, OledSettings, Profile, Screen, ScreenKind, WeatherLocation,
    WeatherSettings, Widget, WidgetOpts, WidgetPreset, neue_id, W, H,
)
from oled.modes import pack_bitmap

logger = logging.getLogger("oled.migrate")


@dataclass
class MigrationResult:
    settings: OledSettings
    presets: list[WidgetPreset] = field(default_factory=list)
    profiles: list[Profile] = field(default_factory=list)
    weather: WeatherSettings = field(default_factory=WeatherSettings)


# Darstellungsart alt -> (neu, Zusatzoptionen falls nicht gesetzt)
DISPLAY_MAP: dict[str, tuple[DisplayMode, dict[str, Any]]] = {
    "zahl": (DisplayMode.text, {"scaleX": 1, "scaleY": 1}),
    "zahl_gross": (DisplayMode.text, {"scaleX": 2, "scaleY": 2}),
    "zahl_xl": (DisplayMode.text, {"scaleX": 3, "scaleY": 3}),
    "zahl_xxl": (DisplayMode.text, {"scaleX": 4, "scaleY": 4}),
    "zahl_breit": (DisplayMode.text, {"scaleX": 2, "scaleY": 1}),
    "zahl_hoch": (DisplayMode.text, {"scaleX": 1, "scaleY": 2}),
    "zahl_x3y1": (DisplayMode.text, {"scaleX": 3, "scaleY": 1}),
    "zahl_x1y3": (DisplayMode.text, {"scaleX": 1, "scaleY": 3}),
    "text": (DisplayMode.text, {"scaleX": 1, "scaleY": 1}),
    "text_gross": (DisplayMode.text, {"scaleX": 2, "scaleY": 2}),
    "text_xl": (DisplayMode.text, {"scaleX": 3, "scaleY": 3}),
    "text_invertiert": (DisplayMode.text_invertiert, {"scaleX": 1, "scaleY": 1, "invert": True}),
    "text_inv_gross": (DisplayMode.text_invertiert, {"scaleX": 2, "scaleY": 2, "invert": True}),
    "text_inv_xl": (DisplayMode.text_invertiert, {"scaleX": 3, "scaleY": 3, "invert": True}),
    "text_rahmen": (DisplayMode.text_rahmen, {"scaleX": 1, "scaleY": 1, "border": True}),
    "text_rahmen_gross": (DisplayMode.text_rahmen, {"scaleX": 2, "scaleY": 2, "border": True}),
    "balken": (DisplayMode.balken, {"width": 60, "height": 6}),
    "balken_schmal": (DisplayMode.balken, {"width": 40, "height": 3}),
    "balken_breit": (DisplayMode.balken, {"width": 80, "height": 8}),
    "balken_hoch": (DisplayMode.balken, {"width": 60, "height": 12}),
    "balken_voll": (DisplayMode.balken, {"width": 126, "height": 6}),
    "balken_label": (DisplayMode.balken_label, {"width": 50, "height": 6}),
    "balken_label_in": (DisplayMode.balken_label_in, {"width": 60, "height": 9}),
    "gauge": (DisplayMode.gauge, {"radius": 12}),
    "gauge_gross": (DisplayMode.gauge, {"radius": 20}),
    "gauge_xl": (DisplayMode.gauge, {"radius": 28}),
    "sparkline": (DisplayMode.sparkline, {"width": 50, "height": 16}),
    "sparkline_gross": (DisplayMode.sparkline, {"width": 80, "height": 24}),
    "sparkline_breit": (DisplayMode.sparkline, {"width": 100, "height": 16}),
    "sparkline_voll": (DisplayMode.sparkline, {"width": 126, "height": 30}),
    "laufschrift": (DisplayMode.laufschrift, {}),
    "fan_icon": (DisplayMode.fan_icon, {"size": 8}),
    "fan_icon_gross": (DisplayMode.fan_icon, {"size": 16}),
    "fan_icon_xl": (DisplayMode.fan_icon, {"size": 24}),
    "fan_icon_rpm": (DisplayMode.fan_icon_rpm, {"size": 16}),
    "linie_h": (DisplayMode.linie_h, {"width": 60}),
    "linie_v": (DisplayMode.linie_v, {"height": 20}),
    "rahmen": (DisplayMode.rahmen, {"width": 40, "height": 20}),
    "rahmen_shape": (DisplayMode.rahmen, {"width": 40, "height": 20}),
    "block": (DisplayMode.block, {"width": 40, "height": 20}),
    "section": (DisplayMode.section, {"width": 60}),
    "bitmap": (DisplayMode.bitmap, {}),
}

# Älteste Widgets (type-basiert) -> (Quelle, Darstellungsart, Zusatzoptionen)
LEGACY_TYPE_MAP: dict[str, tuple[str, DisplayMode, dict[str, Any]]] = {
    "clock": ("zeit.uhr", DisplayMode.text, {"scaleX": 2, "scaleY": 2}),
    "clock_s": ("zeit.uhr_s", DisplayMode.text, {}),
    "clock_l": ("zeit.uhr", DisplayMode.text, {"scaleX": 3, "scaleY": 3}),
    "date": ("zeit.datum", DisplayMode.text, {}),
    "weekday": ("zeit.tag", DisplayMode.text, {}),
    "cpu_temp": ("cpu.temp", DisplayMode.text, {"suffix": "°", "decimals": 0}),
    "cpu_pct": ("cpu.percent", DisplayMode.text, {"suffix": "%"}),
    "cpu_cores": ("cpu.cores", DisplayMode.text, {}),
    "cpu_bar": ("cpu.percent", DisplayMode.balken, {}),
    "ram_used": ("ram.used", DisplayMode.text, {"suffix": " G"}),
    "ram_total": ("ram.total", DisplayMode.text, {"suffix": " G"}),
    "ram_pct": ("ram.percent", DisplayMode.text, {"suffix": "%"}),
    "ram_bar": ("ram.percent", DisplayMode.balken, {}),
    "disk_name": ("disk.label", DisplayMode.text, {}),
    "disk_used": ("disk.used", DisplayMode.text, {"suffix": " G"}),
    "disk_total": ("disk.total", DisplayMode.text, {"suffix": " G"}),
    "disk_pct": ("disk.percent", DisplayMode.text, {"suffix": "%"}),
    "disk_bar": ("disk.percent", DisplayMode.balken, {}),
    "net_ip": ("net.ip", DisplayMode.text, {}),
    "net_if": ("net.interface", DisplayMode.text, {}),
    "net_rx": ("net.rx", DisplayMode.text, {}),
    "net_tx": ("net.tx", DisplayMode.text, {}),
    "uptime": ("zeit.uptime", DisplayMode.text, {}),
    "label": ("text.frei", DisplayMode.text, {}),
    "marquee": ("text.laufschrift", DisplayMode.laufschrift, {}),
    "line_h": ("layout.linie_h", DisplayMode.linie_h, {}),
    "line_v": ("layout.linie_v", DisplayMode.linie_v, {}),
    "rect_o": ("layout.rahmen", DisplayMode.rahmen, {}),
    "rect_f": ("layout.block", DisplayMode.block, {}),
    "spark_cpu": ("cpu.percent", DisplayMode.sparkline, {}),
    "spark_temp": ("cpu.temp", DisplayMode.sparkline, {}),
    "spark_ram": ("ram.percent", DisplayMode.sparkline, {}),
    "gauge_cpu": ("cpu.percent", DisplayMode.gauge, {}),
    "gauge_ram": ("ram.percent", DisplayMode.gauge, {}),
    "gauge_disk": ("disk.percent", DisplayMode.gauge, {}),
    "gauge_temp": ("cpu.temp_pct", DisplayMode.gauge, {}),
    "section": ("layout.section", DisplayMode.section, {}),
}

LEGACY_LABELS: dict[str, str] = {
    "clock": "Uhr", "clock_s": "Uhr mit Sekunden", "clock_l": "Uhr groß", "date": "Datum",
    "weekday": "Wochentag", "cpu_temp": "CPU-Temperatur", "cpu_pct": "CPU-Auslastung",
    "cpu_cores": "Kerne", "cpu_bar": "CPU-Balken", "ram_used": "RAM benutzt",
    "ram_total": "RAM gesamt", "ram_pct": "RAM-Auslastung", "ram_bar": "RAM-Balken",
    "disk_name": "Laufwerk", "disk_used": "Belegt", "disk_total": "Gesamt", "disk_pct": "Belegung",
    "disk_bar": "Laufwerksbalken", "net_ip": "IP-Adresse", "net_if": "Schnittstelle",
    "net_rx": "Download", "net_tx": "Upload", "uptime": "Laufzeit", "label": "Text",
    "marquee": "Laufschrift", "line_h": "Linie", "line_v": "Linie", "rect_o": "Rahmen",
    "rect_f": "Block", "spark_cpu": "CPU-Verlauf", "spark_temp": "Temperaturverlauf",
    "spark_ram": "RAM-Verlauf", "gauge_cpu": "CPU", "gauge_ram": "RAM", "gauge_disk": "Laufwerk",
    "gauge_temp": "Temperatur", "section": "Trennlinie",
}


def _opts_from(alt: dict[str, Any], zusatz: dict[str, Any]) -> WidgetOpts:
    """Alte Optionen plus Zusatzwerte, die nur fehlende Felder füllen."""
    daten = {k: v for k, v in alt.items() if not str(k).startswith("_")}
    if "w" in daten and "width" not in daten:
        daten["width"] = daten.pop("w")
    if "h" in daten and "height" not in daten:
        daten["height"] = daten.pop("h")
    for schluessel, wert in zusatz.items():
        if daten.get(schluessel) in (None, ""):
            daten[schluessel] = wert
    try:
        return WidgetOpts.model_validate(daten)
    except Exception as fehler:
        logger.warning(f"Widget-Optionen verworfen ({fehler}): {daten}")
        return WidgetOpts.model_validate(zusatz)


def migrate_widget(alt: dict[str, Any]) -> Optional[Widget]:
    """Ein altes Widget (beide Formate) in das neue Modell überführen."""
    x = int(alt.get("x", 0) or 0)
    y = int(alt.get("y", 0) or 0)
    x, y = max(0, min(W - 1, x)), max(0, min(H - 1, y))
    name = str(alt.get("name", "") or "")

    if alt.get("source"):
        quelle = str(alt["source"])
        anzeige = str(alt.get("display", "zahl") or "zahl")
        if anzeige not in DISPLAY_MAP:
            logger.warning(f"Unbekannte Darstellungsart '{anzeige}' wird zu Text")
            anzeige = "zahl"
        neu, zusatz = DISPLAY_MAP[anzeige]
        opts = _opts_from(alt.get("opts") or {}, zusatz)
        return Widget(source=quelle, display=neu, x=x, y=y, name=name, opts=opts)

    typ = str(alt.get("type", "") or "")
    if typ not in LEGACY_TYPE_MAP:
        logger.warning(f"Altwidget '{typ}' ohne Entsprechung wird verworfen")
        return None
    quelle, neu, zusatz = LEGACY_TYPE_MAP[typ]
    roh = dict(alt.get("props") or {})
    for schluessel in ("scaleX", "scaleY", "scale", "prefix", "text", "w", "h", "width", "height",
                       "invert", "border", "align", "boxW", "radius", "tsep"):
        if schluessel in alt and schluessel not in roh:
            roh[schluessel] = alt[schluessel]
    disk_index = roh.pop("diskIdx", alt.get("diskIdx"))
    if quelle.startswith("disk."):
        quelle = f"{quelle}.{int(disk_index or 0)}"
    opts = _opts_from(roh, zusatz)
    return Widget(source=quelle, display=neu, x=x, y=y, name=name or LEGACY_LABELS.get(typ, typ), opts=opts)


def _bitmap_from_points(punkte: list[dict[str, Any]]) -> Optional[tuple[int, int, int, int, str]]:
    """Punktliste -> (x, y, breite, höhe, bitmap) über die belegte Fläche."""
    xs = [int(p.get("x", 0)) for p in punkte if 0 <= int(p.get("x", 0)) < W and 0 <= int(p.get("y", 0)) < H]
    ys = [int(p.get("y", 0)) for p in punkte if 0 <= int(p.get("x", 0)) < W and 0 <= int(p.get("y", 0)) < H]
    if not xs:
        return None
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    breite, hoehe = x1 - x0 + 1, y1 - y0 + 1
    raster = [[0] * breite for _ in range(hoehe)]
    for p in punkte:
        px, py = int(p.get("x", 0)), int(p.get("y", 0))
        if 0 <= px < W and 0 <= py < H:
            raster[py - y0][px - x0] = 1
    return x0, y0, breite, hoehe, pack_bitmap(raster)


def _lade_pixelbild(pixel_dir: Path, art_id: str) -> Optional[dict[str, Any]]:
    pfad = pixel_dir / f"{art_id}.json"
    if not pfad.exists():
        return None
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except Exception as fehler:
        logger.warning(f"Pixelbild {art_id}: {fehler}")
        return None


def migrate_screen(alt: dict[str, Any], pixel_dir: Path, index: int) -> Optional[Screen]:
    typ = str(alt.get("type", "system") or "system")
    name = str(alt.get("name", "") or f"Bildschirm {index + 1}")

    if typ in ("system", "widgets"):
        widgets = [w for w in (migrate_widget(r) for r in alt.get("widgets") or []) if w is not None]
        return Screen(name=name, widgets=widgets)

    if typ == "clock":
        return Screen(name=name or "Uhr", widgets=[
            Widget(source="zeit.uhr_blink", display=DisplayMode.text, x=2, y=2, name="Uhr",
                   opts=WidgetOpts(scale_x=3, scale_y=3)),
            Widget(source="zeit.tag", display=DisplayMode.text, x=2, y=34, name="Wochentag"),
            Widget(source="zeit.datum", display=DisplayMode.text, x=2, y=44, name="Datum"),
        ])

    if typ == "marquee":
        return Screen(name=name or "Laufschrift", widgets=[
            Widget(source="text.laufschrift", display=DisplayMode.laufschrift, x=0,
                   y=max(0, min(H - 1, int(alt.get("y", 20) or 20))), name="Laufschrift",
                   opts=WidgetOpts(text=str(alt.get("text", "PyroPlus") or "PyroPlus"),
                                   scale_x=int(alt.get("font_scale", 2) or 2),
                                   scale_y=int(alt.get("font_scale", 2) or 2))),
        ])

    if typ == "pixel_art":
        daten = _lade_pixelbild(pixel_dir, str(alt.get("art_id", "") or ""))
        bild = _bitmap_from_points(daten.get("pixels", [])) if daten else None
        if bild is None:
            return Screen(name=name or "Pixelbild", widgets=[])
        x, y, breite, hoehe, bitmap = bild
        return Screen(name=name or "Pixelbild", widgets=[
            Widget(source="layout.bitmap", display=DisplayMode.bitmap, x=x, y=y, name="Pixelbild",
                   opts=WidgetOpts(width=breite, height=hoehe, bitmap=bitmap)),
        ])

    if typ in ("weather_compact", "weather_hourly", "weather_daily"):
        return Screen(name=name, kind=ScreenKind(typ))

    logger.warning(f"Unbekannter Bildschirmtyp '{typ}' wird übersprungen")
    return None


def migrate_pixel_presets(pixel_dir: Path) -> list[WidgetPreset]:
    """Alle Pixelbilder als Vorlagen, damit nichts verloren geht."""
    ergebnis: list[WidgetPreset] = []
    if not pixel_dir.exists():
        return ergebnis
    for pfad in sorted(pixel_dir.glob("*.json")):
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
        except Exception:
            continue
        bild = _bitmap_from_points(daten.get("pixels", []))
        if bild is None:
            continue
        _, _, breite, hoehe, bitmap = bild
        name = str(daten.get("name") or pfad.stem)
        ergebnis.append(WidgetPreset(name=f"Pixelbild {name}", source="layout.bitmap",
                                     display=DisplayMode.bitmap,
                                     opts=WidgetOpts(width=breite, height=hoehe, bitmap=bitmap)))
    return ergebnis


def migrate_frontend_backup(backup: Optional[dict[str, Any]], pixel_dir: Path
                            ) -> tuple[list[WidgetPreset], list[Profile], WeatherSettings]:
    """Sicherung des alten Editors: Vorlagen, Profile, Städte."""
    presets: list[WidgetPreset] = []
    profiles: list[Profile] = []
    wetter = WeatherSettings()
    if not backup:
        return presets, profiles, wetter

    for p in backup.get("widgetPresets") or []:
        anzeige = str(p.get("display", "zahl") or "zahl")
        neu, zusatz = DISPLAY_MAP.get(anzeige, (DisplayMode.text, {}))
        try:
            presets.append(WidgetPreset(name=str(p.get("name") or p.get("source") or "Widget"),
                                        source=str(p.get("source", "text.frei")), display=neu,
                                        opts=_opts_from(p.get("opts") or {}, zusatz)))
        except Exception as fehler:
            logger.warning(f"Vorlage übersprungen: {fehler}")

    for pr in backup.get("profiles") or []:
        screens = [s for s in (migrate_screen(r, pixel_dir, i) for i, r in enumerate(pr.get("screens") or []))
                   if s is not None]
        try:
            profiles.append(Profile(name=str(pr.get("name") or "Profil"), screens=screens,
                                    rotation_interval=int(pr.get("rotationInterval", 10) or 10)))
        except Exception as fehler:
            logger.warning(f"Profil übersprungen: {fehler}")

    for stadt in backup.get("weatherCities") or []:
        try:
            wetter.locations.append(WeatherLocation(name=str(stadt.get("name", "Ort")),
                                                    lat=float(stadt.get("lat", 0.0)),
                                                    lon=float(stadt.get("lon", 0.0))))
        except Exception as fehler:
            logger.warning(f"Wetterort übersprungen: {fehler}")
    if wetter.locations:
        wetter.default_location_id = wetter.locations[0].id
    return presets, profiles, wetter


def migrate_v1(alt: dict[str, Any], pixel_dir: Path,
               frontend_backup: Optional[dict[str, Any]] = None) -> MigrationResult:
    screens: list[Screen] = []
    for index, roh in enumerate(alt.get("screens") or []):
        screen = migrate_screen(roh, pixel_dir, index)
        if screen is not None:
            screens.append(screen)

    alter_index = int(alt.get("current_screen", 0) or 0)
    aktuell = screens[alter_index].id if 0 <= alter_index < len(screens) else (screens[0].id if screens else None)

    modus = str(alt.get("mode", "auto") or "auto")
    settings = OledSettings(
        mode=OledMode(modus) if modus in ("auto", "manual", "off") else OledMode.auto,
        brightness=max(0, min(255, int(alt.get("brightness", 200) or 200))),
        rotation_interval=max(1, min(3600, int(alt.get("rotation_interval", 10) or 10))),
        current_screen_id=aktuell,
        screens=screens,
    )

    presets = migrate_pixel_presets(pixel_dir)
    backup_presets, profiles, wetter = migrate_frontend_backup(frontend_backup, pixel_dir)
    presets.extend(backup_presets)
    return MigrationResult(settings=settings, presets=presets, profiles=profiles, weather=wetter)
