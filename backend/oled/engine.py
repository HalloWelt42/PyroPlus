"""
PironMan Deluxe v2.5.4 — OLED Display Engine
© HalloWelt42 - Nur für private Nutzung

Vollständiges Rendering für SSD1306 128×64 OLED:
 - System-Widgets (CPU, RAM, Disk, Docker, Netzwerk)
 - Wetter-Screens (W1-W9) mit Pixel-Art Icons
 - Custom Text (frei editierbar, 4 Zeilen, Font-Größe)
 - Pixel-Editor (128×64 freies Bitmap)
 - Laufschrift (Marquee mit Speed/Font)
 - Uhr (Blinken, Sekunden, Zehntel, Datum, 24h/12h)
 - Alles persistiert in /app/data/
"""

import threading
import time
import base64
import io
import json
import math
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import hw_client
from config import OLED_WIDTH, OLED_HEIGHT, OLED_DEFAULT_BRIGHTNESS, OLED_ROTATION_INTERVAL, DATA_DIR
from stats import get_system_stats
from oled.icons import draw_icon, condition_to_icon

logger = logging.getLogger("oled")

W, H = OLED_WIDTH, OLED_HEIGHT
TZ = ZoneInfo("Europe/Berlin")
PIXEL_DIR = DATA_DIR / "pixel_screens"
PIXEL_DIR.mkdir(parents=True, exist_ok=True)

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False
    logger.warning("Pillow nicht installiert — OLED deaktiviert")


def _font(size=10, bold=False):
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            pass
    return ImageFont.load_default()


# Pre-load fonts
F_SM = _font(8) if PIL_OK else None
F_MD = _font(11) if PIL_OK else None
F_LG = _font(18, bold=True) if PIL_OK else None
F_XL = _font(26, bold=True) if PIL_OK else None


