"""
PyroPlus: Bildschirm zusammensetzen.

Jedes Widget wird in einen eigenen Puffer gezeichnet, pixelgenau vermessen,
bei Bedarf gedreht und in den Bildschirmpuffer übernommen. Das Ergebnis sind
das Bild und die exakten Rahmen aller Widgets, die der Editor als
Trefferflächen nutzt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from oled.models import DisplayMode, Rotation, Screen, ScreenKind, Widget, WidgetBox
from oled.modes import get_mode
from oled.renderer import W, H, create_buffer
from oled.values import StatsSnapshot, ValueContext, get_source, resolve, split_disk_source
from oled.weather import WeatherReport

WeatherLookup = Callable[[Optional[str]], Optional[WeatherReport]]


@dataclass
class RenderContext:
    stats: StatsSnapshot
    now: datetime
    weather_for: WeatherLookup
    simulate: dict[str, float]


def _messen(buf: bytearray) -> Optional[tuple[int, int, int, int]]:
    """Belegter Bereich als (x0, y0, x1, y1) oder None bei leerem Puffer."""
    x0, y0, x1, y1 = W, H, -1, -1
    for y in range(H):
        zeile = buf[y * W:(y + 1) * W]
        if 1 not in zeile:
            continue
        erster = zeile.index(1)
        letzter = W - 1 - zeile[::-1].index(1)
        x0, x1 = min(x0, erster), max(x1, letzter)
        y0, y1 = min(y0, y), max(y1, y)
    if x1 < 0:
        return None
    return x0, y0, x1, y1


def _gedreht(quelle: bytearray, ox: int, oy: int, w: int, h: int, rot: Rotation) -> bytearray:
    """Dreht den Bereich (ox, oy, w, h) um die linke obere Ecke des Widgets."""
    ziel = create_buffer()
    for iy in range(h):
        for ix in range(w):
            if not quelle[(oy + iy) * W + (ox + ix)]:
                continue
            if rot == Rotation.r90:
                dx, dy = ox + h - 1 - iy, oy + ix
            elif rot == Rotation.r180:
                dx, dy = ox + w - 1 - ix, oy + h - 1 - iy
            elif rot == Rotation.r270:
                dx, dy = ox + iy, oy + w - 1 - ix
            else:
                dx, dy = ox + ix, oy + iy
            if 0 <= dx < W and 0 <= dy < H:
                ziel[dy * W + dx] = 1
    return ziel


def render_widget(widget: Widget, ctx: RenderContext) -> tuple[bytearray, WidgetBox]:
    """Zeichnet ein Widget in einen eigenen Puffer und misst seinen Rahmen."""
    buf = create_buffer()
    definition = get_mode(widget.display)
    quelle = get_source(widget.source)
    if definition is None:
        return buf, WidgetBox(id=widget.id, x=widget.x, y=widget.y, w=0, h=0)

    bericht = ctx.weather_for(widget.opts.location_id) if (quelle and quelle.uses_location) else None
    _, disk_index = split_disk_source(widget.source)
    vctx = ValueContext(stats=ctx.stats, now=ctx.now, opts=widget.opts, weather=bericht,
                        disk_index=disk_index or 0, simulate=ctx.simulate)
    wert = resolve(widget.source, vctx)
    definition.draw(buf, widget, wert, vctx)

    if widget.display == DisplayMode.bitmap:
        # Ein Pixelbild belegt immer seine Zeichenfläche, auch wenn noch kein Pixel gesetzt ist
        bw = max(1, min(widget.opts.width or 32, W - widget.x))
        bh = max(1, min(widget.opts.height or 16, H - widget.y))
        if widget.opts.rotate != Rotation.r0:
            buf = _gedreht(buf, widget.x, widget.y, bw, bh, widget.opts.rotate)
            if widget.opts.rotate in (Rotation.r90, Rotation.r270):
                bw, bh = bh, bw
        return buf, WidgetBox(id=widget.id, x=widget.x, y=widget.y, w=min(bw, W - widget.x), h=min(bh, H - widget.y))

    rahmen = _messen(buf)
    if rahmen is None:
        return buf, WidgetBox(id=widget.id, x=widget.x, y=widget.y, w=0, h=0)
    x0, y0, x1, y1 = rahmen

    if widget.opts.rotate != Rotation.r0:
        # Um die Widget-Ecke drehen, Bereich reicht von der Ecke bis zur Ausdehnung
        breite, hoehe = x1 - widget.x + 1, y1 - widget.y + 1
        buf = _gedreht(buf, widget.x, widget.y, max(1, breite), max(1, hoehe), widget.opts.rotate)
        rahmen = _messen(buf)
        if rahmen is None:
            return buf, WidgetBox(id=widget.id, x=widget.x, y=widget.y, w=0, h=0)
        x0, y0, x1, y1 = rahmen

    return buf, WidgetBox(id=widget.id, x=x0, y=y0, w=x1 - x0 + 1, h=y1 - y0 + 1)


def render_screen(screen: Screen, ctx: RenderContext) -> tuple[bytearray, list[WidgetBox]]:
    """Rendert einen Bildschirm; Wetterbildschirme kommen aus builtin.py."""
    buf = create_buffer()
    boxes: list[WidgetBox] = []
    if screen.kind != ScreenKind.widgets:
        from oled.builtin import render_builtin
        render_builtin(buf, screen, ctx)
        return buf, boxes
    gesamt = 0
    for widget in screen.widgets:
        teil, box = render_widget(widget, ctx)
        boxes.append(box)
        gesamt |= int.from_bytes(teil, "big")
    buf = bytearray(gesamt.to_bytes(W * H, "big"))
    return buf, boxes
