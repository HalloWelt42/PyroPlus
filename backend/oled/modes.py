"""
PyroPlus: Darstellungsarten.

Jede Darstellungsart ist genau einmal registriert: Beschriftung, erlaubte
Wertarten, gültige Optionen, Vorgaben, benannte Varianten und die
Zeichenfunktion. Der Katalog für die Oberfläche entsteht aus dieser Liste.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from oled.models import DisplayMode, ModeVariant, ValueType, Widget, WidgetOpts
from oled.renderer import (
    W, H, draw_bar, draw_fan_icon, draw_gauge, draw_hline, draw_marquee, draw_rect,
    draw_section_header, draw_sparkline, draw_text, draw_text_ex, draw_vline,
)
from oled.values import Value, ValueContext

ZEILENHOEHE = 8  # 7 Pixel Schrift plus 1 Pixel Abstand

Drawer = Callable[[bytearray, Widget, Value, ValueContext], None]

ALL_DATA = [ValueType.number, ValueType.percent, ValueType.string, ValueType.time]
NUMERIC = [ValueType.number, ValueType.percent]


@dataclass(frozen=True)
class ModeDef:
    id: DisplayMode
    label: str
    for_types: list[ValueType]
    fields: list[str]
    defaults: WidgetOpts
    draw: Drawer
    description: str = ""
    variants: list[ModeVariant] = field(default_factory=list)


_MODES: dict[DisplayMode, ModeDef] = {}


def mode(id: DisplayMode, label: str, for_types: list[ValueType], fields: list[str],
         defaults: WidgetOpts, description: str = "",
         variants: Optional[list[ModeVariant]] = None) -> Callable[[Drawer], Drawer]:
    def wrap(fn: Drawer) -> Drawer:
        _MODES[id] = ModeDef(id, label, for_types, fields, defaults, fn, description, variants or [])
        return fn
    return wrap


def all_modes() -> list[ModeDef]:
    return list(_MODES.values())


def get_mode(id: DisplayMode) -> Optional[ModeDef]:
    return _MODES.get(id)


def modes_for_type(value_type: ValueType) -> list[ModeDef]:
    return [m for m in _MODES.values() if value_type in m.for_types]


def _variante(id: str, label: str, **opts: object) -> ModeVariant:
    return ModeVariant(id=id, label=label, opts=WidgetOpts(**opts))  # type: ignore[arg-type]


def _volltext(value: Value, opts: WidgetOpts) -> str:
    return f"{opts.prefix}{value.text}{opts.suffix}"


def _zeilen(buf: bytearray, text: str, x: int, y: int, opts: WidgetOpts,
            invert: bool, border: bool) -> None:
    """Text zeilenweise zeichnen; Zeilenumbruch trennt Zeilen."""
    sx, sy = opts.scale_x, opts.scale_y_effektiv
    erweitert = invert or border or opts.align.value != "left"
    for i, zeile in enumerate(text.split("\n")):
        zy = y + i * ZEILENHOEHE * sy + (i * 2 if (invert or border) else 0)
        if erweitert:
            draw_text_ex(buf, zeile, x, zy, sx, sy, invert=invert, border=border,
                         align=opts.align.value, box_w=opts.box_w)
        else:
            draw_text(buf, zeile, x, zy, sx, sy)


TEXT_FIELDS = ["scaleX", "scaleY", "prefix", "suffix", "decimals", "thousands", "align", "boxW", "rotate"]

TEXT_VARIANTS = [
    _variante("klein", "Klein (1x)", scale_x=1, scale_y=1),
    _variante("mittel", "Mittel (2x)", scale_x=2, scale_y=2),
    _variante("gross", "Groß (3x)", scale_x=3, scale_y=3),
    _variante("xxl", "XXL (4x)", scale_x=4, scale_y=4),
    _variante("breit", "Breit (2x1)", scale_x=2, scale_y=1),
    _variante("hoch", "Hoch (1x2)", scale_x=1, scale_y=2),
    _variante("extra_breit", "Extra breit (3x1)", scale_x=3, scale_y=1),
    _variante("extra_hoch", "Extra hoch (1x3)", scale_x=1, scale_y=3),
]


@mode(DisplayMode.text, "Zahl oder Text", ALL_DATA, TEXT_FIELDS, WidgetOpts(),
      description="Wert als Schrift; Größe über Skalierung", variants=TEXT_VARIANTS)
def _text(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    _zeilen(buf, _volltext(v, w.opts), w.x, w.y, w.opts, invert=False, border=False)


@mode(DisplayMode.text_invertiert, "Invertiert", ALL_DATA, TEXT_FIELDS, WidgetOpts(invert=True),
      description="Dunkle Schrift auf hellem Block", variants=TEXT_VARIANTS[:4])
def _text_inv(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    _zeilen(buf, _volltext(v, w.opts), w.x, w.y, w.opts, invert=True, border=False)


@mode(DisplayMode.text_rahmen, "Mit Rahmen", ALL_DATA, TEXT_FIELDS, WidgetOpts(border=True),
      description="Schrift mit Rahmen", variants=TEXT_VARIANTS[:3])
def _text_rahmen(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    _zeilen(buf, _volltext(v, w.opts), w.x, w.y, w.opts, invert=False, border=True)


BALKEN_VARIANTS = [
    _variante("standard", "Standard (60x6)", width=60, height=6),
    _variante("schmal", "Schmal (40x3)", width=40, height=3),
    _variante("breit", "Breit (80x8)", width=80, height=8),
    _variante("hoch", "Hoch (60x12)", width=60, height=12),
    _variante("voll", "Volle Breite (126x6)", width=126, height=6),
]


@mode(DisplayMode.balken, "Balken", NUMERIC, ["width", "height", "rotate"],
      WidgetOpts(width=60, height=6), description="Füllstand von 0 bis 100 Prozent", variants=BALKEN_VARIANTS)
def _balken(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    draw_bar(buf, w.x, w.y, w.opts.width or 60, w.opts.height or 6, v.percent_or_number)


@mode(DisplayMode.balken_label, "Balken + Wert", NUMERIC,
      ["width", "height", "scaleX", "scaleY", "prefix", "suffix", "decimals", "thousands", "rotate"],
      WidgetOpts(width=50, height=6, suffix="%"), description="Balken, daneben der Wert")
def _balken_label(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    bw, bh = w.opts.width or 50, w.opts.height or 6
    draw_bar(buf, w.x, w.y, bw, bh, v.percent_or_number)
    draw_text(buf, _volltext(v, w.opts), w.x + bw + 2, w.y, w.opts.scale_x, w.opts.scale_y_effektiv)


@mode(DisplayMode.balken_label_in, "Balken (Wert innen)", NUMERIC,
      ["width", "height", "prefix", "suffix", "decimals", "thousands", "rotate"],
      WidgetOpts(width=60, height=9), description="Balken mit dem Wert in der Mitte")
def _balken_label_in(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    bw, bh = w.opts.width or 60, w.opts.height or 9
    draw_bar(buf, w.x, w.y, bw, bh, v.percent_or_number)
    label = _volltext(v, w.opts)
    lw = len(label) * 6
    # Schrift invertiert über dem gefüllten Teil wäre unleserlich; daher XOR je Pixel
    tmp = bytearray(W * H)
    draw_text(tmp, label, w.x + (bw - lw) // 2, w.y + 1, 1, 1)
    for i in range(W * H):
        if tmp[i]:
            buf[i] = 0 if buf[i] else 1


@mode(DisplayMode.gauge, "Halbkreis", NUMERIC, ["radius", "prefix", "suffix", "decimals", "rotate"],
      WidgetOpts(radius=12, suffix="%"), description="Halbkreis mit Füllbogen und Wert",
      variants=[_variante("klein", "Klein (12)", radius=12), _variante("gross", "Groß (20)", radius=20),
                _variante("xl", "XL (28)", radius=28)])
def _gauge(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    draw_gauge(buf, v.percent_or_number, w.x, w.y, w.opts.radius or 12, label=_volltext(v, w.opts))


HISTORY_KEYS: dict[str, str] = {
    "cpu.percent": "cpu", "cpu.temp": "temp", "ram.percent": "ram",
    "fan.rpm": "fan_speed", "net.rx_raw": "net_rx", "net.tx_raw": "net_tx",
    "net.rx": "net_rx", "net.tx": "net_tx",
}


@mode(DisplayMode.sparkline, "Verlauf", NUMERIC, ["width", "height", "rotate"],
      WidgetOpts(width=50, height=16), description="Verlauf der letzten Minute",
      variants=[_variante("klein", "Klein (50x16)", width=50, height=16),
                _variante("gross", "Groß (80x24)", width=80, height=24),
                _variante("breit", "Breit (100x16)", width=100, height=16),
                _variante("voll", "Volle Breite (126x30)", width=126, height=30)])
def _sparkline(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    basis = w.source.rsplit(".", 1)[0] if w.source.count(".") == 2 else w.source
    schluessel = HISTORY_KEYS.get(w.source) or HISTORY_KEYS.get(basis, "")
    werte = ctx.history.get(schluessel, [])
    draw_sparkline(buf, werte, w.x, w.y, w.opts.width or 50, w.opts.height or 16)


@mode(DisplayMode.laufschrift, "Laufschrift", [ValueType.string, ValueType.time],
      ["text", "scaleX", "scaleY", "prefix", "suffix"], WidgetOpts(),
      description="Text läuft von rechts nach links durch")
def _laufschrift(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    text = _volltext(v, w.opts) or "Laufschrift"
    sx = w.opts.scale_x
    offset = int(time.time() * 30) % (len(text) * 6 * sx + W)
    draw_marquee(buf, text, w.y, offset, sx)


def _fan_frame(rpm: float) -> int:
    tempo = min(1.0, rpm / 3000)
    if tempo <= 0.01:
        return 0
    return int(time.time() * max(1.0, tempo * 12)) % 4


@mode(DisplayMode.fan_icon, "Lüftersymbol", [ValueType.animated], ["size", "rotate"],
      WidgetOpts(size=16), description="Dreht sich mit der Drehzahl",
      variants=[_variante("klein", "Klein (8)", size=8), _variante("mittel", "Mittel (16)", size=16),
                _variante("gross", "Groß (24)", size=24)])
def _fan_icon(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    draw_fan_icon(buf, w.x, w.y, w.opts.size or 16, _fan_frame(v.number or 0.0))


@mode(DisplayMode.fan_icon_rpm, "Symbol + Drehzahl", [ValueType.animated],
      ["size", "scaleX", "scaleY", "suffix"], WidgetOpts(size=16, suffix=" RPM"))
def _fan_icon_rpm(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    groesse = w.opts.size or 16
    rpm = v.number or 0.0
    draw_fan_icon(buf, w.x, w.y, groesse, _fan_frame(rpm))
    draw_text(buf, f"{round(rpm)}{w.opts.suffix}", w.x + groesse + 2, w.y + groesse // 2 - 3,
              w.opts.scale_x, w.opts.scale_y_effektiv)


@mode(DisplayMode.linie_h, "Linie waagerecht", [ValueType.shape], ["width"], WidgetOpts(width=60))
def _linie_h(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    draw_hline(buf, w.x, w.y, w.opts.width or 60)


@mode(DisplayMode.linie_v, "Linie senkrecht", [ValueType.shape], ["height"], WidgetOpts(height=20))
def _linie_v(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    draw_vline(buf, w.x, w.y, w.opts.height or 20)


@mode(DisplayMode.rahmen, "Rahmen", [ValueType.shape], ["width", "height"], WidgetOpts(width=40, height=20))
def _rahmen(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    draw_rect(buf, w.x, w.y, w.x + (w.opts.width or 40) - 1, w.y + (w.opts.height or 20) - 1, filled=False)


@mode(DisplayMode.block, "Block gefüllt", [ValueType.shape], ["width", "height"], WidgetOpts(width=40, height=20))
def _block(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    draw_rect(buf, w.x, w.y, w.x + (w.opts.width or 40) - 1, w.y + (w.opts.height or 20) - 1, filled=True)


@mode(DisplayMode.section, "Trennlinie mit Titel", [ValueType.shape], ["width", "text"],
      WidgetOpts(width=60, text="CPU"))
def _section(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    draw_section_header(buf, w.opts.text or "", w.x, w.y, w.opts.width or 60)


# Pixelbild: Bits zeilenweise gepackt, jede Zeile beginnt an einer Bytegrenze.

def pack_bitmap(rows: list[list[int]]) -> str:
    """Zeilen aus 0/1 zu Base64 packen."""
    daten = bytearray()
    for zeile in rows:
        byte = 0
        bits = 0
        for pixel in zeile:
            byte = (byte << 1) | (1 if pixel else 0)
            bits += 1
            if bits == 8:
                daten.append(byte)
                byte, bits = 0, 0
        if bits:
            daten.append(byte << (8 - bits))
    return base64.b64encode(bytes(daten)).decode("ascii")


def unpack_bitmap(encoded: str, width: int, height: int) -> list[list[int]]:
    """Base64 zu Zeilen aus 0/1; fehlende Daten werden als 0 ergänzt."""
    try:
        daten = base64.b64decode(encoded or "")
    except Exception:
        daten = b""
    breite_bytes = (width + 7) // 8
    rows: list[list[int]] = []
    for y in range(height):
        zeile: list[int] = []
        for x in range(width):
            index = y * breite_bytes + x // 8
            byte = daten[index] if index < len(daten) else 0
            zeile.append((byte >> (7 - x % 8)) & 1)
        rows.append(zeile)
    return rows


@mode(DisplayMode.bitmap, "Pixelbild", [ValueType.bitmap], ["width", "height", "invert", "rotate"],
      WidgetOpts(width=32, height=16), description="Frei gezeichnete Pixel")
def _bitmap(buf: bytearray, w: Widget, v: Value, ctx: ValueContext) -> None:
    breite, hoehe = w.opts.width or 32, w.opts.height or 16
    rows = unpack_bitmap(w.opts.bitmap or "", breite, hoehe)
    for ry, zeile in enumerate(rows):
        for rx, pixel in enumerate(zeile):
            an = (not pixel) if w.opts.invert else bool(pixel)
            px, py = w.x + rx, w.y + ry
            if an and 0 <= px < W and 0 <= py < H:
                buf[py * W + px] = 1
