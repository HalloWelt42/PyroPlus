"""
PyroPlus v3.0.0 — Hardware-Proxy
© HalloWelt42 - Nur für private Nutzung

Nativer systemd-Service mit integrierter LED-Engine.
LEDs werden lokal berechnet und direkt per SPI ausgegeben.
Backend sendet nur Konfigurationsänderungen (kein HTTP pro Frame).

Architektur:
  Backend (Docker) ─── 1x bei Änderung ──→ HW-Proxy ──→ SPI/I2C/GPIO
    Config-Manager                          LED-Engine (lokal, 25 FPS)
    OLED Renderer (1/s)                     Direct HW Access
    Stats/WebSocket                         Reports led_states zurück
"""

import base64
import io
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("hw-proxy")

VERSION = "3.0.0"
PORT = 8072

# ─── Hardware State ─────────────────────────────────────────
_fan_gpio = None
_fan_led_gpio = None
_fan_available = False
_fan_pwm_supported = False

_oled_device = None
_oled_available = False

_strip = None
_led_available = False
_led_count = 4

_led_engine = None  # LEDEffectEngine Instanz


# ═════════════════════════════════════════════════════════════
#  gpiochip Symlink (wie SunFounder pm_auto/utils.py)
# ═════════════════════════════════════════════════════════════

def _softlink_gpiochip0_to_gpiochip4():
    """Pi 5: gpiozero erwartet gpiochip0, neuer Kernel hat RP1 auf gpiochip4."""
    gpiochip0_label = "/sys/bus/gpio/devices/gpiochip0/label"
    gpiochip4 = "/dev/gpiochip4"

    if not os.path.exists(gpiochip4):
        return
    try:
        with open(gpiochip0_label, "r") as f:
            label = f.read().strip()
        if "pinctrl-rp1" in label:
            logger.info("gpiochip0 ist bereits RP1 — kein Symlink nötig")
            return
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning(f"gpiochip Label lesen: {e}")

    gpiochip0 = "/dev/gpiochip0"
    try:
        if os.path.islink(gpiochip0):
            os.remove(gpiochip0)
        if not os.path.exists(gpiochip0):
            os.symlink(gpiochip4, gpiochip0)
            logger.info("Symlink /dev/gpiochip0 → /dev/gpiochip4 erstellt")
    except Exception as e:
        logger.warning(f"gpiochip Symlink: {e}")


# ═════════════════════════════════════════════════════════════
#  Hardware Init / Cleanup
# ═════════════════════════════════════════════════════════════

def _init_hardware():
    global _fan_gpio, _fan_led_gpio, _fan_available, _fan_pwm_supported, _fan_hwmon_dir
    global _oled_device, _oled_available
    global _strip, _led_available, _led_engine

    # ─── Fan GPIO (Pin 6 = Fan, Pin 5 = Fan-LED) ──────
    _softlink_gpiochip0_to_gpiochip4()

    try:
        import gpiozero
        _fan_gpio = gpiozero.DigitalOutputDevice(6, initial_value=False)
        _fan_available = True
        logger.info("Fan GPIO: Pin 6 (gpiozero, initial=aus)")
    except Exception as e:
        logger.error(f"Fan GPIO Init: {e}")

    try:
        import gpiozero
        _fan_led_gpio = gpiozero.DigitalOutputDevice(5)
        _fan_led_gpio.value = 0
        logger.info("Fan LED: Pin 5 (gpiozero)")
    except Exception as e:
        logger.warning(f"Fan LED Init: {e}")

    # Fan PWM über Kernel
    _fan_pwm_supported = os.path.exists("/sys/devices/platform/cooling_fan")
    _fan_hwmon_dir = _find_fan_hwmon()
    logger.info(f"Fan PWM: {'ja' if _fan_pwm_supported else 'nein'}, hwmon: {_fan_hwmon_dir or 'nicht gefunden'}")

    # ─── OLED (SSD1306 I2C 0x3C) ──────────────────────
    try:
        from luma.oled.device import ssd1306
        from luma.core.interface.serial import i2c as i2c_serial
        serial = i2c_serial(port=1, address=0x3C)
        _oled_device = ssd1306(serial, width=128, height=64)
        _oled_device.contrast(200)
        _oled_available = True
        logger.info("OLED: SSD1306 128x64, I2C 0x3C")
    except Exception as e:
        logger.error(f"OLED Init: {e}")

    # ─── LEDs (neopixel_spi über /dev/spidev0.0) ──────
    if not os.path.exists("/dev/spidev0.0"):
        logger.error("SPI nicht aktiviert (/dev/spidev0.0 fehlt) — LEDs deaktiviert")
    else:
        try:
            import board
            import neopixel_spi as neopixel
            import time as _time
            spi = board.SPI()
            _strip = neopixel.NeoPixel_SPI(
                spi, _led_count, pixel_order=neopixel.GRB, auto_write=False,
            )
            _time.sleep(0.01)
            _strip.fill(0)
            _strip.show()
            _led_available = True
            logger.info(f"LEDs: {_led_count}x WS2812B (neopixel_spi)")
        except Exception as e:
            logger.error(f"LED Init: {e}")

    # ─── LED Effect Engine starten ─────────────────────
    from led_engine import LEDEffectEngine
    _led_engine = LEDEffectEngine(_strip)
    _led_engine.start()
    logger.info(f"LED Engine gestartet: Effekt={_led_engine.effect}, HW={'ja' if _strip else 'nein'}")


