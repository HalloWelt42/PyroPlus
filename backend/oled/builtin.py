"""
PyroPlus: fertige Bildschirmarten (Wetter kompakt, stündlich, täglich).

Diese Bildschirme bestehen nicht aus Widgets, sondern sind feste Layouts mit
Wettersymbolen. Sie hängen an einem Wetterort.
"""

from __future__ import annotations

from datetime import datetime

from oled.models import Screen, ScreenKind
from oled.renderer import draw_text
from oled.symbole import draw_symbol, symbol_fuer_wetter
from oled.values import TAGE_KURZ
from oled.weather import WeatherReport


def _icon(buf: bytearray, text: str, x: int, y: int) -> None:
    draw_symbol(buf, symbol_fuer_wetter(text), x, y, 8)


def render_builtin(buf: bytearray, screen: Screen, ctx: object) -> None:
    weather_for = getattr(ctx, "weather_for")
    now: datetime = getattr(ctx, "now")
    bericht: WeatherReport | None = weather_for(screen.location_id)
    if screen.kind == ScreenKind.weather_compact:
        _compact(buf, bericht, now)
    elif screen.kind == ScreenKind.weather_hourly:
        _hourly(buf, bericht)
    elif screen.kind == ScreenKind.weather_daily:
        _daily(buf, bericht)


def _compact(buf: bytearray, b: WeatherReport | None, now: datetime) -> None:
    draw_text(buf, (b.location_name if b else "---")[:14], 0, 0, 1)
    draw_text(buf, now.strftime("%H:%M"), 96, 0, 1)
    if b is None:
        draw_text(buf, "Keine Daten", 2, 28, 1)
        return
    c = b.current
    temp = f"{c.temperature:.1f}" if c.temperature is not None else "--"
    temp_text = f"{temp}°C"
    draw_text(buf, temp_text, 0, 12, 2)
    rechts = len(temp_text) * 12 + 2
    _icon(buf, c.condition_text, rechts, 12)
    draw_text(buf, c.condition_text[:8], rechts + 10, 14, 1)
    feuchte = f"{c.humidity:.0f}" if c.humidity is not None else "--"
    wind = f"{c.wind_speed:.0f}" if c.wind_speed is not None else "--"
    druck = f"{c.pressure:.0f}" if c.pressure is not None else "--"
    draw_text(buf, f"Feu.{feuchte}%", 0, 30, 1)
    draw_text(buf, f"W.{wind}km/h", 0, 40, 1)
    draw_text(buf, f"{druck}hPa", 66, 40, 1)
    draw_symbol(buf, "sonne", 0, 52, 8)
    draw_text(buf, c.sunrise[:5], 10, 54, 1)
    draw_symbol(buf, "mond", 70, 52, 8)
    draw_text(buf, c.sunset[:5], 80, 54, 1)


def _hourly(buf: bytearray, b: WeatherReport | None) -> None:
    draw_text(buf, "Nächste 6h", 2, 0, 1)
    stunden = b.hourly[:6] if b else []
    if not stunden:
        draw_text(buf, "Keine Daten", 2, 28, 1)
        return
    for i, h in enumerate(stunden):
        x = 2 + i * 21
        t = (h.time[-5:-3] + "h") if h.time else f"{i}h"
        draw_text(buf, t[:3], x, 12, 1)
        _icon(buf, h.condition_text, x + 2, 22)
        temp = f"{h.temperature:.0f}" if h.temperature is not None else "?"
        draw_text(buf, temp[:4], x, 34, 1)
        if h.precipitation_probability:
            draw_text(buf, f"{h.precipitation_probability:.0f}%"[:4], x, 44, 1)


def _daily(buf: bytearray, b: WeatherReport | None) -> None:
    draw_text(buf, "5 Tage", 2, 0, 1)
    draw_text(buf, (b.location_name if b else "")[:10], 60, 0, 1)
    tage = b.daily[:5] if b else []
    if not tage:
        draw_text(buf, "Keine Daten", 2, 28, 1)
        return
    for i, d in enumerate(tage):
        y = 12 + i * 10
        try:
            wochentag = TAGE_KURZ[datetime.fromisoformat(d.date.split("T")[0]).weekday()]
        except ValueError:
            wochentag = f"T{i + 1}"
        draw_text(buf, wochentag[:2], 2, y, 1)
        _icon(buf, d.condition_text, 18, y)
        hoch = f"{d.temperature_max:.0f}" if d.temperature_max is not None else ""
        tief = f"{d.temperature_min:.0f}" if d.temperature_min is not None else ""
        draw_text(buf, hoch[:4], 30, y, 1)
        draw_text(buf, tief[:4], 54, y, 1)
        if d.precipitation_probability:
            draw_text(buf, f"{d.precipitation_probability:.0f}%"[:4], 78, y, 1)
