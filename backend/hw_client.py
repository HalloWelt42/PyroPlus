"""
PyroPlus: Client zum Hardware-Proxy.

Alle Hardware-Zugriffe laufen über diese Funktionen. Ist HW_PROXY_URL auf
"none" gesetzt (Tests, Entwicklung ohne Pi), antwortet jede Funktion sofort mit
ihrem Rückfallwert, ohne Netzwerkzugriff.

LEDs:  nur Konfigurationsänderungen (keine HTTP-Anfrage je Bild).
OLED:  fertig gerenderte Bilder.
Lüfter: Sollwerte bei Änderung, Status auf Anfrage.
"""

import logging
from typing import Any, Optional

import httpx

from config import HW_PROXY_DISABLED, HW_PROXY_URL

logger = logging.getLogger("hw_client")

_client: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            base_url=HW_PROXY_URL,
            timeout=httpx.Timeout(5.0, connect=2.0),
        )
    return _client


def close() -> None:
    global _client
    if _client:
        _client.close()
        _client = None


def _call(method: str, path: str, json: Any = None, quiet: bool = False) -> Optional[dict]:
    """Eine Anfrage an den Proxy; None bei Abschaltung oder Fehler."""
    if HW_PROXY_DISABLED:
        return None
    try:
        antwort = _get_client().request(method, path, json=json)
        return antwort.json()
    except Exception as fehler:
        if not quiet:
            logger.error(f"Hardware-Proxy {method} {path}: {fehler}")
        return None


def available() -> bool:
    return not HW_PROXY_DISABLED


# Allgemein

def health() -> dict:
    daten = _call("GET", "/health")
    if daten is None:
        return {"status": "offline", "fan": False, "oled": False, "leds": False}
    return daten


def get_temp() -> float:
    daten = _call("GET", "/temp", quiet=True)
    if daten is not None:
        return float(daten.get("temp", 0.0))
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        return 0.0


def get_host_ip() -> str:
    daten = _call("GET", "/host-ip", quiet=True)
    return str(daten.get("ip", "N/A")) if daten else "N/A"


# Lüfter

def fan_set_pwm(duty: float) -> dict:
    daten = _call("POST", "/fan/pwm", json={"duty": round(duty, 1)})
    return daten if daten is not None else {"ok": False}


def fan_get_status() -> dict:
    daten = _call("GET", "/fan/pwm", quiet=True)
    return daten if daten is not None else {"available": False}


def fan_available() -> bool:
    return bool(fan_get_status().get("available", False))


def case_fan_set(on: bool) -> dict:
    daten = _call("POST", "/fan/case", json={"on": on})
    return daten if daten is not None else {"ok": False}


def case_fan_get() -> dict:
    daten = _call("GET", "/fan/case", quiet=True)
    return daten if daten is not None else {"available": False, "on": False}


# OLED

def oled_display(image_base64: str) -> bool:
    daten = _call("POST", "/oled/display", json={"image_base64": image_base64}, quiet=True)
    return bool(daten and daten.get("ok", False))


def oled_brightness(value: int) -> bool:
    daten = _call("POST", "/oled/brightness", json={"value": value})
    return bool(daten and daten.get("ok", False))


def oled_clear() -> bool:
    daten = _call("POST", "/oled/clear", quiet=True)
    return bool(daten and daten.get("ok", False))


def oled_available() -> bool:
    daten = _call("GET", "/oled/status", quiet=True)
    return bool(daten and daten.get("available", False))


# LEDs (konfigurationsbasiert)

def leds_config(**kwargs: Any) -> bool:
    """Konfigurationsänderung senden. Erlaubte Schlüssel: effect, color, color2,
    brightness, speed, individual_mode, individual_colors."""
    daten = _call("POST", "/leds/config", json=kwargs)
    return bool(daten and daten.get("ok", False))


def leds_push_system_data(cpu_temp: float, cpu_load: float) -> bool:
    daten = _call("POST", "/leds/system-data",
                  json={"cpu_temp": cpu_temp, "cpu_load": cpu_load}, quiet=True)
    return bool(daten and daten.get("ok", False))


def leds_get_state() -> dict:
    daten = _call("GET", "/leds/state")
    return daten if daten is not None else {"available": False, "led_states": []}


def leds_get_states_only() -> list[dict]:
    daten = _call("GET", "/leds/states-only", quiet=True)
    return list(daten.get("led_states", [])) if daten else []


def leds_available() -> bool:
    daten = _call("GET", "/leds/status", quiet=True)
    return bool(daten and daten.get("available", False))


def leds_effects() -> dict:
    daten = _call("GET", "/leds/effects", quiet=True)
    return daten if daten is not None else {"effects": {}, "by_category": {}}


def leds_off() -> bool:
    return leds_config(effect="off")
