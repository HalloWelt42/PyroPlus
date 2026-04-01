"""
PironMan Deluxe v2.5.4 — LED Config Manager
© HalloWelt42 - Nur für private Nutzung

Dünner Config-Wrapper. Animationen laufen im HW-Proxy (nativ).
Backend sendet nur Konfigurationsänderungen per HTTP.
Kein Animation-Thread, kein Frame-Loop, kein HTTP-Spam.
"""

import json
import logging
import threading
import time
from typing import Optional

import hw_client
from config import LED_COUNT, LED_DEFAULT_BRIGHTNESS, LED_DEFAULT_EFFECT, LED_DEFAULT_COLOR, DATA_DIR

logger = logging.getLogger("leds")


class LEDEngine:
    """Config Manager — delegiert Animationen an den HW-Proxy."""

    EFFECTS = {
        "static": {"name": "Static", "category": "basis", "icon": "⬤"},
        "breathing": {"name": "Breathing", "category": "basis", "icon": "🫁"},
        "rainbow": {"name": "Rainbow", "category": "basis", "icon": "🌈"},
        "gradient": {"name": "Gradient", "category": "basis", "icon": "🔀"},
        "candle": {"name": "Candle", "category": "basis", "icon": "🕯️"},
        "lava": {"name": "Lava Lamp", "category": "advanced", "icon": "🫧"},
        "aurora": {"name": "Aurora", "category": "advanced", "icon": "🌌"},
        "fire": {"name": "Fire", "category": "advanced", "icon": "🔥"},
        "ocean": {"name": "Ocean", "category": "advanced", "icon": "🌊"},
        "pulse": {"name": "Pulse", "category": "advanced", "icon": "💫"},
        "sound_reactive": {"name": "Sound Reactive", "category": "audio", "icon": "📊"},
        "freq_bands": {"name": "Frequency Bands", "category": "audio", "icon": "📶"},
        "beat_detect": {"name": "Beat Detection", "category": "audio", "icon": "🥁"},
        "vu_meter": {"name": "VU Meter", "category": "audio", "icon": "📏"},
        "strobe": {"name": "Strobe", "category": "party", "icon": "⚡"},
        "police": {"name": "Police", "category": "party", "icon": "🚨"},
        "disco": {"name": "Disco", "category": "party", "icon": "🪩"},
        "chase": {"name": "Chase", "category": "party", "icon": "🏃"},
        "sparkle": {"name": "Sparkle", "category": "party", "icon": "✨"},
        "firework": {"name": "Firework", "category": "party", "icon": "🎆"},
        "sunset": {"name": "Sunset", "category": "mood", "icon": "🌅"},
        "forest": {"name": "Forest", "category": "mood", "icon": "🌲"},
        "neon": {"name": "Neon", "category": "mood", "icon": "💜"},
        "warm_white": {"name": "Warm White", "category": "mood", "icon": "💡"},
        "night_light": {"name": "Night Light", "category": "mood", "icon": "🌙"},
        "temp_reactive": {"name": "Temp Reactive", "category": "mood", "icon": "🌡️"},
        "load_reactive": {"name": "Load Reactive", "category": "mood", "icon": "📊"},
    }

    def __init__(self):
        self.available = hw_client.leds_available()
        self.effect: str = LED_DEFAULT_EFFECT
        self.color: dict = dict(LED_DEFAULT_COLOR)
        self.color2: dict = {"r": 255, "g": 0, "b": 0}
        self.brightness: int = LED_DEFAULT_BRIGHTNESS
        self.speed: float = 50.0
        self.individual_mode: bool = False
        self.individual_colors: list[dict] = [dict(LED_DEFAULT_COLOR) for _ in range(LED_COUNT)]
        self.led_states: list[dict] = [{"r": 0, "g": 0, "b": 0} for _ in range(LED_COUNT)]

        # System-Daten für reaktive Effekte
        self.cpu_temp: float = 40.0
        self.cpu_load: float = 10.0

        # System-Data Push Thread
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._load_settings()

        # Initial-Config an Proxy senden
        self._push_full_config()
        logger.info(f"LED Config Manager: {self.effect}, br={self.brightness}")

    # ═══════════════════════════════════════════════════════
    #  CONFIG → HW-PROXY
    # ═══════════════════════════════════════════════════════

    def _push_full_config(self):
        """Gesamte Konfiguration an HW-Proxy senden."""
        hw_client.leds_config(
            effect=self.effect,
            color=self.color,
            color2=self.color2,
            brightness=self.brightness,
            speed=self.speed,
            individual_mode=self.individual_mode,
            individual_colors=self.individual_colors,
        )

    def set_effect(self, name: str):
        if name == "off" or name in self.EFFECTS:
            self.effect = name
            hw_client.leds_config(effect=name)
            self._save_settings()

    def set_color(self, r: int, g: int, b: int):
        self.color = {"r": r, "g": g, "b": b}
        hw_client.leds_config(color=self.color)
        self._save_settings()

    def set_color2(self, r: int, g: int, b: int):
        self.color2 = {"r": r, "g": g, "b": b}
        hw_client.leds_config(color2=self.color2)
        self._save_settings()

    def set_brightness(self, value: int):
        self.brightness = max(0, min(1000, value))
        hw_client.leds_config(brightness=self.brightness)
        self._save_settings()

    def set_speed(self, value: float):
        self.speed = max(1.0, min(1000.0, value))
        hw_client.leds_config(speed=self.speed)
        self._save_settings()

    def set_individual_color(self, index: int, r: int, g: int, b: int):
        if 0 <= index < LED_COUNT:
            self.individual_colors[index] = {"r": r, "g": g, "b": b}
            hw_client.leds_config(individual_colors=self.individual_colors)
            self._save_settings()

    # ═══════════════════════════════════════════════════════
    #  SYSTEM DATA PUSH (für reaktive Effekte)
    # ═══════════════════════════════════════════════════════

    def start(self):
        """Startet den System-Data Push Thread (alle 3s)."""
        self._running = True
        self._thread = threading.Thread(target=self._system_data_loop, daemon=True)
        self._thread.start()
        logger.info("System-Data Push gestartet (3s Intervall)")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        hw_client.leds_config(effect="off")

    def _system_data_loop(self):
        """Pusht CPU-Temp/Load alle 3s für reaktive Effekte."""
        while self._running:
            try:
                hw_client.leds_push_system_data(self.cpu_temp, self.cpu_load)
            except Exception:
                pass
            time.sleep(3)

    def update_system_data(self, cpu_temp: float, cpu_load: float):
        """Wird vom Stats-Collector aufgerufen."""
        self.cpu_temp = cpu_temp
        self.cpu_load = cpu_load

    # ═══════════════════════════════════════════════════════
    #  STATE (aus HW-Proxy lesen)
    # ═══════════════════════════════════════════════════════

    def refresh_led_states(self):
        """LED-Farben vom HW-Proxy holen (für WebSocket Push)."""
        try:
            states = hw_client.leds_get_states_only()
            if states:
                self.led_states = states
        except Exception:
            pass

    def get_state(self) -> dict:
        return {
            "available": self.available,
            "effect": self.effect,
            "color": self.color,
            "color2": self.color2,
            "brightness": self.brightness,
            "speed": self.speed,
            "individual_mode": self.individual_mode,
            "individual_colors": self.individual_colors,
            "led_states": self.led_states,
            "effects_catalog": self.EFFECTS,
            "effects_by_category": self._effects_by_category(),
        }

    def get_ws_state(self) -> dict:
        """Leichte Version für WebSocket Push."""
        return {
            "available": self.available,
            "effect": self.effect,
            "color": self.color,
            "color2": self.color2,
            "brightness": self.brightness,
            "speed": self.speed,
            "individual_mode": self.individual_mode,
            "individual_colors": self.individual_colors,
            "led_states": self.led_states,
            "effects_by_category": self._effects_by_category(),
        }

    def _effects_by_category(self) -> dict:
        cats = {}
        for key, meta in self.EFFECTS.items():
            cat = meta["category"]
            if cat not in cats:
                cats[cat] = []
            cats[cat].append(key)
        return cats

    def get_effects_list(self) -> dict:
        categories = {}
        for key, meta in self.EFFECTS.items():
            cat = meta["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({"id": key, **meta})
        return categories

    # ═══════════════════════════════════════════════════════
    #  PERSISTENCE
    # ═══════════════════════════════════════════════════════

    def _save_settings(self):
        try:
            data = {
                "effect": self.effect, "color": self.color, "color2": self.color2,
                "brightness": self.brightness, "speed": self.speed,
                "individual_mode": self.individual_mode,
                "individual_colors": self.individual_colors,
            }
            (DATA_DIR / "led_settings.json").write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"LED Settings speichern: {e}")

    def _load_settings(self):
        path = DATA_DIR / "led_settings.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.effect = data.get("effect", self.effect)
            self.color = data.get("color", self.color)
            self.color2 = data.get("color2", self.color2)
            raw_br = data.get("brightness", self.brightness)
            self.brightness = raw_br if raw_br > 255 else int(raw_br / 255 * 1000)
            self.speed = data.get("speed", self.speed)
            self.individual_mode = data.get("individual_mode", False)
            if "individual_colors" in data:
                self.individual_colors = data["individual_colors"]
        except Exception as e:
            logger.error(f"LED Settings laden: {e}")
