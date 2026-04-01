"""
PironMan Deluxe v2.5.4 — Hardware-Proxy Client
© HalloWelt42 - Nur für private Nutzung

Config-basierte Kommunikation mit dem HW-Proxy.
LEDs: Sendet nur Konfigurationsänderungen (kein HTTP pro Frame).
OLED: Sendet gerenderte Bilder (1x/s — akzeptabel).
Fan:  Sendet bei Änderungen.
"""

import logging
from typing import Optional
import httpx

from config import HW_PROXY_URL

logger = logging.getLogger("hw_client")

# ─── Shared Client (Connection Pooling) ─────────────────────
_client: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            base_url=HW_PROXY_URL,
            timeout=httpx.Timeout(5.0, connect=2.0),
        )
    return _client


def close():
    global _client
    if _client:
        _client.close()
        _client = None


def health() -> dict:
    try:
        r = _get_client().get("/health")
        return r.json()
    except Exception as e:
        logger.error(f"HW-Proxy nicht erreichbar: {e}")
        return {"status": "offline", "fan": False, "oled": False, "leds": False}


# ─── Temperatur ─────────────────────────────────────────────

def get_temp() -> float:
    try:
        r = _get_client().get("/temp")
        return r.json().get("temp", 0.0)
    except Exception:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return round(int(f.read().strip()) / 1000.0, 1)
        except Exception:
            return 0.0


# ─── Fan ────────────────────────────────────────────────────

def fan_set_pwm(duty: float) -> bool:
    try:
        r = _get_client().post("/fan/pwm", json={"duty": round(duty, 1)})
        return r.json().get("ok", False)
    except Exception as e:
        logger.error(f"Fan PWM: {e}")
        return False


def fan_available() -> bool:
    try:
        r = _get_client().get("/fan/pwm")
        return r.json().get("available", False)
    except Exception:
        return False


# ─── OLED ───────────────────────────────────────────────────

def oled_display(image_base64: str) -> bool:
    try:
        r = _get_client().post("/oled/display", json={"image_base64": image_base64})
        return r.json().get("ok", False)
    except Exception as e:
        logger.error(f"OLED Display: {e}")
        return False


def oled_brightness(value: int) -> bool:
    try:
        r = _get_client().post("/oled/brightness", json={"value": value})
        return r.json().get("ok", False)
    except Exception as e:
        logger.error(f"OLED Brightness: {e}")
        return False


def oled_clear() -> bool:
    try:
        r = _get_client().post("/oled/clear")
        return r.json().get("ok", False)
    except Exception:
        return False


def oled_available() -> bool:
    try:
        r = _get_client().get("/oled/status")
        return r.json().get("available", False)
    except Exception:
        return False


# ═════════════════════════════════════════════════════════════
#  LEDs — NEUE CONFIG-BASIERTE API
# ═════════════════════════════════════════════════════════════

def leds_config(**kwargs) -> bool:
    """LED-Konfiguration an Proxy senden (nur bei Änderungen!).

    Beispiel: leds_config(effect="rainbow", speed=100)
    Erlaubte Keys: effect, color, color2, brightness, speed,
                   individual_mode, individual_colors
    """
    try:
        r = _get_client().post("/leds/config", json=kwargs)
        return r.json().get("ok", False)
    except Exception as e:
        logger.error(f"LED Config: {e}")
        return False


def leds_push_system_data(cpu_temp: float, cpu_load: float) -> bool:
    """System-Daten für reaktive Effekte pushen (alle 2-5s)."""
    try:
        r = _get_client().post("/leds/system-data", json={
            "cpu_temp": cpu_temp, "cpu_load": cpu_load
        })
        return r.json().get("ok", False)
    except Exception:
        return False


def leds_get_state() -> dict:
    """Aktuellen LED-State vom Proxy holen (für WebSocket/Frontend)."""
    try:
        r = _get_client().get("/leds/state")
        return r.json()
    except Exception as e:
        logger.error(f"LED State: {e}")
        return {"available": False, "led_states": []}


def leds_get_states_only() -> list[dict]:
    """Nur LED-Farben holen (leichtgewichtig)."""
    try:
        r = _get_client().get("/leds/states-only")
        return r.json().get("led_states", [])
    except Exception:
        return []


def leds_available() -> bool:
    try:
        r = _get_client().get("/leds/status")
        return r.json().get("available", False)
    except Exception:
        return False


def leds_effects() -> dict:
    """Effekt-Katalog vom Proxy."""
    try:
        r = _get_client().get("/leds/effects")
        return r.json()
    except Exception:
        return {"effects": {}, "by_category": {}}


# ─── Legacy (für Abwärtskompatibilität) ─────────────────────

def leds_set(colors: list[dict]) -> bool:
    """DEPRECATED: Direkte Farbsetzung. Nutze leds_config() stattdessen."""
    logger.warning("leds_set() ist deprecated — nutze leds_config()")
    try:
        r = _get_client().post("/leds/set", json={"leds": colors})
        return r.json().get("ok", False)
    except Exception:
        return False


def leds_brightness(value: int) -> bool:
    """DEPRECATED: Nutze leds_config(brightness=X) stattdessen."""
    return leds_config(brightness=int(value / 255 * 1000))


def leds_off() -> bool:
    """LEDs ausschalten."""
    return leds_config(effect="off")