def _cleanup_hardware():
    global _led_engine

    # LED Engine stoppen (setzt LEDs auf schwarz)
    if _led_engine:
        _led_engine.stop()
        _led_engine = None

    if _fan_gpio:
        try:
            _fan_gpio.off()
            _fan_gpio.close()
        except Exception:
            pass
    if _fan_led_gpio:
        try:
            _fan_led_gpio.off()
            _fan_led_gpio.close()
        except Exception:
            pass
    if _oled_device and _oled_available:
        try:
            _oled_device.clear()
        except Exception:
            pass


# ═════════════════════════════════════════════════════════════
#  FastAPI
# ═════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"=== Hardware-Proxy v{VERSION} startet ===")
    _init_hardware()
    logger.info(f"Fan={_fan_available}, PWM={_fan_pwm_supported}, OLED={_oled_available}, LEDs={_led_available}")
    yield
    _cleanup_hardware()
    logger.info("=== Hardware-Proxy gestoppt ===")

app = FastAPI(title="PyroPlus HW-Proxy", version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ─── Models ─────────────────────────────────────────────────

class FanPWM(BaseModel):
    duty: float = Field(ge=0.0, le=100.0)

class OLEDBrightness(BaseModel):
    value: int = Field(ge=0, le=255)

class OLEDImage(BaseModel):
    image_base64: str

class LEDConfig(BaseModel):
    """Konfiguration vom Backend — wird nur bei Änderungen gesendet."""
    effect: Optional[str] = None
    color: Optional[dict] = None
    color2: Optional[dict] = None
    brightness: Optional[int] = None
    speed: Optional[float] = None
    individual_mode: Optional[bool] = None
    individual_colors: Optional[list[dict]] = None

class LEDSystemData(BaseModel):
    """System-Daten für reaktive Effekte (alle 2s vom Backend gepusht)."""
    cpu_temp: float = 40.0
    cpu_load: float = 10.0

# Legacy-Models (Abwärtskompatibilität)
class LEDColor(BaseModel):
    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)

class LEDSet(BaseModel):
    leds: list[LEDColor] = Field(min_length=1, max_length=4)

class LEDBrightness(BaseModel):
    value: int = Field(ge=0, le=255)


# ─── Health ─────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": VERSION,
        "fan": _fan_available,
        "fan_pwm": _fan_pwm_supported,
        "oled": _oled_available,
        "leds": _led_available,
        "led_engine": _led_engine is not None,
        "led_effect": _led_engine.effect if _led_engine else "off",
    }


# ─── Temperature ────────────────────────────────────────────

