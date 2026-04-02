"""
PyroPlus v3.0.0 — Lüfter-Controller
© HalloWelt42 - Nur für private Nutzung

PWM-Steuerung über Temperaturkurve.
Überschreibt den Kernel-Governor alle 500ms.
Notfall-Sicherheit: Vollgas ab 80°C.
"""

import time
import threading
import logging
import json
from typing import Optional

import hw_client
from config import (
    FAN_DEFAULT_CURVE, FAN_DEFAULT_HYSTERESIS,
    FAN_DEFAULT_MODE, FAN_PROFILES, DATA_DIR,
)
from stats import fan_speed_history

logger = logging.getLogger("fan")

SAFETY_TEMP = 80.0  # Ab dieser Temperatur: Vollgas erzwungen
POLL_INTERVAL = 2.0  # 2s — Balance zwischen Reaktivität und Last


class FanController:
    def __init__(self):
        self.mode: str = FAN_DEFAULT_MODE
        self.profile: str = "balanced"
        self.curve: list[dict] = [dict(p) for p in FAN_DEFAULT_CURVE]
        self.custom_curve: list[dict] = [dict(p) for p in FAN_DEFAULT_CURVE]
        self.manual_speed: float = 50.0
        self.hysteresis: float = FAN_DEFAULT_HYSTERESIS
        self.current_duty: float = 0.0  # Aktueller PWM-Wert in % (0-100)
        self.current_temp: float = 0.0
        self.current_rpm: int = 0
        self.sim_temp: float | None = None
        self.available: bool = hw_client.fan_available()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._load_settings()
        logger.info(f"Lüfter verfügbar: {self.available}")

    # ═══════════════════════════════════════════════════════
    #  KURVEN-BERECHNUNG
    # ═══════════════════════════════════════════════════════

    def get_duty_for_temp(self, temp: float) -> float:
        """Berechne PWM-Duty (0-100%) für eine Temperatur anhand der Kurve."""
        if not self.curve or len(self.curve) < 2:
            return 0.0
        if temp <= self.curve[0]["temp"]:
            return self.curve[0]["speed"]
        if temp >= self.curve[-1]["temp"]:
            return self.curve[-1]["speed"]
        for i in range(len(self.curve) - 1):
            p1, p2 = self.curve[i], self.curve[i + 1]
            if p1["temp"] <= temp <= p2["temp"]:
                dt = p2["temp"] - p1["temp"]
                if dt == 0:
                    return p2["speed"]
                ratio = (temp - p1["temp"]) / dt
                return p1["speed"] + (p2["speed"] - p1["speed"]) * ratio
        return 0.0

    # ═══════════════════════════════════════════════════════
    #  KONFIGURATION
    # ═══════════════════════════════════════════════════════

    def set_mode(self, mode: str):
        if mode not in ("auto", "manual", "off"):
            return
        with self._lock:
            self.mode = mode
        self._save_settings()

    def set_profile(self, name: str) -> dict:
        if name == "custom":
            self.profile = "custom"
            self.curve = [dict(p) for p in self.custom_curve]
        elif name in FAN_PROFILES:
            self.profile = name
            self.curve = [dict(p) for p in FAN_PROFILES[name]]
        self._save_settings()
        return self.get_state()

    def set_curve(self, points: list[dict]) -> dict:
        validated = []
        for p in points:
            temp = round(max(20.0, min(85.0, float(p["temp"]))) * 2) / 2
            speed = round(max(0.0, min(100.0, float(p["speed"]))))
            validated.append({"temp": temp, "speed": speed})
        validated.sort(key=lambda x: x["temp"])
        if len(validated) >= 2:
            self.curve = validated
            self.custom_curve = [dict(p) for p in validated]
            self.profile = "custom"
            self._save_settings()
        return {"curve": self.curve}

    def set_manual_speed(self, speed: float):
        self.manual_speed = round(max(0.0, min(100.0, speed)))
        self._save_settings()

    def set_hysteresis(self, value: float):
        self.hysteresis = round(max(0.5, min(10.0, value)) * 2) / 2
        self._save_settings()

    def set_fine_settings(self, hysteresis=None, **kwargs):
        if hysteresis is not None:
            self.hysteresis = round(max(0.5, min(10.0, hysteresis)) * 2) / 2
        self._save_settings()

    # ═══════════════════════════════════════════════════════
    #  CONTROL LOOP (500ms, überschreibt Kernel-Governor)
    # ═══════════════════════════════════════════════════════

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._control_loop, daemon=True)
        self._thread.start()
        logger.info("Lüfter-Controller gestartet (500ms Loop)")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        hw_client.fan_set_pwm(0)

    def _control_loop(self):
        while self._running:
            # Temperatur lesen
            self.current_temp = self.sim_temp if self.sim_temp is not None else hw_client.get_temp()

            # Sicherheit: Ab 80°C immer Vollgas
            if self.current_temp >= SAFETY_TEMP:
                target = 100.0
            elif self.mode == "auto":
                target = self.get_duty_for_temp(self.current_temp)
                # Hysterese: nur runterregeln wenn Differenz groß genug
                if target < self.current_duty:
                    temp_with_hyst = self.current_temp + self.hysteresis
                    hyst_target = self.get_duty_for_temp(temp_with_hyst)
                    if hyst_target >= self.current_duty:
                        target = self.current_duty  # Halten
            elif self.mode == "manual":
                target = self.manual_speed
            else:  # off
                target = 0.0

            # PWM setzen (überschreibt Kernel-Governor)
            self.current_duty = round(target, 1)
            hw_client.fan_set_pwm(self.current_duty)

            # RPM separat lesen (aktueller Wert, nicht aus Set-Antwort)
            try:
                status = hw_client.fan_get_status()
                self.current_rpm = status.get("rpm", 0)
            except Exception:
                self.current_rpm = 0

            time.sleep(POLL_INTERVAL)

    # ═══════════════════════════════════════════════════════
    #  STATE
    # ═══════════════════════════════════════════════════════

    def get_state(self) -> dict:
        return {
            "available": self.available,
            "mode": self.mode,
            "profile": self.profile,
            "curve": self.curve,
            "current_duty": self.current_duty,
            "current_temp": round(self.current_temp, 1),
            "current_rpm": self.current_rpm,
            "manual_speed": self.manual_speed,
            "hysteresis": self.hysteresis,
            "profiles": list(FAN_PROFILES.keys()) + ["custom"],
            "safety_temp": SAFETY_TEMP,
        }

    # ═══════════════════════════════════════════════════════
    #  PERSISTENZ
    # ═══════════════════════════════════════════════════════

    def _save_settings(self):
        try:
            data = {
                "mode": self.mode, "profile": self.profile,
                "curve": self.curve, "custom_curve": self.custom_curve,
                "manual_speed": self.manual_speed,
                "hysteresis": self.hysteresis,
            }
            (DATA_DIR / "fan_settings.json").write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Lüfter-Einstellungen speichern: {e}")

    def _load_settings(self):
        path = DATA_DIR / "fan_settings.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.mode = data.get("mode", self.mode)
            self.profile = data.get("profile", self.profile)
            self.manual_speed = data.get("manual_speed", self.manual_speed)
            self.hysteresis = data.get("hysteresis", self.hysteresis)
            if "curve" in data and len(data["curve"]) >= 2:
                self.curve = data["curve"]
            if "custom_curve" in data and len(data["custom_curve"]) >= 2:
                self.custom_curve = data["custom_curve"]
            logger.info(f"Lüfter-Einstellungen geladen: Modus={self.mode}, Profil={self.profile}")
        except Exception as e:
            logger.error(f"Lüfter-Einstellungen laden: {e}")
