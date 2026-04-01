"""
PyroPlus v3.0.0 — LED Effekt-Engine (nativ)
© HalloWelt42 - Nur für private Nutzung

Läuft direkt auf dem Pi im HW-Proxy. Kein HTTP pro Frame.
Backend sendet nur Konfigurationsänderungen.
"""

import math
import time
import random
import colorsys
import threading
import json
import logging
from pathlib import Path

logger = logging.getLogger("led-engine")

LED_COUNT = 4
DATA_DIR = Path("/opt/pyroplus-hw/data")


class LEDEffectEngine:
    """Autonome LED-Engine mit direktem Strip-Zugriff."""

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

    def __init__(self, strip):
        """strip = neopixel_spi.NeoPixel_SPI Instanz oder None."""
        self._strip = strip
        self.available = strip is not None

        # ─── Konfiguration (wird vom Backend gesetzt) ───
        self.effect: str = "off"
        self.color: dict = {"r": 0, "g": 100, "b": 255}
        self.color2: dict = {"r": 255, "g": 0, "b": 0}
        self.brightness: int = 500   # 1-1000 Skala
        self.speed: float = 50.0
        self.individual_mode: bool = False
        self.individual_colors: list[dict] = [{"r": 0, "g": 100, "b": 255}] * LED_COUNT

        # ─── System-Daten (vom Backend gepusht) ───
        self.cpu_temp: float = 40.0
        self.cpu_load: float = 10.0

        # ─── Interner State ───
        self.led_states: list[dict] = [{"r": 0, "g": 0, "b": 0}] * LED_COUNT
        self._running = False
        self._thread = None
        self._config_changed = threading.Event()
        self._lock = threading.Lock()

        # Settings laden
        self._load_settings()
        # Brightness initial setzen
        self._apply_brightness()

    # ═══════════════════════════════════════════════════════
    #  KONFIGURATION (vom Backend aufgerufen)
    # ═══════════════════════════════════════════════════════

    def set_config(self, config: dict):
        """Komplette Konfiguration vom Backend übernehmen."""
        changed = False
        with self._lock:
            for key in ("effect", "color", "color2", "brightness", "speed",
                        "individual_mode", "individual_colors"):
                if key in config:
                    old = getattr(self, key)
                    new = config[key]
                    if old != new:
                        setattr(self, key, new)
                        changed = True

            if "brightness" in config:
                self._apply_brightness()

        if changed:
            self._config_changed.set()
            self._save_settings()

        # Sofort off senden
        if config.get("effect") == "off":
            self._set_all(0, 0, 0)
            self._show()

    def set_system_data(self, cpu_temp: float, cpu_load: float):
        """System-Daten für reaktive Effekte (vom Backend alle 2s gepusht)."""
        self.cpu_temp = cpu_temp
        self.cpu_load = cpu_load

    def _apply_brightness(self):
        """Brightness 1-1000 → 0.0-1.0 auf Strip."""
        if self._strip:
            hw_val = (max(0, min(1000, self.brightness)) / 1000.0) ** 0.6
            try:
                self._strip.brightness = hw_val
                self._strip.show()
            except Exception as e:
                logger.error(f"Brightness setzen: {e}")

    # ═══════════════════════════════════════════════════════
    #  HARDWARE OUTPUT (direkt, kein HTTP!)
    # ═══════════════════════════════════════════════════════

    def _set_led(self, index: int, r: int, g: int, b: int):
        r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
        if 0 <= index < LED_COUNT:
            self.led_states[index] = {"r": r, "g": g, "b": b}

    def _set_all(self, r: int, g: int, b: int):
        for i in range(LED_COUNT):
            self._set_led(i, r, g, b)

    def _show(self):
        """Direkt auf den SPI-Strip schreiben — kein HTTP!"""
        if not self._strip:
            return
        try:
            for i, c in enumerate(self.led_states):
                if i < LED_COUNT:
                    self._strip[i] = (c["r"], c["g"], c["b"])
            self._strip.show()
        except Exception as e:
            logger.error(f"Strip write: {e}")

    # ═══════════════════════════════════════════════════════
    #  EFFEKT-BERECHNUNG
    # ═══════════════════════════════════════════════════════

    def _tick(self, step: int):
        c, c2 = self.color, self.color2
        spd = (self.speed / 100.0) ** 1.5

        if self.effect == "off":
            self._set_all(0, 0, 0)
        elif self.effect == "static":
            if self.individual_mode:
                for i, ic in enumerate(self.individual_colors):
                    if i < LED_COUNT:
                        self._set_led(i, ic["r"], ic["g"], ic["b"])
            else:
                self._set_all(c["r"], c["g"], c["b"])
        elif self.effect == "breathing":
            f = (math.sin(step * 0.04 * spd) + 1) / 2
            self._set_all(int(c["r"] * f), int(c["g"] * f), int(c["b"] * f))
        elif self.effect == "rainbow":
            for i in range(LED_COUNT):
                hue = ((step * 2 * spd) + (i * 90)) % 360
                r, g, b = self._hsv(hue, 1.0, 1.0)
                self._set_led(i, r, g, b)
        elif self.effect == "gradient":
            for i in range(LED_COUNT):
                t = i / max(1, LED_COUNT - 1)
                r = int(c["r"] + (c2["r"] - c["r"]) * t)
                g = int(c["g"] + (c2["g"] - c["g"]) * t)
                b = int(c["b"] + (c2["b"] - c["b"]) * t)
                phase = math.sin(step * 0.03 * spd) * 0.3 + 0.7
                self._set_led(i, int(r * phase), int(g * phase), int(b * phase))
        elif self.effect == "candle":
            for i in range(LED_COUNT):
                fl = 0.6 + random.random() * 0.4
                self._set_led(i, int(255 * fl), int(120 * fl), int(20 * fl * 0.5))
        elif self.effect == "lava":
            t = step * 0.01 * spd
            for i in range(LED_COUNT):
                hue = (math.sin(t + i * 1.2) * 30 + math.sin(t * 0.7 + i * 0.8) * 20) % 360
                r, g, b = self._hsv(abs(hue), 0.9, 0.5 + math.sin(t + i) * 0.3)
                self._set_led(i, r, g, b)
        elif self.effect == "aurora":
            t = step * 0.015 * spd
            pal = [(0, 255, 100), (0, 180, 255), (80, 0, 255), (0, 255, 180)]
            for i in range(LED_COUNT):
                idx = (math.sin(t + i * 0.8) + 1) / 2 * (len(pal) - 1)
                lo, hi = int(idx), min(int(idx) + 1, len(pal) - 1)
                frac = idx - lo
                r = int(pal[lo][0] + (pal[hi][0] - pal[lo][0]) * frac)
                g = int(pal[lo][1] + (pal[hi][1] - pal[lo][1]) * frac)
                b = int(pal[lo][2] + (pal[hi][2] - pal[lo][2]) * frac)
                bright = 0.4 + math.sin(t * 1.3 + i * 2) * 0.3
                self._set_led(i, int(r * bright), int(g * bright), int(b * bright))
        elif self.effect == "fire":
            for i in range(LED_COUNT):
                h = random.randint(120, 255)
                self._set_led(i, h, max(0, h - 100), max(0, h - 200))
        elif self.effect == "ocean":
            t = step * 0.02 * spd
            for i in range(LED_COUNT):
                w = math.sin(t + i * 1.5) * 0.5 + 0.5
                self._set_led(i, 0, int(80 * w), int(180 + 75 * w))
        elif self.effect == "pulse":
            t = step * 0.06 * spd
            pos = t % (LED_COUNT + 2)
            for i in range(LED_COUNT):
                bright = max(0.0, 1.0 - abs(i - pos) * 0.7)
                self._set_led(i, int(c["r"] * bright), int(c["g"] * bright), int(c["b"] * bright))
        elif self.effect == "strobe":
            on = (step % max(1, int(20 / spd))) < max(1, int(5 / spd))
            if on:
                self._set_all(c["r"], c["g"], c["b"])
            else:
                self._set_all(0, 0, 0)
        elif self.effect == "police":
            phase = (step // max(1, int(8 / spd))) % 4
            self._set_all(0, 0, 0)
            if phase == 0:
                self._set_led(0, 255, 0, 0)
                self._set_led(1, 255, 0, 0)
            elif phase == 2:
                self._set_led(2, 0, 0, 255)
                self._set_led(3, 0, 0, 255)
        elif self.effect == "disco":
            if step % max(1, int(6 / spd)) == 0:
                for i in range(LED_COUNT):
                    r, g, b = self._hsv(random.randint(0, 360), 1.0, 1.0)
                    self._set_led(i, r, g, b)
        elif self.effect == "chase":
            pos = (step // max(1, int(4 / spd))) % LED_COUNT
            for i in range(LED_COUNT):
                if i == pos:
                    self._set_led(i, c["r"], c["g"], c["b"])
                else:
                    self._set_led(i, 0, 0, 0)
        elif self.effect == "sparkle":
            for i in range(LED_COUNT):
                if random.random() < 0.15 * spd:
                    self._set_led(i, c["r"], c["g"], c["b"])
                else:
                    cur = self.led_states[i]
                    self._set_led(i, int(cur["r"] * 0.7), int(cur["g"] * 0.7), int(cur["b"] * 0.7))
        elif self.effect == "firework":
            cycle = max(1, int(60 / spd))
            phase = step % cycle
            if phase == 0:
                self._set_all(255, 255, 255)
            elif phase < cycle * 0.3:
                r, g, b = self._hsv(random.randint(0, 360), 1.0, 1.0)
                self._set_all(r, g, b)
            else:
                fade = max(0, 1.0 - (phase - cycle * 0.3) / (cycle * 0.7))
                cur = self.led_states[0]
                self._set_all(int(cur["r"] * fade), int(cur["g"] * fade), int(cur["b"] * fade))
        elif self.effect == "sunset":
            t = step * 0.008 * spd
            pal = [(255, 60, 0), (255, 120, 0), (255, 80, 50), (200, 40, 80)]
            for i in range(LED_COUNT):
                idx = (math.sin(t + i * 0.5) + 1) / 2 * (len(pal) - 1)
                lo, hi = int(idx), min(int(idx) + 1, len(pal) - 1)
                frac = idx - lo
                self._set_led(i,
                    int(pal[lo][0] + (pal[hi][0] - pal[lo][0]) * frac),
                    int(pal[lo][1] + (pal[hi][1] - pal[lo][1]) * frac),
                    int(pal[lo][2] + (pal[hi][2] - pal[lo][2]) * frac))
        elif self.effect == "forest":
            t = step * 0.01 * spd
            for i in range(LED_COUNT):
                g = int(80 + math.sin(t + i * 1.5) * 40)
                self._set_led(i, int(g * 0.1), g, int(g * 0.2))
        elif self.effect == "neon":
            t = step * 0.02 * spd
            nc = [(255, 0, 255), (0, 255, 255), (255, 0, 100), (100, 0, 255)]
            for i in range(LED_COUNT):
                ci = int((t + i * 2) % len(nc))
                fl = 0.7 + random.random() * 0.3
                self._set_led(i, int(nc[ci][0] * fl), int(nc[ci][1] * fl), int(nc[ci][2] * fl))
        elif self.effect == "warm_white":
            self._set_all(255, 180, 100)
        elif self.effect == "night_light":
            br = 0.05 + math.sin(step * 0.01) * 0.02
            self._set_all(int(255 * br), int(200 * br), int(120 * br))
        elif self.effect == "temp_reactive":
            t = max(30.0, min(80.0, self.cpu_temp))
            ratio = (t - 30.0) / 50.0
            if ratio < 0.5:
                self._set_all(0, int(255 * ratio * 2), int(255 * (1 - ratio * 2)))
            else:
                self._set_all(int(255 * (ratio - 0.5) * 2), int(255 * (1 - (ratio - 0.5) * 2)), 0)
        elif self.effect == "load_reactive":
            intensity = min(100.0, self.cpu_load) / 100.0
            self._set_all(int(c["r"] * intensity), int(c["g"] * intensity), int(c["b"] * intensity))

    @staticmethod
    def _hsv(h: float, s: float, v: float) -> tuple:
        r, g, b = colorsys.hsv_to_rgb(h / 360, s, v)
        return int(r * 255), int(g * 255), int(b * 255)

    # ═══════════════════════════════════════════════════════
    #  ANIMATIONS-LOOP (läuft nativ auf dem Pi!)
    # ═══════════════════════════════════════════════════════

    def start(self):
        if not self.available:
            logger.warning("LEDs nicht verfügbar — Engine läuft im Simulationsmodus")
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("LED Engine gestartet (nativ)")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self._set_all(0, 0, 0)
        self._show()

    def _loop(self):
        step = 0
        last_states = None

        while self._running:
            try:
                eff = self.effect

                # ─── Off: 1x senden, dann lange schlafen ───
                if eff == "off":
                    if last_states != "off":
                        self._set_all(0, 0, 0)
                        self._show()
                        last_states = "off"
                    # Warte auf Config-Änderung oder 500ms
                    self._config_changed.wait(timeout=0.5)
                    self._config_changed.clear()
                    continue

                # ─── Statische Effekte: nur bei Änderung senden ───
                if eff in ("static", "warm_white", "gradient"):
                    self._tick(step)
                    new_states = tuple((l["r"], l["g"], l["b"]) for l in self.led_states)
                    if new_states != last_states:
                        self._show()
                        last_states = new_states
                    step += 1
                    # Warte auf Config-Änderung oder 200ms
                    self._config_changed.wait(timeout=0.2)
                    self._config_changed.clear()
                    continue

                # ─── Animierte Effekte: 20-25 FPS ───
                self._tick(step)
                self._show()
                last_states = None
                step += 1
                time.sleep(0.04)  # 25 FPS

            except Exception as e:
                logger.error(f"LED Loop: {e}")
                time.sleep(0.5)

    # ═══════════════════════════════════════════════════════
    #  STATE (für Backend-Abfrage)
    # ═══════════════════════════════════════════════════════

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
            "led_states": list(self.led_states),
            "effects_catalog": self.EFFECTS,
        }

    def get_led_states(self) -> list[dict]:
        """Nur die aktuellen LED-Farben (für WebSocket Push)."""
        return list(self.led_states)

    def get_effects_by_category(self) -> dict:
        categories = {}
        for key, meta in self.EFFECTS.items():
            cat = meta["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(key)
        return categories

    # ═══════════════════════════════════════════════════════
    #  PERSISTENCE
    # ═══════════════════════════════════════════════════════

    def _save_settings(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
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
            logger.info(f"LED Settings geladen: {self.effect}, br={self.brightness}")
        except Exception as e:
            logger.error(f"LED Settings laden: {e}")
