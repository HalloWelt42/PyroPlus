"""
PyroPlus — OLED Display Engine (Orchestrator)
Schlanke Steuerung: Render-Loop, Screen-Management, Persistenz.
Rendering delegiert an renderer.py, widgets.py, weather.py.
"""

import threading
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import hw_client
from config import OLED_DEFAULT_BRIGHTNESS, OLED_ROTATION_INTERVAL, DATA_DIR
from stats import get_system_stats
from oled.renderer import W, H, create_buffer, buf_to_pil, buf_to_png_base64, draw_text
from oled.widgets import render_widget, update_history
from oled.weather import WeatherProvider, render_weather_compact, render_weather_hourly, render_weather_daily

logger = logging.getLogger("oled")

TZ = ZoneInfo("Europe/Berlin")
PIXEL_DIR = DATA_DIR / "pixel_screens"
PIXEL_DIR.mkdir(parents=True, exist_ok=True)

try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False
    logger.warning("Pillow nicht installiert — OLED deaktiviert")


class OLEDEngine:
    def __init__(self):
        self.enabled = False
        self.brightness = OLED_DEFAULT_BRIGHTNESS
        self.rotation_interval = OLED_ROTATION_INTERVAL
        self.mode = "auto"
        self.current_screen = 0
        self._last_preview: Optional[str] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._rotation_reset = False

        # Wetter
        self.weather = WeatherProvider()

        # Screen-Liste
        self.screens: list[dict] = []

        # Clock Settings
        self.clock_settings = {
            "blink": True, "seconds": False, "tenths": False,
            "date": True, "weekday": True, "format_24h": True,
        }

        # Hardware-Check
        self.enabled = hw_client.oled_available()
        hw_client.oled_brightness(self.brightness)
        logger.info(f"OLED verfuegbar: {self.enabled}")

        self._load_settings()
        if not self.screens:
            self._create_defaults()

    # ═══ DEFAULTS ═══
    def _create_defaults(self):
        self.screens = [
            {"type": "system", "name": "Uhr + System", "widgets": [
                {"source": "zeit.uhr_blink", "display": "zahl_xl", "x": 0, "y": 0, "opts": {"scaleX": 3, "scaleY": 3, "prefix": "", "suffix": ""}},
                {"source": "zeit.tag_datum", "display": "zahl", "x": 0, "y": 24, "opts": {"scaleX": 1, "scaleY": 1, "prefix": "", "suffix": ""}},
                {"source": "cpu.temp", "display": "zahl", "x": 0, "y": 36, "opts": {"scaleX": 1, "scaleY": 1, "prefix": "CPU ", "suffix": "C"}},
                {"source": "ram.percent", "display": "zahl", "x": 0, "y": 46, "opts": {"scaleX": 1, "scaleY": 1, "prefix": "RAM ", "suffix": "%"}},
                {"source": "net.ip", "display": "zahl", "x": 0, "y": 56, "opts": {"scaleX": 1, "scaleY": 1, "prefix": "", "suffix": ""}},
            ]},
        ]
        self._save_settings()

    # ═══ MAIN RENDER ═══
    def render(self, stats: dict) -> Optional[str]:
        if not PIL_OK:
            return None
        with self._lock:
            buf = create_buffer()

            if self.mode != "off" and self.screens:
                idx = min(self.current_screen, len(self.screens) - 1)
                screen = self.screens[idx]
                stype = screen.get("type", "system")

                if stype == "system":
                    self._render_system(buf, screen, stats)
                elif stype == "clock":
                    self._render_clock(buf)
                elif stype == "weather_compact":
                    render_weather_compact(buf, self.weather)
                elif stype == "weather_hourly":
                    render_weather_hourly(buf, self.weather)
                elif stype == "weather_daily":
                    render_weather_daily(buf, self.weather)
                elif stype == "pixel_art":
                    self._render_pixel_art(buf, screen)
                elif stype == "marquee":
                    self._render_marquee(buf, screen)

            # An Hardware senden
            if self.mode != "off":
                img = buf_to_pil(buf)
                import base64, io
                out = io.BytesIO()
                img.save(out, format="PNG")
                hw_client.oled_display(base64.b64encode(out.getvalue()).decode())
            else:
                hw_client.oled_clear()

            # Native 128x64 Preview — keine Skalierung!
            self._last_preview = buf_to_png_base64(buf)
            return self._last_preview

    # ═══ SYSTEM WIDGETS ═══
    def _render_system(self, buf: bytearray, screen: dict, stats: dict):
        """Alle Widgets eines System-Screens rendern."""
        # Weather-Daten mit Location anreichern
        w = dict(self.weather.data or {})
        w["location"] = self.weather.location
        for widget in screen.get("widgets", []):
            render_widget(buf, widget, stats, weather=w)

    # ═══ CLOCK ═══
    def _render_clock(self, buf: bytearray):
        now = datetime.now(TZ)
        cs = self.clock_settings
        colon = ":" if not cs.get("blink") or now.second % 2 == 0 else " "
        time_str = f"{now.strftime('%H')}{colon}{now.strftime('%M')}"
        draw_text(buf, time_str, 2, 2, 3)

        if cs.get("seconds"):
            sec = f":{now.strftime('%S')}"
            draw_text(buf, sec, 98, 8, 1)

        y_pos = 34
        if cs.get("weekday"):
            days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
            draw_text(buf, days[now.weekday()], 2, y_pos, 1)
            y_pos += 10
        if cs.get("date"):
            draw_text(buf, now.strftime("%d.%m.%Y"), 2, y_pos, 1)

    # ═══ PIXEL ART ═══
    def _render_pixel_art(self, buf: bytearray, screen: dict):
        art_id = screen.get("art_id", "")
        path = PIXEL_DIR / f"{art_id}.json"
        if not path.exists():
            draw_text(buf, "Kein Bild", 2, 28, 1)
            return
        try:
            data = json.loads(path.read_text())
            pixels = data.get("pixels", [])
            for p in pixels:
                x, y = p.get("x", 0), p.get("y", 0)
                if 0 <= x < W and 0 <= y < H:
                    buf[y * W + x] = 1
        except Exception as e:
            logger.error(f"Pixel Art laden: {e}")
            draw_text(buf, "Fehler", 2, 28, 1)

    # ═══ MARQUEE ═══
    def _render_marquee(self, buf: bytearray, screen: dict):
        from oled.renderer import draw_marquee
        text = screen.get("text", "PyroPlus")
        scale = screen.get("font_scale", 2)
        y_pos = screen.get("y", 20)
        offset = int(time.time() * 30) % (len(text) * 6 * scale + W)
        draw_marquee(buf, text, y_pos, offset, scale)

    # ═══ SCREEN MANAGEMENT ═══
    def set_screen(self, index: int):
        if 0 <= index < len(self.screens):
            self.current_screen = index
            self._rotation_reset = True
            try:
                self.render(get_system_stats())
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
            try:
                self.render(get_system_stats())
            except Exception:
                pass

    def remove_screen(self, index: int):
        if len(self.screens) > 1 and 0 <= index < len(self.screens):
            self.screens.pop(index)
            if self.current_screen >= len(self.screens):
                self.current_screen = 0
            self._save_settings()

    def reorder_screens(self, order: list[int]):
        try:
            new = [self.screens[i] for i in order if 0 <= i < len(self.screens)]
            if new:
                self.screens = new
                self.current_screen = 0
                self._save_settings()
        except (IndexError, TypeError):
            pass

    # ═══ PIXEL ART MANAGEMENT ═══
    def save_pixel_art(self, art_id: str, pixels: list[dict], name: str = ""):
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

    # ═══ SETTINGS ═══
    def set_mode(self, mode: str):
        if mode in ("auto", "manual", "off"):
            self.mode = mode
            if mode == "off":
                hw_client.oled_clear()
            self._save_settings()

    def set_brightness(self, value: int):
        self.brightness = max(0, min(255, value))
        hw_client.oled_brightness(self.brightness)
        self._save_settings()

    def set_rotation_interval(self, seconds: int):
        self.rotation_interval = max(3, min(120, seconds))
        self._save_settings()

    def set_clock_settings(self, settings: dict):
        for k in ("blink", "seconds", "tenths", "date", "weekday", "format_24h"):
            if k in settings:
                self.clock_settings[k] = bool(settings[k])
        self._save_settings()

    # ═══ STATE ═══
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
            "has_weather": self.weather.data is not None,
            "weather_location": self.weather.location,
        }

    def get_ws_state(self) -> dict:
        """Leichte Version fuer WebSocket Push."""
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
            "has_weather": self.weather.data is not None,
            "weather_location": self.weather.location,
        }

    # ═══ PERSISTENCE ═══
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

    # ═══ RENDER LOOP ═══
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
        last_stats = time.time()
        cached_stats = {}
        render_interval = 0.2  # 5 fps
        stats_interval = 1.0   # Stats nur 1x/s holen

        while self._running:
            try:
                if self._rotation_reset:
                    last_rotate = time.time()
                    self._rotation_reset = False

                now = time.time()

                # Stats + History nur 1x/s aktualisieren
                if now - last_stats >= stats_interval:
                    cached_stats = get_system_stats()
                    update_history(cached_stats)
                    last_stats = now

                    # Wetter alle 5 min
                    if self.weather.needs_update():
                        self.weather.fetch()

                # Rendering 5x/s mit gecachten Stats
                self.render(cached_stats)

                # Rotation
                if self.mode == "auto" and len(self.screens) > 1:
                    if now - last_rotate >= self.rotation_interval:
                        self.current_screen = (self.current_screen + 1) % len(self.screens)
                        last_rotate = now
            except Exception as e:
                logger.error(f"OLED Render-Loop: {e}")
            time.sleep(render_interval)