class OLEDEngine:
    def __init__(self):
        self.enabled = False
        self.brightness = OLED_DEFAULT_BRIGHTNESS
        self.rotation_interval = OLED_ROTATION_INTERVAL
        self.mode = "auto"
        self.current_screen = 0
        self._last_preview: Optional[str] = None
        self._weather_data: Optional[dict] = None
        self._weather_hourly: list = []
        self._weather_daily: list = []
        self._weather_alerts: list = []
        self._weather_aqi: Optional[dict] = None
        self._weather_location: str = ""
        self._weather_fetch_time: float = 0
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._rotation_reset = False

        # ─── Screen-Liste ───────────────────────────────
        # Jeder Screen hat: type, name, + type-spezifische Felder
        self.screens: list[dict] = []

        # ─── Clock Settings ─────────────────────────────
        self.clock_settings = {
            "blink": True,
            "seconds": False,
            "tenths": False,
            "date": True,
            "weekday": True,
            "format_24h": True,
        }

        # ─── Custom Texts ───────────────────────────────
        # Liste von gespeicherten Texten: {id, lines[], font_scale, align}
        self.custom_texts: list[dict] = []

        # ─── Marquee Settings ───────────────────────────
        self.marquees: list[dict] = []

        # Hardware-Check
        self.enabled = hw_client.oled_available()
        hw_client.oled_brightness(self.brightness)
        logger.info(f"OLED verfügbar: {self.enabled}")

        self._load_settings()
        if not self.screens:
            self._create_defaults()

    # ═══════════════════════════════════════════════════════
    #  DEFAULT SCREENS
    # ═══════════════════════════════════════════════════════
    def _create_defaults(self):
        self.screens = [
            {"type": "clock", "name": "Uhr"},
            {"type": "system", "name": "System", "widgets": [
                {"type": "clock", "x": 0, "y": 0, "size": "large"},
                {"type": "cpu_temp", "x": 0, "y": 22, "size": "small"},
                {"type": "ram_bar", "x": 0, "y": 32, "size": "small"},
                {"type": "disk", "x": 0, "y": 44, "size": "small"},
                {"type": "uptime", "x": 0, "y": 54, "size": "small"},
            ]},
            {"type": "weather_compact", "name": "Wetter"},
            {"type": "weather_hourly", "name": "Stündlich"},
            {"type": "weather_daily", "name": "5 Tage"},
        ]
        self._save_settings()

    # ═══════════════════════════════════════════════════════
    #  MAIN RENDER
    # ═══════════════════════════════════════════════════════
    def render(self, stats: dict) -> Optional[str]:
        if not PIL_OK:
            return None
        with self._lock:
            img = Image.new("1", (W, H), 0)
            draw = ImageDraw.Draw(img)

            if self.mode != "off" and self.screens:
                idx = min(self.current_screen, len(self.screens) - 1)
                screen = self.screens[idx]
                stype = screen.get("type", "system")

                if stype == "system":
                    self._render_system(draw, screen, stats)
                elif stype == "clock":
                    self._render_clock_screen(draw)
                elif stype.startswith("weather_"):
                    self._render_weather(draw, stype, stats)
                elif stype == "custom_text":
                    self._render_custom_text(draw, screen)
                elif stype == "pixel_art":
                    self._render_pixel_art(draw, screen)
                elif stype == "marquee":
                    self._render_marquee(draw, screen)

            # Hardware senden
            if self.mode != "off":
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                hw_client.oled_display(base64.b64encode(buf.getvalue()).decode())
            else:
                hw_client.oled_clear()

            # 4× Preview für Frontend
            scaled = img.resize((W * 4, H * 4), Image.NEAREST)
            buf = io.BytesIO()
            scaled.save(buf, format="PNG")
            self._last_preview = base64.b64encode(buf.getvalue()).decode()
            return self._last_preview

    # ═══════════════════════════════════════════════════════
    #  CLOCK SCREEN
    # ═══════════════════════════════════════════════════════
    def _render_clock_screen(self, draw):
        now = datetime.now(TZ)
        cs = self.clock_settings
        fmt_24 = cs.get("format_24h", True)

        # Uhrzeit
        if fmt_24:
            h_str = now.strftime("%H")
        else:
            h_str = now.strftime("%I")
        m_str = now.strftime("%M")

        # Blinken: Doppelpunkt jede Sekunde ein/aus
        blink = cs.get("blink", True)
        colon = ":" if not blink or now.second % 2 == 0 else " "

        time_str = f"{h_str}{colon}{m_str}"
        draw.text((2, 2), time_str, fill=1, font=F_XL)

        # Sekunden
        if cs.get("seconds", False):
            sec_str = f":{now.strftime('%S')}"
            if cs.get("tenths", False):
                tenth = now.microsecond // 100000
                sec_str += f".{tenth}"
            draw.text((98, 8), sec_str, fill=1, font=F_MD)

        # Datum + Wochentag
        y_pos = 34
        if cs.get("weekday", True):
            days_de = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
            draw.text((2, y_pos), days_de[now.weekday()], fill=1, font=F_MD)
            y_pos += 14

        if cs.get("date", True):
            draw.text((2, y_pos), now.strftime("%d.%m.%Y"), fill=1, font=F_MD)

        # AM/PM wenn 12h
        if not fmt_24:
            draw.text((100, 34), now.strftime("%p"), fill=1, font=F_SM)

    # ═══════════════════════════════════════════════════════
    #  SYSTEM WIDGETS — ATOMARE ELEMENTE
    # ═══════════════════════════════════════════════════════
    WIDGET_CATALOG = {
        # ─── Zeit ───
        "clock":        {"cat": "zeit",    "label": "Uhr HH:MM",       "w": 58, "h": 18, "font": "lg"},
        "clock_hms":    {"cat": "zeit",    "label": "Uhr HH:MM:SS",    "w": 48, "h": 10, "font": "sm"},
        "clock_large":  {"cat": "zeit",    "label": "Uhr Groß",        "w": 96, "h": 26, "font": "xl"},
        "date":         {"cat": "zeit",    "label": "Datum",            "w": 58, "h": 10, "font": "sm"},
        "weekday":      {"cat": "zeit",    "label": "Wochentag",        "w": 14, "h": 10, "font": "sm"},
        "datetime_full":{"cat": "zeit",    "label": "Datum + Tag",      "w": 72, "h": 10, "font": "sm"},
        # ─── System ───
        "cpu_temp":     {"cat": "system",  "label": "CPU Temp+%",       "w": 82, "h": 10, "font": "sm"},
        "cpu_temp_only":{"cat": "system",  "label": "CPU °C",           "w": 30, "h": 10, "font": "sm"},
        "cpu_pct":      {"cat": "system",  "label": "CPU %",            "w": 32, "h": 10, "font": "sm"},
        "cpu_bar":      {"cat": "system",  "label": "CPU Balken",       "w": 60, "h": 6,  "font": ""},
        "ram_bar":      {"cat": "system",  "label": "RAM Text",         "w": 82, "h": 10, "font": "sm"},
        "ram_pct":      {"cat": "system",  "label": "RAM %",            "w": 32, "h": 10, "font": "sm"},
        "ram_bar_gfx":  {"cat": "system",  "label": "RAM Balken",       "w": 60, "h": 6,  "font": ""},
        "disk":         {"cat": "system",  "label": "Disk Text",        "w": 72, "h": 10, "font": "sm"},
        "disk_pct":     {"cat": "system",  "label": "Disk %",           "w": 32, "h": 10, "font": "sm"},
        "disk_bar":     {"cat": "system",  "label": "Disk Balken",      "w": 60, "h": 6,  "font": ""},
        "docker":       {"cat": "system",  "label": "Docker",           "w": 60, "h": 10, "font": "sm"},
        "ip":           {"cat": "system",  "label": "IP-Adresse",       "w": 82, "h": 10, "font": "sm"},
        "uptime":       {"cat": "system",  "label": "Uptime",           "w": 60, "h": 10, "font": "sm"},
        "network":      {"cat": "netzwerk","label": "Netz Rx/Tx",       "w": 82, "h": 10, "font": "sm"},
        "net_rx":       {"cat": "netzwerk","label": "Download",          "w": 52, "h": 10, "font": "sm"},
        "net_tx":       {"cat": "netzwerk","label": "Upload",            "w": 52, "h": 10, "font": "sm"},
        # ─── Wetter ───
        "weather":      {"cat": "wetter",  "label": "Wetter Mini",      "w": 72, "h": 10, "font": "sm"},
        "w_temp":       {"cat": "wetter",  "label": "Temperatur",       "w": 36, "h": 18, "font": "lg"},
        "w_temp_sm":    {"cat": "wetter",  "label": "Temp Klein",       "w": 28, "h": 10, "font": "sm"},
        "w_feels":      {"cat": "wetter",  "label": "Gefühlt",          "w": 52, "h": 10, "font": "sm"},
        "w_icon":       {"cat": "wetter",  "label": "Wetter-Icon",      "w": 16, "h": 16, "font": ""},
        "w_icon_sm":    {"cat": "wetter",  "label": "Icon Klein",       "w": 8,  "h": 8,  "font": ""},
        "w_cond":       {"cat": "wetter",  "label": "Beschreibung",     "w": 48, "h": 10, "font": "sm"},
        "w_hum":        {"cat": "wetter",  "label": "Feuchtigkeit",     "w": 32, "h": 10, "font": "sm"},
        "w_wind":       {"cat": "wetter",  "label": "Wind",             "w": 48, "h": 10, "font": "sm"},
        "w_press":      {"cat": "wetter",  "label": "Luftdruck",        "w": 52, "h": 10, "font": "sm"},
        "w_sunrise":    {"cat": "wetter",  "label": "Sonnenaufgang",    "w": 42, "h": 10, "font": "sm"},
        "w_sunset":     {"cat": "wetter",  "label": "Sonnenuntergang",  "w": 42, "h": 10, "font": "sm"},
        "w_uv":         {"cat": "wetter",  "label": "UV-Index",         "w": 24, "h": 10, "font": "sm"},
        "w_location":   {"cat": "wetter",  "label": "Ort",              "w": 52, "h": 10, "font": "sm"},
        # ─── Deko ───
        "label":        {"cat": "deko",    "label": "Text",             "w": 48, "h": 10, "font": "sm"},
        "line_h":       {"cat": "deko",    "label": "Linie ─",          "w": 60, "h": 1,  "font": ""},
        "line_v":       {"cat": "deko",    "label": "Linie │",          "w": 1,  "h": 20, "font": ""},
        "rect":         {"cat": "deko",    "label": "Rahmen □",         "w": 40, "h": 20, "font": ""},
        "icon":         {"cat": "deko",    "label": "Mini-Icon",        "w": 8,  "h": 8,  "font": ""},
    }

    def _render_system(self, draw, screen, stats):
        for widget in screen.get("widgets", []):
            self._render_widget(draw, widget, stats)

    def _render_widget(self, draw, widget, stats):
        x, y = widget.get("x", 0), widget.get("y", 0)
        wt = widget.get("type", "")
        font_key = widget.get("font", "sm")
        font = {"sm": F_SM, "md": F_MD, "lg": F_LG, "xl": F_XL}.get(font_key, F_SM)

        cpu = stats.get("cpu", {})
        ram = stats.get("ram", {})
        disks = stats.get("disks", [])
        disk = disks[0] if disks else {}
        docker = stats.get("docker", {})
        uptime = stats.get("uptime", {})
        net = stats.get("network", {})
        w = self._weather_data or {}
        now = datetime.now(TZ)
        cs = self.clock_settings

        # ═══ ZEIT ═══
        if wt == "clock":
            colon = ":" if not cs.get("blink") or now.second % 2 == 0 else " "
            f = F_LG if widget.get("size") == "large" or font_key == "lg" else font
            draw.text((x, y), f"{now.strftime('%H')}{colon}{now.strftime('%M')}", fill=1, font=f)
        elif wt == "clock_hms":
            draw.text((x, y), now.strftime("%H:%M:%S"), fill=1, font=font)
        elif wt == "clock_large":
            colon = ":" if not cs.get("blink") or now.second % 2 == 0 else " "
            draw.text((x, y), f"{now.strftime('%H')}{colon}{now.strftime('%M')}", fill=1, font=F_XL)
        elif wt == "date":
            draw.text((x, y), now.strftime("%d.%m.%Y"), fill=1, font=font)
        elif wt == "weekday":
            days_de = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
            draw.text((x, y), days_de[now.weekday()], fill=1, font=font)
        elif wt == "datetime_full":
            days_de = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
            draw.text((x, y), f"{days_de[now.weekday()]} {now.strftime('%d.%m.%Y')}", fill=1, font=font)

        # ═══ SYSTEM ═══
        elif wt == "cpu_temp":
            t, p = cpu.get("temp", 0), cpu.get("percent", 0)
            draw_icon(draw, "thermo", x, y, 8)
            draw.text((x + 10, y), f"{t:.0f}C  CPU {p:.0f}%", fill=1, font=font)
        elif wt == "cpu_temp_only":
            draw.text((x, y), f"{cpu.get('temp', 0):.0f}°C", fill=1, font=font)
        elif wt == "cpu_pct":
            draw.text((x, y), f"CPU {cpu.get('percent', 0):.0f}%", fill=1, font=font)
        elif wt == "cpu_bar":
            bw = widget.get("w", 60)
            bh = widget.get("h", 6)
            draw.rectangle([x, y, x + bw, y + bh], outline=1)
            fill = int(bw * min(100, cpu.get("percent", 0)) / 100)
            if fill > 0:
                draw.rectangle([x, y, x + fill, y + bh], fill=1)
        elif wt == "ram_bar":
            u, t2, pct = ram.get("used_gb", 0), ram.get("total_gb", 1), ram.get("percent", 0)
            draw.text((x, y), f"RAM {u:.1f}/{t2:.1f}G {pct:.0f}%", fill=1, font=font)
        elif wt == "ram_pct":
            draw.text((x, y), f"RAM {ram.get('percent', 0):.0f}%", fill=1, font=font)
        elif wt == "ram_bar_gfx":
            bw = widget.get("w", 60)
            bh = widget.get("h", 6)
            draw.rectangle([x, y, x + bw, y + bh], outline=1)
            fill = int(bw * min(100, ram.get("percent", 0)) / 100)
            if fill > 0:
                draw.rectangle([x, y, x + fill, y + bh], fill=1)
        elif wt == "disk":
            draw.text((x, y), f"DSK {disk.get('used_gb', 0):.0f}/{disk.get('total_gb', 1):.0f}G", fill=1, font=font)
        elif wt == "disk_pct":
            draw.text((x, y), f"DSK {disk.get('percent', 0)}%", fill=1, font=font)
        elif wt == "disk_bar":
            bw = widget.get("w", 60)
            bh = widget.get("h", 6)
            draw.rectangle([x, y, x + bw, y + bh], outline=1)
            fill = int(bw * min(100, disk.get("percent", 0)) / 100)
            if fill > 0:
                draw.rectangle([x, y, x + fill, y + bh], fill=1)
        elif wt == "docker":
            draw.text((x, y), f"Docker: {docker.get('running', 0)} up", fill=1, font=font)
        elif wt == "ip":
            draw.text((x, y), f"IP {net.get('ip', 'N/A')}", fill=1, font=font)
        elif wt == "uptime":
            draw.text((x, y), f"Up {uptime.get('formatted', '--')}", fill=1, font=font)

        # ═══ NETZWERK ═══
        elif wt == "network" or wt == "network_io":
            rx = net.get("rx_bytes_sec", 0) / 1024
            tx = net.get("tx_bytes_sec", 0) / 1024
            draw.text((x, y), f"Rx{rx:.0f} Tx{tx:.0f} KB/s", fill=1, font=font)
        elif wt == "net_rx":
            rx = net.get("rx_bytes_sec", 0) / 1024
            draw.text((x, y), f"↓{rx:.0f}KB/s", fill=1, font=font)
        elif wt == "net_tx":
            tx = net.get("tx_bytes_sec", 0) / 1024
            draw.text((x, y), f"↑{tx:.0f}KB/s", fill=1, font=font)

        # ═══ WETTER ═══
        elif wt == "weather":
            self._draw_weather_mini(draw, x, y)
        elif wt == "w_temp":
            temp = w.get("temperature", w.get("temp", "--"))
            draw.text((x, y), f"{temp}°", fill=1, font=font)
        elif wt == "w_temp_sm":
            temp = w.get("temperature", w.get("temp", "--"))
            draw.text((x, y), f"{temp}°C", fill=1, font=font)
        elif wt == "w_feels":
            feels = w.get("feels_like", w.get("feelslike", "--"))
            draw.text((x, y), f"Gef.{feels}°", fill=1, font=font)
        elif wt == "w_icon":
            cond = w.get("condition_text", w.get("condition", ""))
            draw_icon(draw, condition_to_icon(cond), x, y, 16)
        elif wt == "w_icon_sm":
            cond = w.get("condition_text", w.get("condition", ""))
            draw_icon(draw, condition_to_icon(cond), x, y, 8)
        elif wt == "w_cond":
            cond = w.get("condition_text", w.get("condition", "?"))
            draw.text((x, y), str(cond)[:10], fill=1, font=font)
        elif wt == "w_hum":
            hum = w.get("humidity", "--")
            draw.text((x, y), f"{hum}%", fill=1, font=font)
        elif wt == "w_wind":
            spd = w.get("wind_speed", w.get("windspeed", "--"))
            draw.text((x, y), f"{spd}km/h", fill=1, font=font)
        elif wt == "w_press":
            prs = w.get("pressure", "--")
            draw.text((x, y), f"{prs}hPa", fill=1, font=font)
        elif wt == "w_sunrise":
            sr = str(w.get("sunrise", "--"))[:5]
            draw_icon(draw, "sun", x, y, 8)
            draw.text((x + 10, y), sr, fill=1, font=font)
        elif wt == "w_sunset":
            ss = str(w.get("sunset", "--"))[:5]
            draw_icon(draw, "moon", x, y, 8)
            draw.text((x + 10, y), ss, fill=1, font=font)
        elif wt == "w_uv":
            uv = w.get("uv_index", w.get("uv", "--"))
            draw.text((x, y), f"UV{uv}", fill=1, font=font)
        elif wt == "w_location":
            loc = self._weather_location or "---"
            draw.text((x, y), loc[:12], fill=1, font=font)

        # ═══ DEKO ═══
        elif wt == "label":
            text = widget.get("text", "Text")
            draw.text((x, y), text, fill=1, font=font)
        elif wt == "line_h":
            lw = widget.get("w", 60)
            draw.line([(x, y), (x + lw, y)], fill=1)
        elif wt == "line_v":
            lh = widget.get("h", 20)
            draw.line([(x, y), (x, y + lh)], fill=1)
        elif wt == "rect":
            rw = widget.get("w", 40)
            rh = widget.get("h", 20)
            draw.rectangle([x, y, x + rw, y + rh], outline=1)
        elif wt == "icon":
            icon_name = widget.get("icon", "thermo")
            draw_icon(draw, icon_name, x, y, 8)

    def _draw_weather_mini(self, draw, x, y):
        w = self._weather_data
        if w:
            temp = w.get("temperature", w.get("temp", "?"))
            cond = w.get("condition_text", w.get("condition", ""))
            icon = condition_to_icon(cond)
            draw_icon(draw, icon, x, y, 8)
            draw.text((x + 10, y), f"{temp}C {cond[:10]}", fill=1, font=F_SM)
        else:
            draw.text((x, y), "Wetter: ---", fill=1, font=F_SM)

    # ═══════════════════════════════════════════════════════
    #  WEATHER SCREENS
    # ═══════════════════════════════════════════════════════
    def _render_weather(self, draw, stype, stats):
        w = self._weather_data or {}

        if stype == "weather_hero":
            self._render_w_hero(draw, w)
        elif stype == "weather_compact":
            self._render_w_compact(draw, w)
        elif stype == "weather_hourly":
            self._render_w_hourly(draw)
        elif stype == "weather_daily":
            self._render_w_daily(draw)
        elif stype == "weather_wind":
            self._render_w_wind(draw, w)
        elif stype == "weather_sun":
            self._render_w_sun(draw, w)
        elif stype == "weather_rain":
            self._render_w_rain(draw)
        elif stype == "weather_alert":
            self._render_w_alert(draw)
        elif stype == "weather_aqi":
            self._render_w_aqi(draw)

    def _render_w_hero(self, draw, w):
        """W1: Grosse Temperatur + Icon."""
        temp = w.get("temperature", w.get("temp", "--"))
        feels = w.get("feels_like", "")
        cond = w.get("condition_text", w.get("condition", ""))
        icon = condition_to_icon(cond)

        draw.text((2, 2), f"{temp}C", fill=1, font=F_XL)
        draw_icon(draw, icon, 100, 2, 16)
        if cond:
            draw.text((80, 20), cond[:8], fill=1, font=F_SM)
        if feels:
            draw.text((2, 32), f"Gefuehlt {feels}C", fill=1, font=F_SM)

        hum = w.get("humidity", "")
        wind = w.get("wind_speed", "")
        pres = w.get("pressure", "")
        draw_icon(draw, "drop", 2, 44, 8)
        draw.text((12, 44), f"{hum}%", fill=1, font=F_SM)
        draw_icon(draw, "wind", 42, 44, 8)
        draw.text((52, 44), f"{wind}km/h", fill=1, font=F_SM)
        draw.text((2, 54), f"{pres}hPa", fill=1, font=F_SM)

    def _render_w_compact(self, draw, w):
        """W2: Kompakt mit Ort + Uhrzeit."""
        now = datetime.now(TZ)
        loc = self._weather_location or "---"
        draw.text((2, 0), loc[:12], fill=1, font=F_SM)
        draw.text((96, 0), now.strftime("%H:%M"), fill=1, font=F_SM)

        temp = w.get("temperature", w.get("temp", "--"))
        cond = w.get("condition_text", w.get("condition", ""))
        icon = condition_to_icon(cond)

        draw.text((2, 12), f"{temp}C", fill=1, font=F_LG)
        draw_icon(draw, icon, 68, 12, 8)
        if cond:
            draw.text((78, 12), cond[:8], fill=1, font=F_SM)

        feels = w.get("feels_like", "")
        hum = w.get("humidity", "")
        wind = w.get("wind_speed", "")
        draw.text((2, 34), f"Gef.{feels}C", fill=1, font=F_SM)
        draw.text((48, 34), f"Feu.{hum}%", fill=1, font=F_SM)
        draw.text((90, 34), f"W.{wind}", fill=1, font=F_SM)

        sunrise = w.get("sunrise", "")
        sunset = w.get("sunset", "")
        uv = w.get("uv_index", "")
        draw_icon(draw, "sun", 2, 46, 8)
        draw.text((12, 48), str(sunrise)[:5], fill=1, font=F_SM)
        draw.text((50, 48), f"UV {uv}", fill=1, font=F_SM)
        draw_icon(draw, "moon", 86, 46, 8)
        draw.text((96, 48), str(sunset)[:5], fill=1, font=F_SM)

    def _render_w_hourly(self, draw):
        """W3: 6-Stunden Vorhersage."""
        draw.text((2, 0), "Naechste 6h", fill=1, font=F_SM)
        hours = self._weather_hourly[:6]
        if not hours:
            draw.text((2, 28), "Keine Daten", fill=1, font=F_MD)
            return

        for i, h in enumerate(hours):
            x = 2 + i * 21
            t_str = str(h.get("time", ""))[-5:-3] + "h" if h.get("time") else f"{i}h"
            draw.text((x, 12), t_str[:3], fill=1, font=F_SM)
            cond = h.get("condition_text", h.get("condition", ""))
            draw_icon(draw, condition_to_icon(cond), x + 2, 22, 8)
            temp = h.get("temp", h.get("temperature", "?"))
            draw.text((x, 32), f"{temp}".rstrip(".0")[:3], fill=1, font=F_SM)
            rain = h.get("rain_chance", h.get("precipitation_probability", ""))
            draw.text((x, 42), f"{rain}%"[:4] if rain else "", fill=1, font=F_SM)

    def _render_w_daily(self, draw):
        """W4: 5-Tage Vorhersage."""
        draw.text((2, 0), "5-Tage", fill=1, font=F_SM)
        draw.text((80, 0), self._weather_location[:8] or "", fill=1, font=F_SM)
        days = self._weather_daily[:5]
        if not days:
            draw.text((2, 28), "Keine Daten", fill=1, font=F_MD)
            return

        days_de = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        for i, d in enumerate(days):
            y = 12 + i * 10
            # Wochentag
            wd = d.get("weekday", "")
            if not wd:
                try:
                    from datetime import datetime as dt2
                    date_str = d.get("date", "")
                    if date_str:
                        dd = dt2.fromisoformat(date_str.split("T")[0])
                        wd = days_de[dd.weekday()]
                except Exception:
                    wd = f"T{i+1}"
            draw.text((2, y), str(wd)[:2], fill=1, font=F_SM)
            cond = d.get("condition_text", d.get("condition", ""))
            draw_icon(draw, condition_to_icon(cond), 18, y, 8)
            hi = d.get("temp_high", d.get("temperature_max", ""))
            lo = d.get("temp_low", d.get("temperature_min", ""))
            draw.text((30, y), f"{hi}".rstrip(".0")[:3], fill=1, font=F_SM)
            draw.text((52, y), f"{lo}".rstrip(".0")[:3], fill=1, font=F_SM)
            rain = d.get("rain_chance", d.get("precipitation_probability", ""))
            draw.text((74, y), f"{rain}%"[:4] if rain else "", fill=1, font=F_SM)

    def _render_w_wind(self, draw, w):
        """W5: Wind-Details mit Kompass."""
        draw.text((2, 0), "WIND", fill=1, font=F_SM)
        # Kompass-Kreis
        cx, cy, r = 30, 34, 18
        for a in range(0, 360, 5):
            rad = math.radians(a)
            px_x = round(cx + r * math.cos(rad))
            px_y = round(cy + r * math.sin(rad))
            draw.point((px_x, px_y), fill=1)
        draw.text((27, 13), "N", fill=1, font=F_SM)
        draw.text((27, 52), "S", fill=1, font=F_SM)
        draw.text((8, 32), "W", fill=1, font=F_SM)
        draw.text((47, 32), "O", fill=1, font=F_SM)
        # Windrichtung als Linie
        wind_dir = w.get("wind_dir", w.get("wind_direction", 0))
        try:
            angle = float(wind_dir) if isinstance(wind_dir, (int, float)) else 0
        except (ValueError, TypeError):
            angle = 0
        rad = math.radians(angle - 90)  # 0° = Nord
        for i in range(1, 14):
            lx = round(cx + i * math.cos(rad))
            ly = round(cy + i * math.sin(rad))
            draw.point((lx, ly), fill=1)
            draw.point((lx + 1, ly), fill=1)

        # Werte rechts
        speed = w.get("wind_speed", "?")
        gust = w.get("wind_gust", "")
        draw.text((64, 12), "Geschw.", fill=1, font=F_SM)
        draw.text((64, 22), f"{speed} km/h", fill=1, font=F_MD)
        if gust:
            draw.text((64, 38), f"Boeen {gust}", fill=1, font=F_SM)

    def _render_w_sun(self, draw, w):
        """W6: Sonnenauf-/untergang mit Bogen."""
        draw.text((2, 0), "SONNENSTAND", fill=1, font=F_SM)
        sunrise = str(w.get("sunrise", "06:00"))[:5]
        sunset = str(w.get("sunset", "20:00"))[:5]

        # Bogen
        for a in range(180, 361, 2):
            rad = math.radians(a)
            ax = round(64 + 48 * math.cos(rad))
            ay = round(40 + 22 * math.sin(rad))
            if 0 <= ax < W and 0 <= ay < H:
                draw.point((ax, ay), fill=1)
        # Horizont
        for x in range(12, 116):
            draw.point((x, 40), fill=1)

        # Sonne Position
        now = datetime.now(TZ)
        try:
            sh, sm = int(sunrise[:2]), int(sunrise[3:5])
            eh, em = int(sunset[:2]), int(sunset[3:5])
            start_min = sh * 60 + sm
            end_min = eh * 60 + em
            now_min = now.hour * 60 + now.minute
            if end_min > start_min:
                pct = max(0, min(1, (now_min - start_min) / (end_min - start_min)))
            else:
                pct = 0.5
        except (ValueError, IndexError):
            pct = 0.5
        sun_a = math.radians(180 + pct * 180)
        sx = round(64 + 48 * math.cos(sun_a))
        sy = round(40 + 22 * math.sin(sun_a))
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if dx * dx + dy * dy <= 5:
                    draw.point((sx + dx, sy + dy), fill=1)

        draw_icon(draw, "sun", 2, 48, 8)
        draw.text((12, 50), sunrise, fill=1, font=F_SM)
        draw_icon(draw, "moon", 98, 48, 8)
        draw.text((108, 50), sunset, fill=1, font=F_SM)
        # Tageslicht berechnen
        try:
            dl = (eh * 60 + em) - (sh * 60 + sm)
            draw.text((42, 50), f"{dl // 60}h{dl % 60:02d}m", fill=1, font=F_SM)
        except Exception:
            pass

    def _render_w_rain(self, draw):
        """W7: Regen-Balken 12h."""
        draw.text((2, 0), "REGEN 12h", fill=1, font=F_SM)
        hours = self._weather_hourly[:12]
        if not hours:
            draw.text((2, 28), "Keine Daten", fill=1, font=F_MD)
            return
        max_h = 38
        for i, h in enumerate(hours):
            rain = h.get("rain_chance", h.get("precipitation_probability", 0))
            try:
                rain = float(rain)
            except (ValueError, TypeError):
                rain = 0
            bh = max(1, round(rain / 100 * max_h))
            x = 4 + i * 10
            for dy in range(bh):
                for dx in range(8):
                    draw.point((x + dx, 12 + max_h - bh + dy), fill=1)

        # Stundenangaben
        for i in range(0, 12, 3):
            h = self._weather_hourly[i] if i < len(self._weather_hourly) else {}
            t_str = str(h.get("time", ""))[-5:-3] or str(i)
            draw.text((4 + i * 10, 54), t_str[:2], fill=1, font=F_SM)

    def _render_w_alert(self, draw):
        """W8: Wetterwarnung."""
        if not self._weather_alerts:
            draw.text((2, 24), "Keine Warnungen", fill=1, font=F_MD)
            return
        a = self._weather_alerts[0]
        draw_icon(draw, "alert", 2, 2, 8)
        draw.text((14, 2), "WARNUNG", fill=1, font=F_LG)
        sev = a.get("severity", "")
        draw.text((2, 22), f"Stufe: {sev}"[:21], fill=1, font=F_SM)
        title = a.get("title", a.get("event", ""))
        draw.text((2, 32), title[:21], fill=1, font=F_SM)
        desc = a.get("description", "")
        # 2 Zeilen Beschreibung
        draw.text((2, 42), desc[:21], fill=1, font=F_SM)
        draw.text((2, 52), desc[21:42], fill=1, font=F_SM)

    def _render_w_aqi(self, draw):
        """W9: Luftqualität."""
        draw.text((2, 0), "LUFTQUALITAET", fill=1, font=F_SM)
        aqi_data = self._weather_aqi or {}
        aqi = aqi_data.get("aqi", aqi_data.get("index", "--"))
        label = aqi_data.get("label", "")
        if not label and isinstance(aqi, (int, float)):
            if aqi <= 50:
                label = "Gut"
            elif aqi <= 100:
                label = "Maessig"
            else:
                label = "Schlecht"

        draw.text((2, 14), "AQI", fill=1, font=F_MD)
        draw.text((30, 10), str(aqi), fill=1, font=F_XL)
        draw.text((90, 18), label[:6], fill=1, font=F_SM)

        # Fortschrittsbalken
        try:
            pct = min(100, max(0, float(aqi) / 3))
        except (ValueError, TypeError):
            pct = 0
        bar_w = 120
        draw.rectangle([2, 38, 2 + bar_w, 44], outline=1)
        fill_w = int(bar_w * pct / 100)
        if fill_w > 0:
            draw.rectangle([2, 38, 2 + fill_w, 44], fill=1)

        pm25 = aqi_data.get("pm25", aqi_data.get("pm2_5", ""))
        pm10 = aqi_data.get("pm10", "")
        draw.text((2, 50), f"PM2.5:{pm25}", fill=1, font=F_SM)
        draw.text((64, 50), f"PM10:{pm10}", fill=1, font=F_SM)

    # ═══════════════════════════════════════════════════════
    #  CUSTOM TEXT
    # ═══════════════════════════════════════════════════════
    def _render_custom_text(self, draw, screen):
        lines = screen.get("lines", ["", "", "", ""])
        font_scale = screen.get("font_scale", 1)  # 1=klein, 2=mittel, 3=gross
        align = screen.get("align", "left")  # left, center, right
        font = F_SM if font_scale == 1 else (F_MD if font_scale == 2 else F_LG)
        line_h = 10 if font_scale == 1 else (14 if font_scale == 2 else 22)
        max_lines = max(1, H // line_h)

        for i, line in enumerate(lines[:max_lines]):
            if not line:
                continue
            y = i * line_h
            if align == "center":
                try:
                    tw = draw.textlength(line, font=font)
                except Exception:
                    tw = len(line) * 6
                x = max(0, (W - int(tw)) // 2)
            elif align == "right":
                try:
                    tw = draw.textlength(line, font=font)
                except Exception:
                    tw = len(line) * 6
                x = max(0, W - int(tw) - 2)
            else:
                x = 2
            draw.text((x, y), line, fill=1, font=font)

    # ═══════════════════════════════════════════════════════
    #  PIXEL ART
    # ═══════════════════════════════════════════════════════
    def _render_pixel_art(self, draw, screen):
        """Rendert ein 128×64 Pixel-Bitmap aus gespeicherten Daten."""
        art_id = screen.get("art_id", "")
        path = PIXEL_DIR / f"{art_id}.json"
        if not path.exists():
            draw.text((2, 28), "Kein Bild", fill=1, font=F_MD)
            return
        try:
            data = json.loads(path.read_text())
            pixels = data.get("pixels", [])
            for p in pixels:
                x, y = p.get("x", 0), p.get("y", 0)
                if 0 <= x < W and 0 <= y < H:
                    draw.point((x, y), fill=1)
        except Exception as e:
            logger.error(f"Pixel Art laden: {e}")
            draw.text((2, 28), "Fehler", fill=1, font=F_MD)

    # ═══════════════════════════════════════════════════════
    #  MARQUEE (LAUFSCHRIFT)
    # ═══════════════════════════════════════════════════════
    def _render_marquee(self, draw, screen):
        text = screen.get("text", "PironMan Deluxe")
        speed = screen.get("speed", 3)  # 1-10
        font_scale = screen.get("font_scale", 2)  # 1=klein, 2=gross
        font = F_MD if font_scale == 1 else F_LG
        y_pos = screen.get("y", 20)

        try:
            text_w = int(draw.textlength(text, font=font))
        except Exception:
            text_w = len(text) * (7 if font_scale == 1 else 12)

        total_w = text_w + W
        offset = int(time.time() * speed * 3) % total_w
        x = W - offset
        draw.text((x, y_pos), text, fill=1, font=font)

    # ═══════════════════════════════════════════════════════
    #  SCREEN MANAGEMENT
    # ═══════════════════════════════════════════════════════
    def set_screen(self, index):
        if 0 <= index < len(self.screens):
            self.current_screen = index
            self._rotation_reset = True  # Timer zurücksetzen
            # Sofort rendern für Preview-Update
            try:
                stats = get_system_stats()
                self.render(stats)
            except Exception:
                pass
            self._save_settings()

    def add_screen(self, screen_data: dict) -> int:
        self.screens.append(screen_data)
        self._save_settings()
        return len(self.screens) - 1

    def update_screen(self, index: int, screen_data: dict):
        if 0 <= index < len(self.screens):
            self.screens[index] = screen_data
            self._save_settings()
            # Sofort rendern für Preview-Update
            try:
                stats = get_system_stats()
                self.render(stats)
            except Exception:
                pass

    def remove_screen(self, index: int):
        if len(self.screens) > 1 and 0 <= index < len(self.screens):
            self.screens.pop(index)
            if self.current_screen >= len(self.screens):
                self.current_screen = 0
            self._save_settings()

    def reorder_screens(self, order: list[int]):
        """Screens umsortieren nach Index-Liste."""
        try:
            new = [self.screens[i] for i in order if 0 <= i < len(self.screens)]
            if new:
                self.screens = new
                self.current_screen = 0
                self._save_settings()
        except (IndexError, TypeError):
            pass

    # ═══════════════════════════════════════════════════════
    #  PIXEL ART MANAGEMENT
    # ═══════════════════════════════════════════════════════
    def save_pixel_art(self, art_id: str, pixels: list[dict], name: str = ""):
        """Speichert ein Pixel-Art Bild."""
        data = {"id": art_id, "name": name, "pixels": pixels,
                "created": datetime.now(TZ).isoformat()}
        (PIXEL_DIR / f"{art_id}.json").write_text(json.dumps(data))
        return data

    def list_pixel_arts(self) -> list[dict]:
        result = []
        for f in sorted(PIXEL_DIR.glob("*.json")):
            try:
                d = json.loads(f.read_text())
                result.append({"id": d.get("id", f.stem), "name": d.get("name", f.stem),
                               "pixel_count": len(d.get("pixels", []))})
            except Exception:
                pass
        return result

    def delete_pixel_art(self, art_id: str):
        path = PIXEL_DIR / f"{art_id}.json"
        if path.exists():
            path.unlink()

    def get_pixel_art(self, art_id: str) -> Optional[dict]:
        path = PIXEL_DIR / f"{art_id}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None

    # ═══════════════════════════════════════════════════════
    #  SETTINGS
    # ═══════════════════════════════════════════════════════
    def set_mode(self, mode):
        if mode in ("auto", "manual", "off"):
            self.mode = mode
            if mode == "off":
                hw_client.oled_clear()
            self._save_settings()

    def set_brightness(self, value):
        self.brightness = max(0, min(255, value))
        hw_client.oled_brightness(self.brightness)
        self._save_settings()

    def set_rotation_interval(self, seconds):
        self.rotation_interval = max(3, min(120, seconds))
        self._save_settings()

    def set_clock_settings(self, settings: dict):
        for k in ("blink", "seconds", "tenths", "date", "weekday", "format_24h"):
            if k in settings:
                self.clock_settings[k] = bool(settings[k])
        self._save_settings()

    # ═══════════════════════════════════════════════════════
    #  STATE / PERSISTENCE
    # ═══════════════════════════════════════════════════════
    def get_state(self) -> dict:
        return {
            "available": self.enabled or PIL_OK,
            "hardware": self.enabled,
            "mode": self.mode,
            "brightness": self.brightness,
            "rotation_interval": self.rotation_interval,
            "current_screen": self.current_screen,
            "screens": self.screens,
            "clock_settings": self.clock_settings,
            "pixel_arts": self.list_pixel_arts(),
            "preview": self._last_preview,
            "resolution": f"{W}x{H}",
            "has_weather": self._weather_data is not None,
            "weather_location": self._weather_location,
        }

    def get_ws_state(self) -> dict:
        """Leichte Version für WebSocket Push (ohne Pixel Art Liste)."""
        return {
            "available": self.enabled or PIL_OK,
            "hardware": self.enabled,
            "mode": self.mode,
            "brightness": self.brightness,
            "rotation_interval": self.rotation_interval,
            "current_screen": self.current_screen,
            "screens": self.screens,
            "clock_settings": self.clock_settings,
            "preview": self._last_preview,
            "resolution": f"{W}x{H}",
            "has_weather": self._weather_data is not None,
            "weather_location": self._weather_location,
        }

    def _save_settings(self):
        try:
            data = {
                "mode": self.mode, "brightness": self.brightness,
                "rotation_interval": self.rotation_interval,
                "screens": self.screens, "current_screen": self.current_screen,
                "clock_settings": self.clock_settings,
            }
            (DATA_DIR / "oled_settings.json").write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"OLED Settings speichern: {e}")

    def _load_settings(self):
        path = DATA_DIR / "oled_settings.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.mode = data.get("mode", self.mode)
            self.brightness = data.get("brightness", self.brightness)
            self.rotation_interval = data.get("rotation_interval", self.rotation_interval)
            if "screens" in data and data["screens"]:
                self.screens = data["screens"]
            self.current_screen = data.get("current_screen", 0)
            if "clock_settings" in data:
                self.clock_settings.update(data["clock_settings"])
        except Exception as e:
            logger.error(f"OLED Settings laden: {e}")

    # ═══════════════════════════════════════════════════════
    #  RENDER LOOP + WEATHER FETCH
    # ═══════════════════════════════════════════════════════
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._render_loop, daemon=True)
        self._thread.start()
        logger.info("OLED Engine gestartet")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        hw_client.oled_clear()

    def _render_loop(self):
        last_rotate = time.time()
        while self._running:
            try:
                # Rotation-Timer Reset (z.B. nach manuellem Screen-Wechsel)
                if self._rotation_reset:
                    last_rotate = time.time()
                    self._rotation_reset = False

                stats = get_system_stats()
                if time.time() - self._weather_fetch_time > 300:
                    self._fetch_weather()
                self.render(stats)
                if self.mode == "auto" and len(self.screens) > 1:
                    if time.time() - last_rotate >= self.rotation_interval:
                        self.current_screen = (self.current_screen + 1) % len(self.screens)
                        last_rotate = time.time()
            except Exception as e:
                logger.error(f"OLED Render-Loop: {e}")
            time.sleep(1)

    def _fetch_weather(self):
        self._weather_fetch_time = time.time()
        try:
            import httpx
            # WeatherCache läuft auf dem Host, nicht im Container!
            from config import HW_PROXY_URL
            weather_base = HW_PROXY_URL.rsplit(":", 1)[0] + ":8060"  # host.docker.internal:8060
            r = httpx.get(f"{weather_base}/api/v1/locations", timeout=5)
            if r.status_code != 200:
                return
            locs = r.json().get("locations", [])
            if not locs:
                return
            loc = locs[0]
            loc_id = loc.get("id", "")
            self._weather_location = loc.get("name", loc.get("city", ""))
            if not loc_id:
                return
            r2 = httpx.get(f"{weather_base}/api/v1/weather/complete/{loc_id}", timeout=5)
            if r2.status_code != 200:
                return
            data = r2.json()
            current = data.get("current", {})
            self._weather_data = current.get("data", current)
            hourly = data.get("hourly", {})
            self._weather_hourly = hourly.get("hours", hourly.get("data", []))
            daily = data.get("daily", {})
            self._weather_daily = daily.get("days", daily.get("data", []))
            alerts = data.get("alerts", {})
            self._weather_alerts = alerts.get("alerts", alerts.get("data", []))
            aqi = data.get("air_quality", {})
            self._weather_aqi = aqi.get("data", aqi)
            logger.info(f"Wetter geladen: {self._weather_location} {self._weather_data.get('temperature', '?')}°C")
        except Exception as e:
            logger.debug(f"Wetter-Fetch: {e}")
