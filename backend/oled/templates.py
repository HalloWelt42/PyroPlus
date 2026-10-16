"""
PyroPlus: mitgelieferte Vorlagen.

Fertige Bildschirme und Widgets, die als Kopie eingefügt und danach frei
bearbeitet werden. Vorlagen sind gewöhnliche Modelle; beim Einfügen bekommen
sie neue Kennungen. Jede Vorlage ist mit Beispieldaten gerendert und geprüft.

Maße der Schrift: 5x7 Pixel je Zeichen, 6 Pixel Vorschub, Höhe 7 je Zeile.
Bei Skalierung s: Breite n*6*s-s, Höhe 7*s. Zentrieren über align=center
mit boxW=128 bei x=0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from oled.models import (
    Align, DisplayMode, Screen, ScreenKind, Widget, WidgetOpts, neue_id,
)
from oled.models import ApiModel


class ScreenTemplate(ApiModel):
    id: str
    name: str
    description: str
    category: str
    screen: Screen


class WidgetTemplate(ApiModel):
    id: str
    name: str
    description: str
    category: str
    widget: Widget


class TemplateCatalog(ApiModel):
    screens: list[ScreenTemplate]
    widgets: list[WidgetTemplate]
    categories: list[str]


def _w(source: str, display: DisplayMode, x: int, y: int, name: str = "", **opts: object) -> Widget:
    return Widget(source=source, display=display, x=x, y=y, name=name, opts=WidgetOpts(**opts))  # type: ignore[arg-type]


def _zentriert(source: str, y: int, scale: int, name: str = "", **opts: object) -> Widget:
    return _w(source, DisplayMode.text, 0, y, name, scale_x=scale, scale_y=scale,
              align=Align.center, box_w=128, **opts)


def _rechts(source: str, y: int, scale: int, name: str = "", **opts: object) -> Widget:
    return _w(source, DisplayMode.text, 0, y, name, scale_x=scale, scale_y=scale,
              align=Align.right, box_w=128, **opts)


# Bildschirmvorlagen

def _klassisch() -> Screen:
    return Screen(name="Klassisch", widgets=[
        _w("zeit.uhr_blink", DisplayMode.text, 0, 0, "Uhr", scale_x=3, scale_y=3),
        _w("zeit.tag_datum", DisplayMode.text, 0, 24, "Datum"),
        _w("cpu.temp", DisplayMode.text, 0, 36, "CPU", prefix="CPU ", suffix=" C", decimals=1),
        _w("ram.percent", DisplayMode.text, 0, 46, "RAM", prefix="RAM ", suffix="%"),
        _w("net.ip", DisplayMode.text, 0, 56, "IP"),
    ])


def _grosse_uhr() -> Screen:
    return Screen(name="Große Uhr", widgets=[
        _zentriert("zeit.uhr_blink", 6, 4, "Uhr"),
        _zentriert("zeit.tag_lang", 40, 1, "Wochentag"),
        _zentriert("zeit.datum", 52, 1, "Datum"),
    ])


def _uhr_mit_sekunden() -> Screen:
    return Screen(name="Uhr mit Sekunden", widgets=[
        _zentriert("zeit.uhr", 4, 3, "Uhr"),
        _zentriert("zeit.sekunde", 28, 2, "Sekunden", decimals=0),
        _w("zeit.tag_datum", DisplayMode.text, 0, 50, "Datum", align=Align.center, box_w=128),
        _w("layout.linie_h", DisplayMode.linie_h, 14, 46, "Linie", width=100),
    ])


def _minimal() -> Screen:
    return Screen(name="Minimal", widgets=[
        _zentriert("zeit.uhr_blink", 18, 3, "Uhr"),
        _rechts("cpu.temp", 56, 1, "Temperatur", suffix=" C", decimals=1),
        _w("zeit.datum_kurz", DisplayMode.text, 0, 56, "Datum"),
    ])


def _system_uebersicht() -> Screen:
    return Screen(name="System-Übersicht", widgets=[
        _w("layout.section", DisplayMode.section, 0, 0, "Titel", width=128, text="SYSTEM"),
        _w("text.frei", DisplayMode.text, 0, 12, "Beschriftung", text="CPU"),
        _w("cpu.percent", DisplayMode.balken_label, 26, 12, "CPU-Balken", width=66, height=7, suffix="%"),
        _w("text.frei", DisplayMode.text, 0, 24, "Beschriftung", text="RAM"),
        _w("ram.percent", DisplayMode.balken_label, 26, 24, "RAM-Balken", width=66, height=7, suffix="%"),
        _w("text.frei", DisplayMode.text, 0, 36, "Beschriftung", text="TMP"),
        _w("cpu.temp", DisplayMode.balken_label, 26, 36, "Temp-Balken", width=66, height=7, suffix=" C", decimals=0),
        _w("zeit.uptime", DisplayMode.text, 0, 48, "Laufzeit", prefix="UP "),
        _rechts("zeit.uhr", 48, 1, "Uhr"),
        _w("net.ip", DisplayMode.text, 0, 57, "IP"),
    ])


def _messuhren() -> Screen:
    return Screen(name="Messuhren", widgets=[
        _w("cpu.percent", DisplayMode.gauge, 8, 4, "CPU", radius=22, suffix="%"),
        _w("ram.percent", DisplayMode.gauge, 76, 4, "RAM", radius=22, suffix="%"),
        _w("text.frei", DisplayMode.text, 21, 32, "Titel CPU", text="CPU"),
        _w("text.frei", DisplayMode.text, 89, 32, "Titel RAM", text="RAM"),
        _w("layout.linie_h", DisplayMode.linie_h, 0, 44, "Linie", width=128),
        _w("cpu.temp", DisplayMode.text, 0, 50, "Temperatur", prefix="Temp ", suffix=" C", decimals=1, scale_x=1, scale_y=2),
        _rechts("zeit.uhr", 50, 2, "Uhr"),
    ])


def _laufwerke() -> Screen:
    return Screen(name="Laufwerke", widgets=[
        _w("layout.section", DisplayMode.section, 0, 0, "Titel", width=128, text="LAUFWERKE"),
        _w("disk.label.0", DisplayMode.text, 0, 11, "Name 1"),
        _w("disk.percent.0", DisplayMode.balken_label_in, 0, 19, "Balken 1", width=128, height=9, suffix="%"),
        _w("disk.label.1", DisplayMode.text, 0, 30, "Name 2"),
        _w("disk.percent.1", DisplayMode.balken_label_in, 0, 38, "Balken 2", width=128, height=9, suffix="%"),
        _w("disk.label.2", DisplayMode.text, 0, 48, "Name 3"),
        _w("disk.percent.2", DisplayMode.balken_label_in, 0, 55, "Balken 3", width=128, height=9, suffix="%"),
    ])


def _laufwerk_gross() -> Screen:
    return Screen(name="Laufwerk im Detail", widgets=[
        _w("disk.label.0", DisplayMode.text_invertiert, 0, 0, "Name", scale_x=1, scale_y=1, align=Align.center, box_w=126),
        _w("disk.available.0", DisplayMode.text, 0, 14, "Frei", scale_x=3, scale_y=3, suffix=" GB", decimals=0, thousands=True, align=Align.center, box_w=128),
        _w("text.frei", DisplayMode.text, 0, 38, "Beschriftung", text="frei", align=Align.center, box_w=128),
        _w("disk.percent.0", DisplayMode.balken_label, 0, 50, "Belegung", width=80, height=8, suffix="% voll"),
    ])


def _netzwerk() -> Screen:
    return Screen(name="Netzwerk", widgets=[
        _w("net.hostname", DisplayMode.text, 0, 0, "Rechnername", scale_x=1, scale_y=2),
        _w("net.ip", DisplayMode.text, 0, 15, "IP", scale_x=1, scale_y=2),
        _w("net.interface", DisplayMode.text, 0, 31, "Schnittstelle", prefix="via "),
        _w("net.rx", DisplayMode.text, 0, 44, "Download", prefix="↓ "),
        _w("net.tx", DisplayMode.text, 0, 54, "Upload", prefix="↑ "),
        _w("net.rx_raw", DisplayMode.sparkline, 72, 42, "Verlauf", width=56, height=22),
    ])


def _luefter() -> Screen:
    return Screen(name="Lüfter", widgets=[
        _w("fan.symbol", DisplayMode.fan_icon, 0, 0, "Symbol", size=32),
        _w("fan.rpm", DisplayMode.text, 36, 2, "Drehzahl", scale_x=2, scale_y=2, suffix=" RPM", decimals=0),
        _w("fan.level", DisplayMode.text, 36, 20, "Stufe", prefix="Stufe "),
        _w("fan.duty", DisplayMode.balken_label, 0, 35, "Leistung", width=86, height=8, suffix="%"),
        _w("cpu.temp", DisplayMode.text, 0, 48, "Temperatur", prefix="CPU ", suffix=" C", decimals=1, scale_x=2, scale_y=2),
    ])


def _temperatur() -> Screen:
    return Screen(name="Temperatur im Blick", widgets=[
        _zentriert("cpu.temp", 2, 4, "Temperatur", suffix="°", decimals=0),
        _w("cpu.temp", DisplayMode.sparkline, 0, 34, "Verlauf", width=128, height=22),
        _w("cpu.temp_min", DisplayMode.text, 0, 57, "Min", prefix="min ", decimals=0),
        _rechts("cpu.temp_max", 57, 1, "Max", prefix="max ", decimals=0),
    ])


def _verlauf() -> Screen:
    return Screen(name="Auslastung mit Verlauf", widgets=[
        _w("text.frei", DisplayMode.text, 0, 0, "Titel", text="CPU-Auslastung"),
        _rechts("cpu.percent", 0, 1, "Wert", suffix="%"),
        _w("cpu.percent", DisplayMode.sparkline, 0, 9, "Verlauf", width=128, height=30),
        _w("text.frei", DisplayMode.text, 0, 42, "Beschriftung", text="RAM"),
        _w("ram.percent", DisplayMode.balken_label, 22, 42, "RAM-Balken", width=80, height=7, suffix="%"),
        _w("cpu.temp", DisplayMode.text, 0, 54, "Temp", prefix="Temp ", suffix=" C", decimals=1),
        _rechts("zeit.uhr", 54, 1, "Uhr"),
    ])


def _wetter_jetzt() -> Screen:
    return Screen(name="Wetter jetzt", widgets=[
        _w("wetter.ort", DisplayMode.text_invertiert, 0, 0, "Ort", align=Align.center, box_w=126),
        _w("wetter.temp", DisplayMode.text, 2, 14, "Temperatur", scale_x=3, scale_y=3, suffix="°", decimals=1),
        _w("wetter.zustand", DisplayMode.text, 2, 38, "Zustand"),
        _w("wetter.gefuehlt", DisplayMode.text, 2, 48, "Gefühlt", prefix="gef. ", suffix="°", decimals=0),
        _rechts("wetter.wind", 48, 1, "Wind", suffix=" km/h", decimals=0),
        _w("wetter.sunrise", DisplayMode.text, 2, 57, "Aufgang", prefix="↑ "),
        _rechts("wetter.sunset", 57, 1, "Untergang", prefix="↓ "),
    ])


def _wetter_und_uhr() -> Screen:
    return Screen(name="Wetter und Uhr", widgets=[
        _w("zeit.uhr_blink", DisplayMode.text, 0, 2, "Uhr", scale_x=2, scale_y=3),
        _w("wetter.temp", DisplayMode.text, 70, 2, "Temperatur", scale_x=2, scale_y=3, suffix="°", decimals=0),
        _w("layout.linie_h", DisplayMode.linie_h, 0, 26, "Linie", width=128),
        _w("zeit.tag_datum", DisplayMode.text, 0, 31, "Datum"),
        _w("wetter.ort", DisplayMode.text, 0, 42, "Ort"),
        _rechts("wetter.zustand", 42, 1, "Zustand"),
        _w("wetter.feuchte", DisplayMode.text, 0, 53, "Feuchte", prefix="Feuchte ", suffix="%"),
        _rechts("wetter.wind", 53, 1, "Wind", suffix=" km/h", decimals=0),
    ])


def _wetter_details() -> Screen:
    return Screen(name="Wetter im Detail", widgets=[
        _w("wetter.ort", DisplayMode.text, 0, 0, "Ort", scale_x=2, scale_y=2),
        _rechts("wetter.temp", 0, 2, "Temperatur", suffix="°", decimals=0),
        _w("wetter.zustand", DisplayMode.text, 0, 16, "Zustand"),
        _w("layout.linie_h", DisplayMode.linie_h, 0, 25, "Linie", width=128),
        _w("text.frei", DisplayMode.text, 0, 29, "Beschriftung", text="Feuchte"),
        _w("wetter.feuchte", DisplayMode.balken_label, 46, 29, "Feuchte-Balken", width=54, height=7, suffix="%"),
        _w("text.frei", DisplayMode.text, 0, 39, "Beschriftung", text="Wolken"),
        _w("wetter.wolken", DisplayMode.balken_label, 46, 39, "Wolken-Balken", width=54, height=7, suffix="%"),
        _w("wetter.druck", DisplayMode.text, 0, 49, "Druck", suffix=" hPa", decimals=0),
        _rechts("wetter.wind_kombi", 49, 1, "Wind"),
        _w("wetter.niederschlag", DisplayMode.text, 0, 57, "Regen", prefix="Regen ", suffix=" mm", decimals=1),
    ])


def _weltzeit() -> Screen:
    return Screen(name="Weltzeituhren", widgets=[
        _w("text.frei", DisplayMode.text, 0, 0, "Beschriftung", text="Berlin"),
        _w("zeit.paris", DisplayMode.text, 0, 8, "Berlin", scale_x=2, scale_y=2),
        _w("text.frei", DisplayMode.text, 68, 0, "Beschriftung", text="New York"),
        _w("zeit.new_york", DisplayMode.text, 68, 8, "New York", scale_x=2, scale_y=2),
        _w("layout.linie_h", DisplayMode.linie_h, 0, 27, "Linie", width=128),
        _w("text.frei", DisplayMode.text, 0, 32, "Beschriftung", text="Tokio"),
        _w("zeit.tokio", DisplayMode.text, 0, 40, "Tokio", scale_x=2, scale_y=2),
        _w("text.frei", DisplayMode.text, 68, 32, "Beschriftung", text="Sydney"),
        _w("zeit.sydney", DisplayMode.text, 68, 40, "Sydney", scale_x=2, scale_y=2),
        _w("zeit.datum", DisplayMode.text, 0, 57, "Datum", align=Align.center, box_w=128),
    ])


def _kacheln() -> Screen:
    return Screen(name="Vier Kacheln", widgets=[
        _w("layout.rahmen", DisplayMode.rahmen, 0, 0, "Rahmen 1", width=63, height=31),
        _w("text.frei", DisplayMode.text, 3, 3, "Titel", text="CPU"),
        _w("cpu.percent", DisplayMode.text, 3, 13, "CPU", scale_x=2, scale_y=2, suffix="%"),
        _w("layout.rahmen", DisplayMode.rahmen, 65, 0, "Rahmen 2", width=63, height=31),
        _w("text.frei", DisplayMode.text, 68, 3, "Titel", text="RAM"),
        _w("ram.percent", DisplayMode.text, 68, 13, "RAM", scale_x=2, scale_y=2, suffix="%"),
        _w("layout.rahmen", DisplayMode.rahmen, 0, 33, "Rahmen 3", width=63, height=31),
        _w("text.frei", DisplayMode.text, 3, 36, "Titel", text="TEMP"),
        _w("cpu.temp", DisplayMode.text, 3, 46, "Temperatur", scale_x=2, scale_y=2, suffix="°", decimals=0),
        _w("layout.rahmen", DisplayMode.rahmen, 65, 33, "Rahmen 4", width=63, height=31),
        _w("text.frei", DisplayMode.text, 68, 36, "Titel", text="DISK"),
        _w("disk.percent.0", DisplayMode.text, 68, 46, "Laufwerk", scale_x=2, scale_y=2, suffix="%"),
    ])


def _invertierte_uhr() -> Screen:
    return Screen(name="Uhr auf hellem Grund", widgets=[
        _w("zeit.uhr_blink", DisplayMode.text_invertiert, 0, 0, "Uhr", scale_x=3, scale_y=4, align=Align.center, box_w=126),
        _w("zeit.tag_datum", DisplayMode.text, 0, 36, "Datum", align=Align.center, box_w=128),
        _w("cpu.temp", DisplayMode.text, 0, 50, "Temperatur", prefix="CPU ", suffix=" C", decimals=1),
        _rechts("ram.percent", 50, 1, "RAM", prefix="RAM ", suffix="%"),
    ])


def _laufschrift() -> Screen:
    return Screen(name="Uhr mit Laufschrift", widgets=[
        _zentriert("zeit.uhr_blink", 2, 3, "Uhr"),
        _w("zeit.tag_datum", DisplayMode.text, 0, 26, "Datum", align=Align.center, box_w=128),
        _w("layout.linie_h", DisplayMode.linie_h, 0, 38, "Linie", width=128),
        _w("text.laufschrift", DisplayMode.laufschrift, 0, 46, "Laufschrift", scale_x=2, scale_y=2,
           text="Willkommen bei PyroPlus   "),
    ])


def _wetter_kompakt() -> Screen:
    return Screen(name="Wetter kompakt (fertig)", kind=ScreenKind.weather_compact)


def _wetter_stunden() -> Screen:
    return Screen(name="Wetter nächste Stunden (fertig)", kind=ScreenKind.weather_hourly)


def _wetter_tage() -> Screen:
    return Screen(name="Wetter fünf Tage (fertig)", kind=ScreenKind.weather_daily)


@dataclass(frozen=True)
class _ScreenDef:
    id: str
    name: str
    description: str
    category: str
    factory: Callable[[], Screen]


def _ringe() -> Screen:
    return Screen(name="Drei Ringe", widgets=[
        _w("cpu.percent", DisplayMode.ring, 6, 2, "CPU", radius=14, suffix="%", decimals=0),
        _w("ram.percent", DisplayMode.ring, 50, 2, "RAM", radius=14, suffix="%", decimals=0),
        _w("cpu.temp", DisplayMode.ring, 94, 2, "Temperatur", radius=14, suffix="°", decimals=0),
        _w("text.frei", DisplayMode.text, 12, 33, "Beschriftung", text="CPU"),
        _w("text.frei", DisplayMode.text, 56, 33, "Beschriftung", text="RAM"),
        _w("text.frei", DisplayMode.text, 100, 33, "Beschriftung", text="TMP"),
        _zentriert("zeit.uhr_blink", 48, 2, "Uhr"),
    ])


def _symbole() -> Screen:
    return Screen(name="Symbole mit Werten", widgets=[
        _w("cpu.temp", DisplayMode.symbol_wert, 0, 0, "Temperatur", size=16, icon="thermometer", suffix=" C", decimals=1),
        _w("cpu.percent", DisplayMode.symbol_wert, 0, 16, "CPU", size=16, icon="chip", suffix="%", decimals=0),
        _w("ram.percent", DisplayMode.symbol_wert, 0, 32, "RAM", size=16, icon="speicher", suffix="%", decimals=0),
        _w("disk.percent.0", DisplayMode.symbol_wert, 0, 48, "Laufwerk", size=16, icon="laufwerk", suffix="%", decimals=0),
        _w("zeit.uhr", DisplayMode.symbol_wert, 66, 0, "Uhr", size=16, icon="uhr"),
        _w("zeit.datum_kurz", DisplayMode.symbol_wert, 66, 16, "Datum", size=16, icon="kalender"),
        _w("fan.rpm", DisplayMode.symbol_wert, 66, 32, "Drehzahl", size=16, icon="luefter", decimals=0),
        _w("fan.duty", DisplayMode.symbol_wert, 66, 48, "Leistung", size=16, icon="tacho", suffix="%", decimals=0),
    ])


def _digitaluhr() -> Screen:
    return Screen(name="Digitaluhr", widgets=[
        _w("zeit.uhr", DisplayMode.sieben_segment, 18, 4, "Uhr", height=32),
        _zentriert("zeit.tag_datum", 44, 1, "Datum"),
        _w("cpu.temp", DisplayMode.symbol_wert, 0, 56, "Temperatur", size=8, icon="thermometer", suffix=" C", decimals=1),
        _rechts("ram.percent", 56, 1, "RAM", suffix="% RAM", decimals=0),
    ])


def _stufen() -> Screen:
    return Screen(name="Stufenanzeige", widgets=[
        _w("text.frei", DisplayMode.text, 0, 2, "Beschriftung", text="CPU"),
        _w("cpu.percent", DisplayMode.stufen, 24, 1, "CPU", steps=10, width=104, height=8),
        _w("text.frei", DisplayMode.text, 0, 18, "Beschriftung", text="RAM"),
        _w("ram.percent", DisplayMode.stufen, 24, 17, "RAM", steps=10, width=104, height=8),
        _w("text.frei", DisplayMode.text, 0, 34, "Beschriftung", text="TMP"),
        _w("cpu.temp", DisplayMode.stufen, 24, 33, "Temperatur", steps=10, width=104, height=8),
        _w("fan.rpm", DisplayMode.symbol_wert, 0, 52, "Drehzahl", size=8, icon="luefter", suffix=" RPM", decimals=0),
        _rechts("zeit.uhr", 52, 1, "Uhr"),
    ])


def _saeulen() -> Screen:
    return Screen(name="Säulen", widgets=[
        _w("cpu.percent", DisplayMode.balken_v, 12, 4, "CPU", width=14, height=40),
        _w("ram.percent", DisplayMode.balken_v, 42, 4, "RAM", width=14, height=40),
        _w("cpu.temp", DisplayMode.balken_v, 72, 4, "Temperatur", width=14, height=40),
        _w("fan.rpm_pct", DisplayMode.balken_v, 102, 4, "Drehzahl", width=14, height=40),
        _w("text.frei", DisplayMode.text, 11, 48, "Beschriftung", text="CPU"),
        _w("text.frei", DisplayMode.text, 41, 48, "Beschriftung", text="RAM"),
        _w("text.frei", DisplayMode.text, 71, 48, "Beschriftung", text="TMP"),
        _w("text.frei", DisplayMode.text, 101, 48, "Beschriftung", text="FAN"),
        _w("cpu.percent", DisplayMode.text, 11, 57, "CPU-Wert", suffix="%", decimals=0),
        _w("ram.percent", DisplayMode.text, 41, 57, "RAM-Wert", suffix="%", decimals=0),
        _w("cpu.temp", DisplayMode.text, 71, 57, "Temperaturwert", suffix="°", decimals=0),
        _w("fan.rpm_pct", DisplayMode.text, 101, 57, "Drehzahlwert", suffix="%", decimals=0),
    ])


SCREEN_TEMPLATES: list[_ScreenDef] = [
    _ScreenDef("klassisch", "Klassisch", "Blinkende Uhr, Datum, CPU, RAM und IP-Adresse", "Uhr", _klassisch),
    _ScreenDef("grosse_uhr", "Große Uhr", "Uhrzeit so groß wie möglich, darunter Wochentag und Datum", "Uhr", _grosse_uhr),
    _ScreenDef("uhr_sekunden", "Uhr mit Sekunden", "Uhrzeit, laufende Sekunden und Datum", "Uhr", _uhr_mit_sekunden),
    _ScreenDef("minimal", "Minimal", "Nur Uhrzeit, Datum und Temperatur", "Uhr", _minimal),
    _ScreenDef("uhr_invertiert", "Uhr auf hellem Grund", "Uhr als heller Block, darunter Datum und Werte", "Uhr", _invertierte_uhr),
    _ScreenDef("uhr_laufschrift", "Uhr mit Laufschrift", "Uhr und Datum, unten ein frei einstellbarer Lauftext", "Uhr", _laufschrift),
    _ScreenDef("weltzeit", "Weltzeituhren", "Vier Städte in zwei Spalten", "Uhr", _weltzeit),
    _ScreenDef("system", "System-Übersicht", "CPU, RAM und Temperatur als Balken mit Wert, Laufzeit, Uhr, IP", "System", _system_uebersicht),
    _ScreenDef("messuhren", "Messuhren", "Zwei Halbkreise für CPU und RAM, darunter Temperatur und Uhr", "System", _messuhren),
    _ScreenDef("kacheln", "Vier Kacheln", "CPU, RAM, Temperatur und Laufwerk in Rahmen", "System", _kacheln),
    _ScreenDef("temperatur", "Temperatur im Blick", "Temperatur groß mit Verlauf, Minimum und Maximum", "System", _temperatur),
    _ScreenDef("verlauf", "Auslastung mit Verlauf", "CPU-Verlauf der letzten Minute, RAM-Balken, Temperatur", "System", _verlauf),
    _ScreenDef("luefter", "Lüfter", "Drehendes Symbol, Drehzahl, Stufe, Leistung und Temperatur", "System", _luefter),
    _ScreenDef("laufwerke", "Laufwerke", "Drei Laufwerke mit Belegungsbalken", "Laufwerke", _laufwerke),
    _ScreenDef("laufwerk_detail", "Laufwerk im Detail", "Freier Platz groß, Belegung als Balken", "Laufwerke", _laufwerk_gross),
    _ScreenDef("netzwerk", "Netzwerk", "Rechnername, IP, Schnittstelle, Download und Upload mit Verlauf", "Netzwerk", _netzwerk),
    _ScreenDef("wetter_jetzt", "Wetter jetzt", "Ort, Temperatur groß, Zustand, gefühlt, Wind, Sonnenauf- und -untergang", "Wetter", _wetter_jetzt),
    _ScreenDef("wetter_uhr", "Wetter und Uhr", "Uhr und Außentemperatur groß, darunter Datum, Ort, Feuchte und Wind", "Wetter", _wetter_und_uhr),
    _ScreenDef("wetter_details", "Wetter im Detail", "Feuchte und Bewölkung als Balken, Druck, Wind, Niederschlag", "Wetter", _wetter_details),
    _ScreenDef("wetter_kompakt", "Wetter kompakt", "Fertiger Wetterbildschirm mit Symbolen", "Wetter", _wetter_kompakt),
    _ScreenDef("wetter_stunden", "Nächste Stunden", "Fertige Stundenvorhersage mit Symbolen", "Wetter", _wetter_stunden),
    _ScreenDef("wetter_tage", "Fünf Tage", "Fertige Tagesvorhersage mit Symbolen", "Wetter", _wetter_tage),
    _ScreenDef("ringe", "Drei Ringe", "CPU, RAM und Temperatur als Ringe, darunter die Uhr", "System", _ringe),
    _ScreenDef("symbole", "Symbole mit Werten", "Acht Werte mit passenden Symbolen in zwei Spalten", "System", _symbole),
    _ScreenDef("stufen", "Stufenanzeige", "CPU, RAM und Temperatur in zehn Stufen, unten Drehzahl und Uhr", "System", _stufen),
    _ScreenDef("saeulen", "Säulen", "Vier senkrechte Balken mit Beschriftung und Wert", "System", _saeulen),
    _ScreenDef("digitaluhr", "Digitaluhr", "Siebensegmentanzeige, Datum, Temperatur und RAM", "Uhr", _digitaluhr),
]


# Widgetvorlagen (Bausteine)

@dataclass(frozen=True)
class _WidgetDef:
    id: str
    name: str
    description: str
    category: str
    factory: Callable[[], Widget]


def _symbolwert(source: str, name: str, icon: str | None = None, size: int = 16, **opts: object) -> Widget:
    return _w(source, DisplayMode.symbol_wert, 0, 0, name, size=size, icon=icon, **opts)


WIDGET_TEMPLATES: list[_WidgetDef] = [
    # Uhr und Datum
    _WidgetDef("uhr_gross", "Uhr groß", "Blinkende Uhrzeit in dreifacher Größe", "Uhr",
               lambda: _w("zeit.uhr_blink", DisplayMode.text, 0, 0, "Uhr", scale_x=3, scale_y=3)),
    _WidgetDef("uhr_riesig", "Uhr riesig", "Uhrzeit in vierfacher Größe, fast volle Breite", "Uhr",
               lambda: _w("zeit.uhr_blink", DisplayMode.text, 0, 0, "Uhr", scale_x=4, scale_y=4)),
    _WidgetDef("uhr_sekunden", "Uhr mit Sekunden", "Stunden, Minuten und Sekunden in doppelter Größe", "Uhr",
               lambda: _w("zeit.uhr_s", DisplayMode.text, 0, 0, "Uhr", scale_x=2, scale_y=2)),
    _WidgetDef("uhr_digital", "Digitaluhr", "Uhrzeit als Siebensegmentanzeige, 24 Pixel hoch", "Uhr",
               lambda: _w("zeit.uhr", DisplayMode.sieben_segment, 0, 0, "Digitaluhr", height=24)),
    _WidgetDef("uhr_digital_riesig", "Digitaluhr riesig", "Siebensegmentanzeige über fast die ganze Höhe", "Uhr",
               lambda: _w("zeit.uhr", DisplayMode.sieben_segment, 0, 0, "Digitaluhr", height=40)),
    _WidgetDef("uhr_symbol", "Uhr mit Symbol", "Uhrsymbol, daneben die Zeit in doppelter Größe", "Uhr",
               lambda: _symbolwert("zeit.uhr", "Uhr", "uhr", scale_x=2, scale_y=2)),
    _WidgetDef("datum_lang", "Datum mit Wochentag", "Mo 16.10.2026", "Uhr",
               lambda: _w("zeit.tag_datum", DisplayMode.text, 0, 0, "Datum")),
    _WidgetDef("datum_gross", "Datum groß", "16.10.2026 in doppelter Größe", "Uhr",
               lambda: _w("zeit.datum", DisplayMode.text, 0, 0, "Datum", scale_x=2, scale_y=2)),
    _WidgetDef("wochentag", "Wochentag", "Ausgeschriebener Wochentag in doppelter Größe", "Uhr",
               lambda: _w("zeit.tag_lang", DisplayMode.text, 0, 0, "Wochentag", scale_x=2, scale_y=2)),
    _WidgetDef("datum_symbol", "Datum mit Kalender", "Kalendersymbol und Datum", "Uhr",
               lambda: _symbolwert("zeit.datum", "Datum", "kalender")),
    _WidgetDef("laufzeit", "Laufzeit", "Betriebszeit seit dem Start, zum Beispiel UP 3d 4h 12m", "Uhr",
               lambda: _w("zeit.uptime", DisplayMode.text, 0, 0, "Laufzeit", prefix="UP ")),
    _WidgetDef("laufzeit_symbol", "Laufzeit mit Stoppuhr", "Stoppuhrsymbol und Betriebszeit", "Uhr",
               lambda: _symbolwert("zeit.uptime", "Laufzeit", "stoppuhr")),
    _WidgetDef("weltzeit", "Weltzeit", "Uhrzeit einer anderen Zeitzone mit Kürzel davor", "Uhr",
               lambda: _w("zeit.london", DisplayMode.text, 0, 0, "London", prefix="LON ")),
    # System
    _WidgetDef("cpu_balken", "CPU-Balken mit Wert", "Auslastung als Balken, rechts der Prozentwert", "System",
               lambda: _w("cpu.percent", DisplayMode.balken_label, 0, 0, "CPU", width=60, height=7, suffix="%")),
    _WidgetDef("cpu_ring", "CPU-Ring", "Auslastung als Ring mit Wert in der Mitte", "System",
               lambda: _w("cpu.percent", DisplayMode.ring, 0, 0, "CPU", radius=14, suffix="%", decimals=0)),
    _WidgetDef("cpu_stufen", "CPU in Stufen", "Zehn Felder, gefüllt bis zur Auslastung", "System",
               lambda: _w("cpu.percent", DisplayMode.stufen, 0, 0, "CPU", steps=10, width=62, height=6)),
    _WidgetDef("cpu_saeule", "CPU-Säule", "Senkrechter Balken, füllt sich von unten", "System",
               lambda: _w("cpu.percent", DisplayMode.balken_v, 0, 0, "CPU", width=8, height=32)),
    _WidgetDef("cpu_verlauf", "CPU-Verlauf", "Verlauf der letzten Minute als Linie", "System",
               lambda: _w("cpu.percent", DisplayMode.sparkline, 0, 0, "CPU-Verlauf", width=64, height=20)),
    _WidgetDef("cpu_flaeche", "CPU-Verlauf als Fläche", "Verlauf der letzten Minute, Fläche gefüllt", "System",
               lambda: _w("cpu.percent", DisplayMode.sparkline, 0, 0, "CPU-Verlauf", width=64, height=20, filled=True)),
    _WidgetDef("cpu_symbol", "CPU mit Symbol", "Prozessorsymbol und Auslastung", "System",
               lambda: _symbolwert("cpu.percent", "CPU", "chip", suffix="%", decimals=0)),
    _WidgetDef("ram_balken_innen", "RAM-Balken, Wert innen", "Balken über volle Breite mit Wert in der Mitte", "System",
               lambda: _w("ram.percent", DisplayMode.balken_label_in, 0, 0, "RAM", width=128, height=9, suffix="% RAM")),
    _WidgetDef("ram_ring", "RAM-Ring", "Speicherbelegung als Ring", "System",
               lambda: _w("ram.percent", DisplayMode.ring, 0, 0, "RAM", radius=14, suffix="%", decimals=0)),
    _WidgetDef("ram_symbol", "RAM mit Symbol", "Speichersymbol und Belegung", "System",
               lambda: _symbolwert("ram.percent", "RAM", "speicher", suffix="%", decimals=0)),
    _WidgetDef("ram_frei", "RAM frei", "Freier Arbeitsspeicher in Gigabyte", "System",
               lambda: _w("ram.available", DisplayMode.text, 0, 0, "RAM frei", suffix=" GB frei", decimals=1)),
    _WidgetDef("temp_messuhr", "Temperatur-Messuhr", "Halbkreis mit Temperatur in Grad", "System",
               lambda: _w("cpu.temp", DisplayMode.gauge, 0, 0, "Temperatur", radius=20, suffix="°", decimals=0)),
    _WidgetDef("temp_ring", "Temperatur-Ring", "Ring, der sich mit der Temperatur füllt", "System",
               lambda: _w("cpu.temp", DisplayMode.ring, 0, 0, "Temperatur", radius=14, suffix="°", decimals=0)),
    _WidgetDef("temp_gross", "Temperatur groß", "Zweifache Größe mit Grad", "System",
               lambda: _w("cpu.temp", DisplayMode.text, 0, 0, "Temperatur", scale_x=2, scale_y=2, suffix=" C", decimals=1)),
    _WidgetDef("temp_digital", "Temperatur digital", "Siebensegmentanzeige mit einer Nachkommastelle", "System",
               lambda: _w("cpu.temp", DisplayMode.sieben_segment, 0, 0, "Temperatur", height=16, decimals=1)),
    _WidgetDef("temp_symbol", "Temperatur mit Thermometer", "Thermometersymbol und Temperatur", "System",
               lambda: _symbolwert("cpu.temp", "Temperatur", "thermometer", suffix=" C", decimals=1)),
    _WidgetDef("temp_verlauf", "Temperaturverlauf", "Verlauf der letzten Minute als Fläche", "System",
               lambda: _w("cpu.temp", DisplayMode.sparkline, 0, 0, "Temperaturverlauf", width=64, height=20, filled=True)),
    _WidgetDef("temp_spanne", "Temperaturspanne", "Minimum und Maximum seit dem Start", "System",
               lambda: _w("cpu.temp_range", DisplayMode.text, 0, 0, "Spanne", prefix="min/max ")),
    _WidgetDef("last", "Last mit Tacho", "Tachosymbol und Systemlast", "System",
               lambda: _symbolwert("cpu.load", "Last", "tacho")),
    # Laufwerke
    _WidgetDef("laufwerk_balken", "Laufwerk mit Belegung", "Belegung des ersten Laufwerks als Balken mit Wert", "Laufwerke",
               lambda: _w("disk.percent.0", DisplayMode.balken_label, 0, 0, "Laufwerk", width=70, height=7, suffix="%")),
    _WidgetDef("laufwerk_symbol", "Laufwerk mit Symbol", "Laufwerksymbol und Belegung", "Laufwerke",
               lambda: _symbolwert("disk.percent.0", "Laufwerk", "laufwerk", suffix="%", decimals=0)),
    _WidgetDef("laufwerk_frei", "Laufwerk frei", "Freier Platz des ersten Laufwerks", "Laufwerke",
               lambda: _w("disk.available.0", DisplayMode.text, 0, 0, "Frei", suffix=" GB frei", decimals=0)),
    _WidgetDef("laufwerk_stufen", "Laufwerk in Stufen", "Belegung in zehn Feldern", "Laufwerke",
               lambda: _w("disk.percent.0", DisplayMode.stufen, 0, 0, "Laufwerk", steps=10, width=62, height=6)),
    _WidgetDef("laufwerk_ring", "Laufwerk-Ring", "Belegung als Ring", "Laufwerke",
               lambda: _w("disk.percent.0", DisplayMode.ring, 0, 0, "Laufwerk", radius=14, suffix="%", decimals=0)),
    # Netzwerk
    _WidgetDef("ip_adresse", "IP-Adresse", "Adresse im Heimnetz", "Netzwerk",
               lambda: _w("net.ip", DisplayMode.text, 0, 0, "IP")),
    _WidgetDef("ip_symbol", "IP mit Symbol", "Kleines Netzwerksymbol und Adresse", "Netzwerk",
               lambda: _symbolwert("net.ip", "IP", "netzwerk", size=8)),
    _WidgetDef("rechnername", "Rechnername", "Serversymbol und Name des Rechners", "Netzwerk",
               lambda: _symbolwert("net.hostname", "Rechnername", "server")),
    _WidgetDef("download", "Download", "Pfeil nach unten und Empfangsrate", "Netzwerk",
               lambda: _symbolwert("net.rx", "Download", "download")),
    _WidgetDef("upload", "Upload", "Pfeil nach oben und Senderate", "Netzwerk",
               lambda: _symbolwert("net.tx", "Upload", "upload")),
    _WidgetDef("netz_verlauf", "Netzwerkverlauf", "Empfangsrate der letzten Minute als Fläche", "Netzwerk",
               lambda: _w("net.rx", DisplayMode.sparkline, 0, 0, "Netzwerk", width=64, height=20, filled=True)),
    _WidgetDef("schnittstelle", "Schnittstelle", "Steckersymbol und Name der Schnittstelle", "Netzwerk",
               lambda: _symbolwert("net.interface", "Schnittstelle", "ethernet", size=8)),
    # Lüfter
    _WidgetDef("luefter_symbol", "Lüfter dreht", "Symbol, das sich mit der Drehzahl dreht", "Lüfter",
               lambda: _w("fan.symbol", DisplayMode.fan_icon, 0, 0, "Lüfter", size=16)),
    _WidgetDef("luefter_gross", "Lüfter groß", "Drehendes Symbol in 32 Pixeln", "Lüfter",
               lambda: _w("fan.symbol", DisplayMode.fan_icon, 0, 0, "Lüfter", size=32)),
    _WidgetDef("luefter_drehzahl", "Lüfter mit Drehzahl", "Drehendes Symbol und Drehzahl", "Lüfter",
               lambda: _w("fan.symbol_rpm", DisplayMode.fan_icon_rpm, 0, 0, "Lüfter", size=16, suffix=" RPM")),
    _WidgetDef("luefter_leistung", "Lüfterleistung", "Leistung als Balken mit Prozentwert", "Lüfter",
               lambda: _w("fan.duty", DisplayMode.balken_label, 0, 0, "Leistung", width=60, height=7, suffix="%", decimals=0)),
    _WidgetDef("luefter_stufe", "Lüfterstufe", "Name der aktuellen Stufe", "Lüfter",
               lambda: _w("fan.level", DisplayMode.text, 0, 0, "Stufe", prefix="Stufe ")),
    _WidgetDef("luefter_ring", "Drehzahl-Ring", "Drehzahl bezogen auf das Maximum als Ring", "Lüfter",
               lambda: _w("fan.rpm_pct", DisplayMode.ring, 0, 0, "Drehzahl", radius=14, suffix="%", decimals=0)),
    _WidgetDef("luefter_saeule", "Drehzahl-Säule", "Drehzahl als senkrechter Balken", "Lüfter",
               lambda: _w("fan.rpm_pct", DisplayMode.balken_v, 0, 0, "Drehzahl", width=8, height=32)),
    # Wetter
    _WidgetDef("wetter_temp", "Außentemperatur", "Temperatur des Vorgabeorts, dreifach", "Wetter",
               lambda: _w("wetter.temp", DisplayMode.text, 0, 0, "Außen", scale_x=3, scale_y=3, suffix="°", decimals=0)),
    _WidgetDef("wetter_kombi", "Temperatur und Zustand", "Zum Beispiel 14° Bewölkt", "Wetter",
               lambda: _w("wetter.kombi", DisplayMode.text, 0, 0, "Wetter")),
    _WidgetDef("wetter_thermometer", "Außentemperatur mit Symbol", "Thermometer und Temperatur in doppelter Größe", "Wetter",
               lambda: _symbolwert("wetter.temp", "Außen", "thermometer", scale_x=2, scale_y=2, suffix="°", decimals=0)),
    _WidgetDef("wetter_gefuehlt", "Gefühlte Temperatur", "Gefühlt, in Grad", "Wetter",
               lambda: _w("wetter.gefuehlt", DisplayMode.text, 0, 0, "Gefühlt", prefix="gef. ", suffix="°", decimals=0)),
    _WidgetDef("wetter_wind", "Wind", "Windsymbol und Geschwindigkeit", "Wetter",
               lambda: _symbolwert("wetter.wind", "Wind", "wind", suffix=" km/h", decimals=0)),
    _WidgetDef("wetter_feuchte", "Luftfeuchte", "Tropfen und Feuchte in Prozent", "Wetter",
               lambda: _symbolwert("wetter.feuchte", "Feuchte", "tropfen", suffix="%", decimals=0)),
    _WidgetDef("wetter_regen", "Niederschlag", "Regensymbol und Menge in Millimetern", "Wetter",
               lambda: _symbolwert("wetter.niederschlag", "Regen", "regen", suffix=" mm", decimals=1)),
    _WidgetDef("wetter_druck", "Luftdruck", "Tacho und Druck in Hektopascal", "Wetter",
               lambda: _symbolwert("wetter.druck", "Druck", "tacho", suffix=" hPa", decimals=0)),
    _WidgetDef("wetter_sonne", "Sonnenaufgang", "Sonne und Uhrzeit des Aufgangs", "Wetter",
               lambda: _symbolwert("wetter.sunrise", "Sonnenaufgang", "sonne", size=8)),
    _WidgetDef("wetter_mond", "Sonnenuntergang", "Mond und Uhrzeit des Untergangs", "Wetter",
               lambda: _symbolwert("wetter.sunset", "Sonnenuntergang", "mond", size=8)),
    _WidgetDef("wetter_ort", "Ort", "Standortsymbol und Name des Orts", "Wetter",
               lambda: _symbolwert("wetter.ort", "Ort", "standort", size=8)),
    _WidgetDef("wetter_zustand", "Wetterzustand", "Zustand als Text, zum Beispiel Bewölkt", "Wetter",
               lambda: _w("wetter.zustand", DisplayMode.text, 0, 0, "Zustand")),
    # Symbole
    _WidgetDef("symbol_klein", "Symbol klein (8)", "Festes Symbol in 8 Pixeln, frei wählbar", "Symbole",
               lambda: _w("layout.symbol", DisplayMode.symbol, 0, 0, "Symbol", size=8, icon="stern")),
    _WidgetDef("symbol_mittel", "Symbol (16)", "Festes Symbol in 16 Pixeln, frei wählbar", "Symbole",
               lambda: _w("layout.symbol", DisplayMode.symbol, 0, 0, "Symbol", size=16, icon="herz")),
    _WidgetDef("symbol_gross", "Symbol groß (24)", "Festes Symbol in 24 Pixeln, frei wählbar", "Symbole",
               lambda: _w("layout.symbol", DisplayMode.symbol, 0, 0, "Symbol", size=24, icon="haus")),
    _WidgetDef("symbol_xl", "Symbol XL (32)", "Festes Symbol in 32 Pixeln, frei wählbar", "Symbole",
               lambda: _w("layout.symbol", DisplayMode.symbol, 0, 0, "Symbol", size=32, icon="rakete")),
    # Layout und Text
    _WidgetDef("titelzeile", "Titelzeile", "Heller Block über volle Breite mit zentriertem Text", "Layout",
               lambda: _w("text.frei", DisplayMode.text_invertiert, 0, 0, "Titel", text="TITEL", align=Align.center, box_w=126)),
    _WidgetDef("trennlinie", "Trennlinie mit Titel", "Linie mit Beschriftung in der Mitte", "Layout",
               lambda: _w("layout.section", DisplayMode.section, 0, 0, "Trennlinie", width=128, text="TITEL")),
    _WidgetDef("rahmen", "Rahmen", "Kasten um einen Bereich", "Layout",
               lambda: _w("layout.rahmen", DisplayMode.rahmen, 0, 0, "Rahmen", width=63, height=31)),
    _WidgetDef("block", "Block", "Gefüllte Fläche", "Layout",
               lambda: _w("layout.block", DisplayMode.block, 0, 0, "Block", width=40, height=20)),
    _WidgetDef("linie_waagerecht", "Linie waagerecht", "Linie über die volle Breite", "Layout",
               lambda: _w("layout.linie_h", DisplayMode.linie_h, 0, 0, "Linie", width=128)),
    _WidgetDef("linie_senkrecht", "Linie senkrecht", "Linie über die volle Höhe", "Layout",
               lambda: _w("layout.linie_v", DisplayMode.linie_v, 0, 0, "Linie", height=64)),
    _WidgetDef("laufschrift", "Laufschrift", "Eigener Text, der durchläuft", "Layout",
               lambda: _w("text.laufschrift", DisplayMode.laufschrift, 0, 0, "Laufschrift", scale_x=2, scale_y=2, text="Hallo Welt   ")),
    _WidgetDef("text_zwei_zeilen", "Zwei Zeilen Text", "Eigener Text mit Zeilenumbruch", "Layout",
               lambda: _w("text.mehrzeilig", DisplayMode.text, 0, 0, "Text", text="Zeile 1\nZeile 2")),
    _WidgetDef("text_rahmen", "Text mit Rahmen", "Eigener Text in einem Kasten", "Layout",
               lambda: _w("text.frei", DisplayMode.text_rahmen, 0, 0, "Text", text="INFO")),
    _WidgetDef("pixelbild", "Leeres Pixelbild", "32 mal 16 Pixel zum Zeichnen", "Layout",
               lambda: _w("layout.bitmap", DisplayMode.bitmap, 0, 0, "Pixelbild", width=32, height=16)),
]


def _frische_ids(screen: Screen) -> Screen:
    kopie = screen.model_copy(deep=True)
    kopie.id = neue_id()
    for widget in kopie.widgets:
        widget.id = neue_id()
    return kopie


def template_catalog() -> TemplateCatalog:
    screens = [ScreenTemplate(id=d.id, name=d.name, description=d.description, category=d.category,
                              screen=_frische_ids(d.factory())) for d in SCREEN_TEMPLATES]
    widgets = [WidgetTemplate(id=d.id, name=d.name, description=d.description, category=d.category,
                              widget=d.factory()) for d in WIDGET_TEMPLATES]
    kategorien: list[str] = []
    for k in [d.category for d in SCREEN_TEMPLATES] + [d.category for d in WIDGET_TEMPLATES]:
        if k not in kategorien:
            kategorien.append(k)
    return TemplateCatalog(screens=screens, widgets=widgets, categories=kategorien)


def screen_template(template_id: str) -> Screen | None:
    for d in SCREEN_TEMPLATES:
        if d.id == template_id:
            return _frische_ids(d.factory())
    return None


def widget_template(template_id: str) -> Widget | None:
    for d in WIDGET_TEMPLATES:
        if d.id == template_id:
            widget = d.factory()
            widget.id = neue_id()
            return widget
    return None
