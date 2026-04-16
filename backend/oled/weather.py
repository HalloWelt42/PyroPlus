"""
PyroPlus — OLED Wetter-Modul
Daten von Open-Meteo API holen + Wetter-Screens rendern.
"""

import logging
import math
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from oled.renderer import (
    W, H, create_buffer, draw_text, draw_hline,
    draw_bar, draw_icon, set_pixel,
)
from oled.icons import ICONS_8x8, condition_to_icon

logger = logging.getLogger("oled.weather")
TZ = ZoneInfo("Europe/Berlin")


class WeatherProvider:
    """Holt und cached Wetterdaten von Open-Meteo."""

    def __init__(self):
        self.data: dict | None = None
        self.hourly: list[dict] = []
        self.daily: list[dict] = []
        self.alerts: list[dict] = []
        self.location: str = ""
        self.lat: float = 51.05
        self.lon: float = 12.13
        self._fetch_time: float = 0

    def needs_update(self) -> bool:
        return time.time() - self._fetch_time > 600  # 10 Min Cache

    def fetch(self):
        """Wetterdaten von Open-Meteo holen."""
        self._fetch_time = time.time()
        try:
            import httpx
            r = httpx.get(
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={self.lat}&longitude={self.lon}"
                f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,"
                f"weather_code,surface_pressure"
                f"&hourly=temperature_2m,weather_code,precipitation_probability"
                f"&daily=temperature_2m_max,temperature_2m_min,weather_code,"
                f"sunrise,sunset,precipitation_probability_max"
                f"&forecast_days=5&timezone=auto",
                timeout=10,
            )
            if r.status_code != 200:
                return
            data = r.json()
            current = data.get("current", {})

            self.data = {
                "temperature": current.get("temperature_2m"),
                "temp": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "pressure": current.get("surface_pressure"),
                "weather_code": current.get("weather_code"),
                "condition_text": self._wmo_to_text(current.get("weather_code")),
            }

            # Hourly
            hourly_raw = data.get("hourly", {})
            times = hourly_raw.get("time", [])
            temps = hourly_raw.get("temperature_2m", [])
            codes = hourly_raw.get("weather_code", [])
            probs = hourly_raw.get("precipitation_probability", [])
            now_h = datetime.now(TZ).hour
            self.hourly = []
            for i in range(len(times)):
                try:
                    h = int(times[i][-5:-3]) if times[i] else i
                except (ValueError, IndexError):
                    h = i
                if h >= now_h or len(self.hourly) > 0:
                    self.hourly.append({
                        "time": times[i] if i < len(times) else "",
                        "temperature": temps[i] if i < len(temps) else 0,
                        "weather_code": codes[i] if i < len(codes) else 0,
                        "condition_text": self._wmo_to_text(codes[i] if i < len(codes) else 0),
                        "precipitation_probability": probs[i] if i < len(probs) else 0,
                    })
                if len(self.hourly) >= 24:
                    break

            # Daily
            daily_raw = data.get("daily", {})
            dates = daily_raw.get("time", [])
            maxs = daily_raw.get("temperature_2m_max", [])
            mins = daily_raw.get("temperature_2m_min", [])
            d_codes = daily_raw.get("weather_code", [])
            sunrises = daily_raw.get("sunrise", [])
            sunsets = daily_raw.get("sunset", [])
            d_probs = daily_raw.get("precipitation_probability_max", [])
            self.daily = []
            for i in range(len(dates)):
                sr = sunrises[i] if i < len(sunrises) else ""
                ss = sunsets[i] if i < len(sunsets) else ""
                self.daily.append({
                    "date": dates[i],
                    "temperature_max": maxs[i] if i < len(maxs) else 0,
                    "temperature_min": mins[i] if i < len(mins) else 0,
                    "weather_code": d_codes[i] if i < len(d_codes) else 0,
                    "condition_text": self._wmo_to_text(d_codes[i] if i < len(d_codes) else 0),
                    "sunrise": sr[-5:] if len(sr) >= 5 else sr,
                    "sunset": ss[-5:] if len(ss) >= 5 else ss,
                    "precipitation_probability": d_probs[i] if i < len(d_probs) else 0,
                })

            # Sunrise/Sunset in current data
            if self.daily:
                self.data["sunrise"] = self.daily[0].get("sunrise", "")
                self.data["sunset"] = self.daily[0].get("sunset", "")

            logger.info(f"Wetter aktualisiert: {self.data.get('temperature')}°C")
        except Exception as e:
            logger.error(f"Wetter-Fetch: {e}")

    @staticmethod
    def _wmo_to_text(code) -> str:
        if code is None:
            return "---"
        if code == 0:
            return "Klar"
        if code <= 3:
            return "Bewoelkt"
        if code <= 49:
            return "Nebel"
        if code <= 59:
            return "Niesel"
        if code <= 69:
            return "Regen"
        if code <= 79:
            return "Schnee"
        if code <= 84:
            return "Schauer"
        return "Gewitter"