@app.get("/host-ip")
def get_host_ip():
    """Echte Host-IP (nicht Docker) — läuft nativ auf dem Pi."""
    import subprocess
    try:
        result = subprocess.run(['ip', '-4', 'route', 'get', '1.1.1.1'], capture_output=True, text=True, timeout=2)
        parts = result.stdout.split()
        if 'src' in parts:
            ip = parts[parts.index('src') + 1]
            return {"ip": ip}
    except: pass
    return {"ip": "N/A"}

@app.get("/temp")
def get_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return {"temp": round(int(f.read().strip()) / 1000.0, 1)}
    except Exception:
        return {"temp": 0.0}


# ─── Fan ────────────────────────────────────────────────────
# Der Lüfter wird über zwei Wege gesteuert:
# 1. PWM über /sys/.../pwm1 (0-255) = echte Geschwindigkeitssteuerung
# 2. GPIO Pin 6 = zusätzlicher An/Aus-Schalter
# Beide steuern denselben physischen Lüfter.

_fan_hwmon_dir: str = ""

def _find_fan_hwmon() -> str:
    """Findet den hwmon-Pfad für den Lüfter."""
    base = "/sys/devices/platform/cooling_fan/hwmon/"
    if os.path.exists(base):
        subs = os.listdir(base)
        if subs:
            return f"{base}{subs[0]}"
    return ""

def _fan_read_rpm() -> int:
    if not _fan_hwmon_dir:
        return 0
    try:
        with open(f"{_fan_hwmon_dir}/fan1_input") as f:
            return int(f.read().strip())
    except Exception:
        return 0

def _fan_read_pwm() -> int:
    if not _fan_hwmon_dir:
        return 0
    try:
        with open(f"{_fan_hwmon_dir}/pwm1") as f:
            return int(f.read().strip())
    except Exception:
        return 0

def _fan_write_pwm(value: int):
    """PWM-Wert setzen (0-255). Setzt vorher pwm1_enable auf manuell."""
    if not _fan_hwmon_dir:
        return
    try:
        with open(f"{_fan_hwmon_dir}/pwm1_enable", "w") as f:
            f.write("1")
        with open(f"{_fan_hwmon_dir}/pwm1", "w") as f:
            f.write(str(max(0, min(255, value))))
    except Exception as e:
        logger.error(f"PWM schreiben: {e}")

# ─── Fan Endpoints ──────────────────────────────────────────

@app.post("/fan/pwm")
def fan_set_pwm(req: FanPWM):
    """CPU-Lüfter PWM setzen (duty 0-100% → PWM 0-255). Nur PWM, kein GPIO."""
    pwm_value = int(req.duty / 100.0 * 255)
    _fan_write_pwm(pwm_value)
    return {
        "ok": True,
        "duty": req.duty,
        "pwm": pwm_value,
        "rpm": _fan_read_rpm(),
    }

@app.get("/fan/pwm")
def fan_get_pwm():
    """Aktuellen Lüfter-Status lesen."""
    pwm = _fan_read_pwm()
    rpm = _fan_read_rpm()
    return {
        "available": _fan_pwm_supported or _fan_available,
        "pwm": pwm,
        "duty": round(pwm / 255 * 100, 1),
        "rpm": rpm,
        "gpio_on": bool(_fan_gpio.value) if _fan_gpio else False,
    }

# ─── Gehäuselüfter (GPIO An/Aus) ────────────────────────────

@app.post("/fan/case")
def fan_case_set(req: dict):
    """Gehäuselüfter: GPIO Pin 6, nur An/Aus."""
    if not _fan_available or not _fan_gpio:
        return {"ok": False, "error": "Gehäuselüfter nicht verfügbar"}
    on = bool(req.get("on", False))
    try:
        _fan_gpio.value = 1 if on else 0
        if _fan_led_gpio:
            _fan_led_gpio.value = 1 if on else 0
        return {"ok": True, "on": on}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/fan/case")
def fan_case_get():
    """Gehäuselüfter Status."""
    on = bool(_fan_gpio.value) if _fan_gpio else False
    return {"available": _fan_available, "on": on}



# ─── OLED ───────────────────────────────────────────────────

