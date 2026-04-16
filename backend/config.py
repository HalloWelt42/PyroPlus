"""
PyroPlus v3.0.0 — Konfiguration
© HalloWelt42 - Nur für private Nutzung
"""

import os
import secrets
import logging
from pathlib import Path

VERSION = "4.3.0"
APP_NAME = "PyroPlus"

# ─── Pfade ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
PROFILES_DIR = DATA_DIR / "profiles"
PRESETS_DIR = DATA_DIR / "presets"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROFILES_DIR.mkdir(parents=True, exist_ok=True)
PRESETS_DIR.mkdir(parents=True, exist_ok=True)

# ─── API Token ──────────────────────────────────────────────
# Wird beim ersten Start generiert und in data/api_token.txt gespeichert.
# Der User kann den Token dort auslesen.
# Frontend bekommt ihn über den /api/token Endpoint (nur lokal erreichbar).
TOKEN_FILE = DATA_DIR / "api_token.txt"

def _load_or_create_token() -> str:
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
        if len(token) >= 32:
            return token
    token = secrets.token_urlsafe(32)
    TOKEN_FILE.write_text(token + "\n")
    return token

API_TOKEN = _load_or_create_token()

# ─── Server ─────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8071))

# ─── Hardware-Proxy ─────────────────────────────────────────
HW_PROXY_URL = os.getenv("HW_PROXY_URL", "http://host.docker.internal:8072")

# ─── OLED ───────────────────────────────────────────────────
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_DEFAULT_BRIGHTNESS = 200
OLED_ROTATION_INTERVAL = 10

# ─── LEDs ───────────────────────────────────────────────────
LED_COUNT = 4
LED_DEFAULT_BRIGHTNESS = 500
LED_DEFAULT_EFFECT = "static"
LED_DEFAULT_COLOR = {"r": 0, "g": 100, "b": 255}

# ─── Fan Defaults ───────────────────────────────────────────
FAN_DEFAULT_MODE = "auto"
FAN_DEFAULT_HYSTERESIS = 3.0
FAN_DEFAULT_RAMP_UP = 3.0
FAN_DEFAULT_RAMP_DOWN = 8.0
FAN_DEFAULT_MIN_SPEED = 0
FAN_DEFAULT_POLL_INTERVAL = 1.0

FAN_DEFAULT_CURVE = [
    {"temp": 30.0, "speed": 0}, {"temp": 40.0, "speed": 0},
    {"temp": 45.0, "speed": 15}, {"temp": 50.0, "speed": 25},
    {"temp": 55.0, "speed": 40}, {"temp": 60.0, "speed": 55},
    {"temp": 65.0, "speed": 75}, {"temp": 70.0, "speed": 90},
    {"temp": 75.0, "speed": 100},
]

FAN_PROFILES = {
    "silent": [
        {"temp": 30.0, "speed": 0}, {"temp": 50.0, "speed": 0},
        {"temp": 55.0, "speed": 15}, {"temp": 60.0, "speed": 30},
        {"temp": 65.0, "speed": 50}, {"temp": 75.0, "speed": 80},
    ],
    "balanced": FAN_DEFAULT_CURVE,
    "performance": [
        {"temp": 30.0, "speed": 15}, {"temp": 35.0, "speed": 25},
        {"temp": 40.0, "speed": 40}, {"temp": 45.0, "speed": 55},
        {"temp": 50.0, "speed": 70}, {"temp": 55.0, "speed": 85},
        {"temp": 60.0, "speed": 100},
    ],
}

# ─── WebSocket ──────────────────────────────────────────────
WS_STATS_INTERVAL = 1.0

# ─── Logging ────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
