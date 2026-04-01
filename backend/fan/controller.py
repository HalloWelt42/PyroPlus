"""
PironMan Deluxe v2.1.0 — Lüfter-Controller
© HalloWelt42 - Nur für private Nutzung

Präzisions-PWM-Steuerung über Hardware-Proxy.
"""

import time
import threading
import logging
import json
from typing import Optional

import hw_client
from config import (
    FAN_DEFAULT_CURVE, FAN_DEFAULT_HYSTERESIS,
    FAN_DEFAULT_RAMP_UP, FAN_DEFAULT_RAMP_DOWN, FAN_DEFAULT_MIN_SPEED,
    FAN_DEFAULT_POLL_INTERVAL, FAN_DEFAULT_MODE, FAN_PROFILES, DATA_DIR,
)
from stats import fan_speed_history

logger = logging.getLogger("fan")


class FanController:
    def __init__(self):
        self.mode: str = FAN_DEFAULT_MODE
        self.profile: str = "balanced"
        self.curve: list[dict] = [dict(p) for p in FAN_DEFAULT_CURVE]
        self.custom_curve: list[dict] = [dict(p) for p in FAN_DEFAULT_CURVE]
        self.manual_speed: float = 50.0
        self.hysteresis: float = FAN_DEFAULT_HYSTERESIS
        self.ramp_up: float = FAN_DEFAULT_RAMP_UP
        self.ramp_down: float = FAN_DEFAULT_RAMP_DOWN
        self.min_speed: float = FAN_DEFAULT_MIN_SPEED
        self.poll_interval: float = FAN_DEFAULT_POLL_INTERVAL
        self.current_speed: float = 0.0
        self.target_speed: float = 0.0
        self.current_temp: float = 0.0
        self.last_direction: str = "down"
        self.available: bool = hw_client.fan_available()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._load_settings()
        logger.info(f"Fan verfügbar: {self.available}")

    def get_speed_for_temp(self, temp: float) -> float:
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
                    return p1["speed"]
                ratio = (temp - p1["temp"]) / dt
                return p1["speed"] + ratio * (p2["speed"] - p1["speed"])
        return 0.0

    def set_curve(self, points: list[dict]) -> list[dict]:
        validated = []
        for p in points:
            temp = round(max(20.0, min(85.0, float(p["temp"]))) * 2) / 2
            speed = round(max(0.0, min(100.0, float(p["speed"]))))
            validated.append({"temp": temp, "speed": speed})
        validated.sort(key=lambda x: x["temp"])
        if len(validated) < 2:
            return self.curve
        with self._lock:
            self.curve = validated
            self.custom_curve = [dict(p) for p in validated]
            self.profile = "custom"
        self._save_settings()
        return self.curve

    def add_point(self, temp: float, speed: float) -> list[dict]:
        temp = round(max(20.0, min(85.0, temp)) * 2) / 2
        speed = round(max(0.0, min(100.0, speed)))
        with self._lock:
            for p in self.curve:
                if abs(p["temp"] - temp) < 0.25:
                    p["speed"] = speed
                    self._save_settings()
                    return self.curve
            self.curve.append({"temp": temp, "speed": speed})
            self.curve.sort(key=lambda x: x["temp"])
            self.profile = "custom"
            self.custom_curve = [dict(p) for p in self.curve]
        self._save_settings()
        return self.curve

    def remove_point(self, index: int) -> list[dict]:
        with self._lock:
            if len(self.curve) <= 2:
                return self.curve
            if 0 <= index < len(self.curve):
                self.curve.pop(index)
                self.profile = "custom"
                self.custom_curve = [dict(p) for p in self.curve]
        self._save_settings()
        return self.curve

    def update_point(self, index: int, temp: float, speed: float) -> list[dict]:
        with self._lock:
            if 0 <= index < len(self.curve):
                self.curve[index]["temp"] = round(max(20.0, min(85.0, temp)) * 2) / 2
                self.curve[index]["speed"] = round(max(0.0, min(100.0, speed)))
                self.curve.sort(key=lambda x: x["temp"])
                self.profile = "custom"
                self.custom_curve = [dict(p) for p in self.curve]
        self._save_settings()
        return self.curve

    def set_profile(self, name: str) -> dict:
        if name == "custom":
            with self._lock:
                self.curve = [dict(p) for p in self.custom_curve]
                self.profile = "custom"
        elif name in FAN_PROFILES:
            with self._lock:
                self.curve = [dict(p) for p in FAN_PROFILES[name]]
                self.profile = name
        else:
            return {"error": f"Unbekanntes Profil: {name}"}
        self._save_settings()
        return {"ok": True, "profile": name, "curve": self.curve}

    def set_mode(self, mode: str):
        if mode not in ("auto", "manual", "off"):
            return
        with self._lock:
            self.mode = mode
            if mode == "off":
                self.target_speed = 0
                self._apply_speed(0)
            elif mode == "manual":
                self.target_speed = self.manual_speed
        self._save_settings()

    def set_manual_speed(self, speed: float):
        self.manual_speed = round(max(0.0, min(100.0, speed)))
        if self.mode == "manual":
            self.target_speed = self.manual_speed
        self._save_settings()

    def set_fine_settings(self, hysteresis=None, ramp_up=None, ramp_down=None, min_speed=None, poll_interval=None):
        if hysteresis is not None:
            self.hysteresis = round(max(0.5, min(10.0, hysteresis)) * 2) / 2
        if ramp_up is not None:
            self.ramp_up = round(max(0.0, min(15.0, ramp_up)) * 2) / 2
        if ramp_down is not None:
            self.ramp_down = round(max(0.0, min(30.0, ramp_down)), 1)
        if min_speed is not None:
            self.min_speed = round(max(0.0, min(40.0, min_speed)))
        if poll_interval is not None:
            self.poll_interval = round(max(0.5, min(10.0, poll_interval)) * 2) / 2
        self._save_settings()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._control_loop, daemon=True)
        self._thread.start()
        logger.info("Lüfter-Controller gestartet")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._apply_speed(0)

    def _control_loop(self):
        last_time = time.time()
        while self._running:
            now = time.time()
            dt = now - last_time
            last_time = now
            self.current_temp = hw_client.get_temp()

            if self.mode == "auto":
                raw_target = self.get_speed_for_temp(self.current_temp)
                with self._lock:
                    if raw_target > self.target_speed:
                        self.target_speed = raw_target
                        self.last_direction = "up"
                    elif raw_target < self.target_speed:
                        hyst_target = self.get_speed_for_temp(self.current_temp + self.hysteresis)
                        if hyst_target < self.target_speed:
                            self.target_speed = raw_target
                            self.last_direction = "down"
                if self.target_speed > 0 and self.target_speed < self.min_speed:
                    self.target_speed = self.min_speed
            elif self.mode == "manual":
                self.target_speed = self.manual_speed
            elif self.mode == "off":
                self.target_speed = 0

            speed_diff = self.target_speed - self.current_speed
            if abs(speed_diff) > 0.5:
                if speed_diff > 0:
                    rate = 100.0 / max(0.1, self.ramp_up) if self.ramp_up > 0 else 1000.0
                    self.current_speed = min(self.target_speed, self.current_speed + rate * dt)
                else:
                    rate = 100.0 / max(0.1, self.ramp_down) if self.ramp_down > 0 else 1000.0
                    self.current_speed = max(self.target_speed, self.current_speed - rate * dt)
            else:
                self.current_speed = self.target_speed

            self._apply_speed(self.current_speed)
            fan_speed_history.append(round(self.current_speed, 1))
            time.sleep(self.poll_interval)

    def _apply_speed(self, speed: float):
        hw_client.fan_set_pwm(max(0.0, min(100.0, speed)))

    def get_state(self) -> dict:
        return {
            "available": self.available,
            "mode": self.mode,
            "profile": self.profile,
            "curve": self.curve,
            "current_speed": round(self.current_speed, 1),
            "target_speed": round(self.target_speed, 1),
            "current_temp": self.current_temp,
            "manual_speed": self.manual_speed,
            "estimated_rpm": round(self.current_speed * 60),
            "settings": {
                "hysteresis": self.hysteresis,
                "ramp_up": self.ramp_up,
                "ramp_down": self.ramp_down,
                "min_speed": self.min_speed,
                "poll_interval": self.poll_interval,
            },
            "profiles": list(FAN_PROFILES.keys()) + ["custom"],
        }

    def _save_settings(self):
        try:
            data = {
                "mode": self.mode, "profile": self.profile,
                "curve": self.curve, "custom_curve": self.custom_curve,
                "manual_speed": self.manual_speed, "hysteresis": self.hysteresis,
                "ramp_up": self.ramp_up, "ramp_down": self.ramp_down,
                "min_speed": self.min_speed, "poll_interval": self.poll_interval,
            }
            (DATA_DIR / "fan_settings.json").write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Fan-Settings speichern: {e}")

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
            self.ramp_up = data.get("ramp_up", self.ramp_up)
            self.ramp_down = data.get("ramp_down", self.ramp_down)
            self.min_speed = data.get("min_speed", self.min_speed)
            self.poll_interval = data.get("poll_interval", self.poll_interval)
            if "curve" in data and len(data["curve"]) >= 2:
                self.curve = data["curve"]
            if "custom_curve" in data and len(data["custom_curve"]) >= 2:
                self.custom_curve = data["custom_curve"]
        except Exception as e:
            logger.error(f"Fan-Settings laden: {e}")