@app.post("/oled/display")
def oled_display(req: OLEDImage):
    if not _oled_available:
        return {"ok": False, "error": "OLED nicht verfügbar"}
    try:
        from PIL import Image
        img_bytes = base64.b64decode(req.image_base64)
        img = Image.open(io.BytesIO(img_bytes)).convert("1")
        img = img.resize((128, 64))
        _oled_device.display(img)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/oled/brightness")
def oled_brightness(req: OLEDBrightness):
    if not _oled_available:
        return {"ok": False, "error": "OLED nicht verfügbar"}
    try:
        _oled_device.contrast(req.value)
        return {"ok": True, "brightness": req.value}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/oled/clear")
def oled_clear():
    if not _oled_available:
        return {"ok": False, "error": "OLED nicht verfügbar"}
    try:
        _oled_device.clear()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/oled/status")
def oled_status():
    return {"available": _oled_available}


# ═════════════════════════════════════════════════════════════
#  LEDs — NEUE ARCHITEKTUR (Config-basiert statt Frame-basiert)
# ═════════════════════════════════════════════════════════════

@app.post("/leds/config")
def leds_set_config(req: LEDConfig):
    """Backend sendet Konfigurationsänderung (nur bei Änderung, nicht pro Frame!).
    Dies ist der Hauptendpoint der neuen Architektur."""
    if not _led_engine:
        return {"ok": False, "error": "LED Engine nicht initialisiert"}
    config = req.model_dump(exclude_none=True)
    _led_engine.set_config(config)
    return {"ok": True, **{k: getattr(_led_engine, k) for k in config}}

@app.post("/leds/system-data")
def leds_system_data(req: LEDSystemData):
    """Backend pusht System-Daten für reaktive Effekte (alle 2-5s)."""
    if _led_engine:
        _led_engine.set_system_data(req.cpu_temp, req.cpu_load)
    return {"ok": True}

@app.get("/leds/state")
def leds_get_state():
    """Aktueller LED-State (für Backend WebSocket/Frontend)."""
    if not _led_engine:
        return {"available": False, "led_states": []}
    return _led_engine.get_state()

@app.get("/leds/states-only")
def leds_get_states_only():
    """Nur aktuelle LED-Farben (leichtgewichtig für häufige Abfrage)."""
    if not _led_engine:
        return {"led_states": []}
    return {"led_states": _led_engine.get_led_states()}

@app.get("/leds/status")
def leds_status():
    return {
        "available": _led_available,
        "count": _led_count,
        "engine": _led_engine is not None,
        "effect": _led_engine.effect if _led_engine else "off",
    }

@app.get("/leds/effects")
def leds_effects():
    """Effekt-Katalog."""
    if not _led_engine:
        return {"effects": {}, "by_category": {}}
    return {
        "effects": _led_engine.EFFECTS,
        "by_category": _led_engine.get_effects_by_category(),
    }


# ─── Legacy-Endpoints (Abwärtskompatibilität) ──────────────
# Diese werden nicht mehr vom Backend genutzt, bleiben aber
# für direkte API-Aufrufe erhalten.

@app.post("/leds/set")
def leds_set_legacy(req: LEDSet):
    """Legacy: Direkte LED-Farben setzen (umgeht die Engine)."""
    if not _strip or not _led_available:
        return {"ok": False, "error": "LEDs nicht verfügbar"}
    try:
        for i, c in enumerate(req.leds):
            if i < _led_count:
                _strip[i] = (c.r, c.g, c.b)
        _strip.show()
        return {"ok": True, "warning": "Legacy-Endpoint — nutze /leds/config"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/leds/brightness")
def leds_brightness_legacy(req: LEDBrightness):
    """Legacy: Brightness direkt setzen."""
    if _led_engine:
        # Mapping: 0-255 → 0-1000
        _led_engine.set_config({"brightness": int(req.value / 255 * 1000)})
        return {"ok": True, "brightness": req.value}
    return {"ok": False, "error": "LED Engine nicht initialisiert"}

@app.post("/leds/off")
def leds_off_legacy():
    """Legacy: LEDs ausschalten."""
    if _led_engine:
        _led_engine.set_config({"effect": "off"})
        return {"ok": True}
    return {"ok": False}


# ─── Startup ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