# ═══ Wetter-Screen-Renderer ═══

def render_weather_compact(buf: bytearray, weather: WeatherProvider):
    """Kompakte Wetter-Anzeige."""
    w = weather.data or {}
    now = datetime.now(TZ)
    loc = weather.location or "---"
    draw_text(buf, loc[:14], 0, 0, 1)
    draw_text(buf, now.strftime("%H:%M"), 96, 0, 1)

    temp = w.get("temperature", "--")
    cond = w.get("condition_text", "")
    icon_name = condition_to_icon(cond)
    icon_rows = ICONS_8x8.get(icon_name, [])

    draw_text(buf, f"{temp}\u00b0C", 0, 12, 2)
    if icon_rows:
        draw_icon(buf, icon_rows, 68, 12)
    draw_text(buf, cond[:10], 78, 14, 1)

    hum = w.get("humidity", "--")
    wind = w.get("wind_speed", "--")
    prs = w.get("pressure", "--")
    draw_text(buf, f"Feu.{hum}%", 0, 30, 1)
    draw_text(buf, f"W.{wind}km/h", 0, 40, 1)
    draw_text(buf, f"{prs}hPa", 66, 40, 1)

    sr = w.get("sunrise", "")
    ss = w.get("sunset", "")
    sun_icon = ICONS_8x8.get("sun", [])
    moon_icon = ICONS_8x8.get("moon", [])
    if sun_icon:
        draw_icon(buf, sun_icon, 0, 52)
    draw_text(buf, str(sr)[:5], 10, 54, 1)
    if moon_icon:
        draw_icon(buf, moon_icon, 70, 52)
    draw_text(buf, str(ss)[:5], 80, 54, 1)


def render_weather_hourly(buf: bytearray, weather: WeatherProvider):
    """6-Stunden Vorhersage."""
    draw_text(buf, "Naechste 6h", 2, 0, 1)
    hours = weather.hourly[:6]
    if not hours:
        draw_text(buf, "Keine Daten", 2, 28, 1)
        return
    for i, h in enumerate(hours):
        x = 2 + i * 21
        t_str = str(h.get("time", ""))[-5:-3] + "h" if h.get("time") else f"{i}h"
        draw_text(buf, t_str[:3], x, 12, 1)
        cond = h.get("condition_text", "")
        icon_name = condition_to_icon(cond)
        icon_rows = ICONS_8x8.get(icon_name, [])
        if icon_rows:
            draw_icon(buf, icon_rows, x + 2, 22)
        temp = h.get("temperature", "?")
        draw_text(buf, f"{temp}"[:4], x, 34, 1)
        rain = h.get("precipitation_probability", "")
        if rain:
            draw_text(buf, f"{rain}%"[:4], x, 44, 1)


def render_weather_daily(buf: bytearray, weather: WeatherProvider):
    """5-Tage Vorhersage."""
    draw_text(buf, "5-Tage", 2, 0, 1)
    draw_text(buf, (weather.location or "")[:10], 60, 0, 1)
    days = weather.daily[:5]
    if not days:
        draw_text(buf, "Keine Daten", 2, 28, 1)
        return
    days_de = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    for i, d in enumerate(days):
        y = 12 + i * 10
        wd = ""
        try:
            from datetime import datetime as dt2
            date_str = d.get("date", "")
            if date_str:
                dd = dt2.fromisoformat(date_str.split("T")[0])
                wd = days_de[dd.weekday()]
        except Exception:
            wd = f"T{i + 1}"
        draw_text(buf, wd[:2], 2, y, 1)
        cond = d.get("condition_text", "")
        icon_name = condition_to_icon(cond)
        icon_rows = ICONS_8x8.get(icon_name, [])
        if icon_rows:
            draw_icon(buf, icon_rows, 18, y)
        hi = d.get("temperature_max", "")
        lo = d.get("temperature_min", "")
        draw_text(buf, f"{hi}"[:4], 30, y, 1)
        draw_text(buf, f"{lo}"[:4], 54, y, 1)
        rain = d.get("precipitation_probability", "")
        if rain:
            draw_text(buf, f"{rain}%"[:4], 78, y, 1)
