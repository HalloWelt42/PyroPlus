"""Migration des alten Bestands: Bildschirme, Altwidgets, Pixelbilder, Editor-Sicherung."""

import json
from pathlib import Path

from oled.migrate import migrate_v1, migrate_widget
from oled.models import DisplayMode, OledMode, ScreenKind
from oled.store import OledStore

ALT = {
    "mode": "auto", "brightness": 30, "rotation_interval": 10, "current_screen": 1,
    "screens": [
        {"type": "system", "name": "Screen 3", "widgets": [
            {"source": "ram.percent", "display": "balken_label", "x": 43, "y": 3, "name": "Auslastung",
             "opts": {"width": 45, "height": 6, "scaleX": 2, "scaleY": 2, "prefix": "", "suffix": "%",
                      "_boxW": 74, "_boxH": 10}},
            {"source": "disk.available.2", "display": "zahl", "x": 21, "y": 48, "name": "Verfügbar",
             "opts": {"scaleX": 2, "scaleY": 2, "suffix": " GB", "decimals": 0, "tsep": True}},
            {"source": "wetter.temp", "display": "zahl_gross", "x": 4, "y": 11, "opts": {"scaleX": 3, "scaleY": 5}},
            {"source": "layout.rahmen", "display": "rahmen_shape", "x": 0, "y": 0, "opts": {"width": 20, "height": 10}},
            {"type": "cpu_temp", "x": 5, "y": 5, "props": {"scale": 2, "prefix": "T "}},
            {"type": "gauge_disk", "x": 5, "y": 5, "scaleX": 1, "scaleY": 1, "diskIdx": 1},
            {"type": "unbekannt", "x": 0, "y": 0},
        ]},
        {"type": "clock", "name": "Uhr"},
        {"type": "weather_daily", "name": "Wetter"},
        {"type": "marquee", "name": "Lauf", "text": "Hallo", "font_scale": 2, "y": 30},
        {"type": "pixel_art", "name": "Bild", "art_id": "art_1"},
    ],
    "clock_settings": {"blink": True},
}


def _pixel_dir(tmp_path: Path) -> Path:
    d = tmp_path / "pixel_screens"
    d.mkdir()
    (d / "art_1.json").write_text(json.dumps({"id": "art_1", "name": "Herz", "pixels": [
        {"x": 10, "y": 10}, {"x": 11, "y": 10}, {"x": 10, "y": 11}, {"x": 12, "y": 12}]}))
    return d


def test_migration_bildschirme(tmp_path: Path) -> None:
    ergebnis = migrate_v1(ALT, _pixel_dir(tmp_path))
    s = ergebnis.settings
    assert s.mode == OledMode.auto and s.brightness == 30
    assert len(s.screens) == 5
    assert s.current_screen_id == s.screens[1].id

    w = s.screens[0].widgets
    assert len(w) == 6, "unbekanntes Altwidget wird verworfen, der Rest bleibt"
    assert w[0].display == DisplayMode.balken_label and w[0].opts.width == 45 and w[0].opts.scale_x == 2
    assert w[1].display == DisplayMode.text and w[1].opts.thousands and w[1].opts.decimals == 0
    assert w[2].display == DisplayMode.text and w[2].opts.scale_x == 3 and w[2].opts.scale_y == 5
    assert w[3].display == DisplayMode.rahmen
    assert w[4].source == "cpu.temp" and w[4].opts.scale_x == 2 and w[4].opts.prefix == "T "
    assert w[5].source == "disk.percent.1" and w[5].display == DisplayMode.gauge
    assert all(len(x.id) == 32 for x in w)

    assert s.screens[1].kind == ScreenKind.widgets and len(s.screens[1].widgets) == 3
    assert s.screens[2].kind == ScreenKind.weather_daily
    lauf = s.screens[3].widgets[0]
    assert lauf.display == DisplayMode.laufschrift and lauf.opts.text == "Hallo" and lauf.y == 30
    bild = s.screens[4].widgets[0]
    assert bild.display == DisplayMode.bitmap and (bild.x, bild.y) == (10, 10)
    assert (bild.opts.width, bild.opts.height) == (3, 3)
    assert len(ergebnis.presets) == 1 and ergebnis.presets[0].name == "Pixelbild Herz"


def test_migration_editor_sicherung(tmp_path: Path) -> None:
    sicherung = {
        "weatherCities": [{"name": "Zeitz", "lat": 51.05, "lon": 12.13}, {"name": "Leipzig", "lat": 51.3, "lon": 12.4}],
        "widgetPresets": [{"source": "cpu.temp", "display": "gauge_gross", "name": "Temp", "opts": {"radius": 20}}],
        "profiles": [{"name": "Nacht", "screens": [{"type": "system", "widgets": []}], "rotationInterval": 20}],
    }
    ergebnis = migrate_v1({"screens": []}, _pixel_dir(tmp_path), sicherung)
    assert [o.name for o in ergebnis.weather.locations] == ["Zeitz", "Leipzig"]
    assert ergebnis.weather.default_location_id == ergebnis.weather.locations[0].id
    assert ergebnis.presets[-1].display == DisplayMode.gauge and ergebnis.presets[-1].opts.radius == 20
    assert ergebnis.profiles[0].name == "Nacht" and ergebnis.profiles[0].rotation_interval == 20


def test_store_migriert_genau_einmal(tmp_path: Path) -> None:
    (tmp_path / "oled_settings.json").write_text(json.dumps(ALT))
    _pixel_dir(tmp_path)
    store = OledStore(tmp_path, {"name": "Zeitz", "lat": 51.05, "lon": 12.13})
    assert store.ensure_initialised() is not None
    assert (tmp_path / "oled.json").exists() and (tmp_path / "oled_settings.json").exists()
    assert store.ensure_initialised() is None
    settings = store.load_settings()
    assert len(settings.screens) == 5 and settings.schema_version == 2
    wetter = store.load_weather()
    assert wetter.locations[0].name == "Zeitz"


def test_store_ohne_bestand_legt_vorgabe_an(tmp_path: Path) -> None:
    store = OledStore(tmp_path, {"name": "Zeitz", "lat": 51.05, "lon": 12.13})
    store.ensure_initialised()
    settings = store.load_settings()
    assert len(settings.screens) == 1 and settings.screens[0].widgets


def test_altwidget_ohne_entsprechung() -> None:
    assert migrate_widget({"type": "xyz"}) is None
    w = migrate_widget({"source": "cpu.temp", "display": "nie_gesehen", "x": 999, "y": -3})
    assert w is not None and w.display == DisplayMode.text and (w.x, w.y) == (127, 0)
