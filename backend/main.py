"""
PyroPlus v3.0.0 — FastAPI Backend
© HalloWelt42 - Nur für private Nutzung

Swagger-UI: http://host:8071/docs
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

import hw_client
from config import VERSION, APP_NAME, HOST, PORT, WS_STATS_INTERVAL, API_TOKEN, TOKEN_FILE
from stats import collect_stats
from fan.controller import FanController
from oled.engine import OLEDEngine
from effects.engine import LEDEngine

logger = logging.getLogger("api")

fan: Optional[FanController] = None
oled: Optional[OLEDEngine] = None
leds: Optional[LEDEngine] = None
ws_clients: set[WebSocket] = set()
_custom_data: dict[str, dict] = {}


# ─── Token Auth Middleware ──────────────────────────────────
OPEN_PATHS = {"/api/token", "/docs", "/openapi.json", "/redoc", "/health"}

class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Offene Pfade brauchen kein Token
        if path in OPEN_PATHS or path.startswith("/ws"):
            return await call_next(request)
        # Token prüfen
        token = request.headers.get("X-API-Token") or request.query_params.get("token")
        if token != API_TOKEN:
            return JSONResponse(status_code=401, content={"error": "Ungültiger API-Token"})
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global fan, oled, leds
    logger.info(f"=== {APP_NAME} v{VERSION} startet ===")
    logger.info(f"API-Token: {API_TOKEN[:8]}... (gespeichert in {TOKEN_FILE})")

    hw_status = hw_client.health()
    logger.info(f"Hardware-Proxy: {hw_status}")

    fan = FanController()
    fan.start()
    oled = OLEDEngine()
    oled.start()
    leds = LEDEngine()
    leds.start()

    push_task = asyncio.create_task(_ws_push_loop())
    logger.info("=== Alle Systeme aktiv ===")
    yield

    push_task.cancel()
    fan.stop()
    oled.stop()
    leds.stop()
    hw_client.close()
    logger.info(f"=== {APP_NAME} gestoppt ===")


app = FastAPI(title=APP_NAME, version=VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.add_middleware(TokenAuthMiddleware)


# ─── Models ─────────────────────────────────────────────────
class ColorModel(BaseModel):
    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)

class FanManualSpeed(BaseModel):
    speed: float = Field(ge=0.0, le=100.0)

class FanFineSettings(BaseModel):
    hysteresis: Optional[float] = Field(None, ge=0.5, le=10.0)
    ramp_up: Optional[float] = Field(None, ge=0.0, le=15.0)
    ramp_down: Optional[float] = Field(None, ge=0.0, le=30.0)
    min_speed: Optional[float] = Field(None, ge=0.0, le=40.0)
    poll_interval: Optional[float] = Field(None, ge=0.5, le=10.0)
    threshold_on: Optional[float] = Field(None, ge=35, le=75)
    threshold_off: Optional[float] = Field(None, ge=30, le=70)
    case_profile: Optional[str] = None

class CurvePoint(BaseModel):
    temp: float = Field(ge=20.0, le=85.0)
    speed: float = Field(ge=0.0, le=100.0)

class FanCurveRequest(BaseModel):
    points: list[CurvePoint] = Field(min_length=2)

class OLEDScreenData(BaseModel):
    """Flexibles Screen-Format: type + screen-spezifische Felder."""
    type: str
    name: str = ""
    # system screens
    widgets: Optional[list[dict]] = None
    # custom_text
    lines: Optional[list[str]] = None
    font_scale: Optional[int] = None
    align: Optional[str] = None
    # pixel_art
    art_id: Optional[str] = None
    # marquee
    text: Optional[str] = None
    speed: Optional[int] = None
    y: Optional[int] = None

class OLEDClockSettings(BaseModel):
    blink: Optional[bool] = None
    seconds: Optional[bool] = None
    tenths: Optional[bool] = None
    date: Optional[bool] = None
    weekday: Optional[bool] = None
    format_24h: Optional[bool] = None

class PixelArtData(BaseModel):
    id: str
    name: str = ""
    pixels: list[dict]


class LEDIndividualColor(BaseModel):
    index: int = Field(ge=0, le=3)
    color: ColorModel

class CustomDataEntry(BaseModel):
    label: str = Field(max_length=100, description="Anzeigename")
    value: str = Field(max_length=1000, description="Wert (Text/Zahl)")
    unit: str = Field("", max_length=20, description="Einheit (optional)")
    icon: str = Field("📊", max_length=4, description="Emoji-Icon")
    category: str = Field("custom", max_length=50, description="Kategorie")
    url: str = Field("", max_length=500, description="Link (optional)")


# ─── Token / System ────────────────────────────────────────
@app.get("/api/token", tags=["System"],
         summary="API-Token abrufen (kein Auth nötig)")
def get_api_token():
    """Gibt den API-Token zurück. Das Frontend ruft diesen beim Start ab."""
    return {"token": API_TOKEN, "info": "Sende diesen Token als X-API-Token Header"}

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "version": VERSION}

@app.get("/api/info", tags=["System"])
def get_info():
    return {"app": APP_NAME, "version": VERSION}

@app.get("/api/stats", tags=["System"])
def get_stats():
    return collect_stats()

@app.get("/api/state", tags=["System"],
         summary="Kompletter Systemstatus")
def get_full_state():
    # LED-States frisch vom HW-Proxy holen
    if leds:
        leds.refresh_led_states()
    return {
        "version": VERSION,
        "hw_proxy": hw_client.health(),
        "fan": fan.get_state() if fan else {},
        "oled": oled.get_state() if oled else {},
        "leds": leds.get_state() if leds else {},
        "stats": collect_stats(),
        "custom_data": _custom_data,
    }


# ─── Fan ────────────────────────────────────────────────────
@app.get("/api/fan", tags=["Lüfter"])
def fan_get_state():
    return fan.get_state()

@app.post("/api/fan/mode/{mode}", tags=["Lüfter"],
          summary="Lüfter-Modus: auto | manual | off")
def fan_set_mode(mode: str):
    if mode not in ("auto", "manual", "off"):
        return {"error": "Ungültiger Modus. Erlaubt: auto, manual, off"}
    fan.set_mode(mode)
    return {"ok": True, "mode": mode}

@app.post("/api/fan/profile/{name}", tags=["Lüfter"],
          summary="Auto-Profil wählen: silent | balanced | performance | night")
def fan_set_profile(name: str):
    return fan.set_profile(name)

@app.post("/api/fan/curve", tags=["Lüfter"],
          summary="Benutzerdefinierte Temperaturkurve setzen")
def fan_set_curve(req: FanCurveRequest):
    points = [{"temp": p.temp, "speed": p.speed} for p in req.points]
    fan.set_curve(points)
    return {"ok": True, **fan.get_state()}

@app.post("/api/fan/manual-speed", tags=["Lüfter"],
          summary="Manuelle Geschwindigkeit setzen (0-100%)")
def fan_set_manual_speed(req: FanManualSpeed):
    fan.set_manual_speed(req.speed)
    return {"ok": True, "speed": req.speed}

@app.post("/api/fan/settings", tags=["Lüfter"],
          summary="Feineinstellungen (Hysterese)")
def fan_set_fine_settings(req: FanFineSettings):
    fan.set_fine_settings(
        hysteresis=req.hysteresis,
        threshold_on=req.threshold_on,
        threshold_off=req.threshold_off,
        case_profile=req.case_profile,
    )
    return {"ok": True, **fan.get_state()}

@app.get("/api/fan/duty-for-temp", tags=["Lüfter"],
         summary="Berechne PWM-Duty für eine Temperatur")
def fan_duty_for_temp(temp: float = Query()):
    return {"temp": temp, "duty": round(fan.get_duty_for_temp(temp), 1)}


# ─── SIMULATION ─────────────────────────────────────────────
_sim_temp: float | None = None

@app.post("/api/simulate/temp", tags=["Simulation"],
          summary="Temperatur simulieren (wirkt auf LEDs und Lüfter)")
def simulate_temp(req: dict):
    global _sim_temp
    temp = req.get("temp")
    if temp is None:
        _sim_temp = None
        if fan:
            fan.sim_temp = None
            # Sofort echte Temperatur lesen und Fan-State aktualisieren
            real_temp = hw_client.get_temp() if hw_client else 40.0
            fan.current_temp = real_temp
        # Sofort echte Temperatur an HW-Proxy pushen
        if leds:
            real_temp = hw_client.get_temp() if hw_client else 40.0
            leds.update_system_data(real_temp, leds.cpu_load)
        return {"ok": True, "simulation": False}
    _sim_temp = float(temp)
    if leds: leds.update_system_data(_sim_temp, leds.cpu_load)
    if fan: fan.sim_temp = _sim_temp
    return {"ok": True, "simulation": True, "temp": _sim_temp}


# ─── OLED ───────────────────────────────────────────────────
@app.get("/api/oled", tags=["OLED Display"])
def oled_get_state():
    return oled.get_state()

@app.get("/api/oled/widget-catalog", tags=["OLED Display"],
         summary="Verfügbare Widget-Typen für den visuellen Editor")
def oled_widget_catalog():
    from oled.engine import OLEDEngine
    return OLEDEngine.WIDGET_CATALOG

@app.post("/api/oled/display-raw", tags=["OLED Display"],
          summary="Bild direkt an OLED senden (Base64 PNG)")
def oled_display_raw(req: dict):
    image_base64 = req.get("image_base64", "")
    if not image_base64:
        return {"error": "Kein Bild"}
    result = hw_client.oled_display(image_base64)
    return {"ok": result}

@app.post("/api/oled/mode/{mode}", tags=["OLED Display"],
          summary="Display-Modus: auto | manual | off")
def oled_set_mode(mode: str):
    if mode not in ("auto", "manual", "off"):
        return {"error": "Ungültiger Modus. Erlaubt: auto, manual, off"}
    oled.set_mode(mode)
    return {"ok": True, "mode": mode}

@app.post("/api/oled/brightness/{value}", tags=["OLED Display"])
def oled_set_brightness(value: int):
    oled.set_brightness(value)
    return {"ok": True, "brightness": oled.brightness}

@app.post("/api/oled/rotation/{seconds}", tags=["OLED Display"])
def oled_set_rotation(seconds: int):
    oled.set_rotation_interval(seconds)
    return {"ok": True, "rotation_interval": oled.rotation_interval}

@app.post("/api/oled/screen/{index}", tags=["OLED Display"])
def oled_set_screen(index: int):
    oled.set_screen(index)
    return {"ok": True, "current_screen": oled.current_screen, "preview": oled._last_preview}

@app.post("/api/oled/screens", tags=["OLED Display"],
          summary="Screen hinzufügen")
def oled_add_screen(req: OLEDScreenData):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    idx = oled.add_screen(data)
    return {"ok": True, "index": idx, "screens": oled.screens}

@app.put("/api/oled/screens/{index}", tags=["OLED Display"],
         summary="Screen aktualisieren")
def oled_update_screen(index: int, req: OLEDScreenData):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    oled.update_screen(index, data)
    return {"ok": True, "screens": oled.screens, "preview": oled._last_preview}

@app.delete("/api/oled/screens/{index}", tags=["OLED Display"])
def oled_remove_screen(index: int):
    oled.remove_screen(index)
    return {"ok": True, "screens": oled.screens}

@app.post("/api/oled/screens/reorder", tags=["OLED Display"],
          summary="Screens umsortieren")
def oled_reorder_screens(order: list[int]):
    oled.reorder_screens(order)
    return {"ok": True, "screens": oled.screens}

@app.get("/api/oled/preview", tags=["OLED Display"])
def oled_get_preview():
    return {"preview": oled._last_preview}

@app.post("/api/oled/clock", tags=["OLED Display"],
          summary="Uhr-Einstellungen")
def oled_set_clock(req: OLEDClockSettings):
    settings = {k: v for k, v in req.model_dump().items() if v is not None}
    oled.set_clock_settings(settings)
    return {"ok": True, "clock_settings": oled.clock_settings}

# ─── Pixel Art ─────────────────────────────────────────────
@app.get("/api/oled/pixel-arts", tags=["OLED Pixel Art"])
def oled_list_pixel_arts():
    return {"pixel_arts": oled.list_pixel_arts()}

@app.get("/api/oled/pixel-arts/{art_id}", tags=["OLED Pixel Art"])
def oled_get_pixel_art(art_id: str):
    data = oled.get_pixel_art(art_id)
    if not data:
        return {"error": "Nicht gefunden"}
    return data

@app.post("/api/oled/pixel-arts", tags=["OLED Pixel Art"],
          summary="Pixel Art speichern")
def oled_save_pixel_art(req: PixelArtData):
    data = oled.save_pixel_art(req.id, [p for p in req.pixels], req.name)
    return {"ok": True, "pixel_art": data}

@app.delete("/api/oled/pixel-arts/{art_id}", tags=["OLED Pixel Art"])
def oled_delete_pixel_art(art_id: str):
    oled.delete_pixel_art(art_id)
    return {"ok": True}


# ─── LEDs ───────────────────────────────────────────────────
@app.get("/api/leds", tags=["WS2812B LEDs"])
def leds_get_state():
    return leds.get_state()

@app.get("/api/leds/effects", tags=["WS2812B LEDs"],
         summary="Alle verfügbaren LED-Effekte")
def leds_get_effects():
    return leds.get_effects_list()

@app.post("/api/leds/effect/{name}", tags=["WS2812B LEDs"],
          summary="LED-Effekt aktivieren (oder 'off' zum Ausschalten)")
def leds_set_effect(name: str):
    if name != "off" and name not in leds.EFFECTS:
        return {"error": f"Unbekannter Effekt: {name}"}
    leds.set_effect(name)
    return {"ok": True, "effect": name}

@app.post("/api/leds/color", tags=["WS2812B LEDs"],
          summary="Primärfarbe setzen (RGB)")
def leds_set_color(color: ColorModel):
    leds.set_color(color.r, color.g, color.b)
    return {"ok": True, "color": leds.color}

@app.post("/api/leds/color2", tags=["WS2812B LEDs"],
          summary="Sekundärfarbe setzen (RGB)")
def leds_set_color2(color: ColorModel):
    leds.set_color2(color.r, color.g, color.b)
    return {"ok": True, "color2": leds.color2}

@app.post("/api/leds/brightness/{value}", tags=["WS2812B LEDs"],
          summary="LED-Helligkeit (1-1000, nicht-linear auf 0-255 gemappt)")
def leds_set_brightness(value: int):
    leds.set_brightness(value)
    return {"ok": True, "brightness": leds.brightness}

@app.post("/api/leds/speed/{value}", tags=["WS2812B LEDs"],
          summary="Effekt-Geschwindigkeit (1-1000)")
def leds_set_speed(value: float):
    leds.set_speed(value)
    return {"ok": True, "speed": leds.speed}

@app.post("/api/leds/individual", tags=["WS2812B LEDs"],
          summary="Einzelne LED steuern (Index 0-3)")
def leds_set_individual(req: LEDIndividualColor):
    leds.set_individual_color(req.index, req.color.r, req.color.g, req.color.b)
    return {"ok": True, "index": req.index, "color": leds.individual_colors[req.index]}

@app.post("/api/leds/individual-mode/{enabled}", tags=["WS2812B LEDs"])
def leds_set_individual_mode(enabled: bool):
    leds.individual_mode = enabled
    hw_client.leds_config(individual_mode=enabled)
    leds._save_settings()
    return {"ok": True, "individual_mode": enabled}


# ─── Quick Actions ──────────────────────────────────────────
@app.post("/api/quick/leds-off", tags=["Schnellzugriff"])
def quick_leds_off():
    leds.set_effect("off")
    return {"ok": True, "effect": "off"}

@app.post("/api/quick/leds-on", tags=["Schnellzugriff"])
def quick_leds_on():
    last = leds.effect if leds.effect and leds.effect != "off" else "static"
    leds.set_effect(last)
    return {"ok": True, "effect": leds.effect}

@app.post("/api/quick/oled-off", tags=["Schnellzugriff"])
def quick_oled_off():
    oled.set_mode("off")
    return {"ok": True, "mode": "off"}

@app.post("/api/quick/oled-on", tags=["Schnellzugriff"])
def quick_oled_on():
    oled.set_mode("auto")
    return {"ok": True, "mode": "auto"}

@app.post("/api/quick/fan-auto", tags=["Schnellzugriff"])
def quick_fan_auto():
    fan.set_mode("auto")
    return {"ok": True, "mode": "auto"}

@app.post("/api/quick/fan-off", tags=["Schnellzugriff"])
def quick_fan_off():
    fan.set_mode("off")
    return {"ok": True, "mode": "off"}


# ─── Disk Config ───────────────────────────────────────────
@app.get("/api/disks/all", tags=["System"],
         summary="Alle erkannten Laufwerke (für Settings)")
def get_all_disks():
    from stats import get_all_disks as _all
    return {"disks": _all()}

@app.get("/api/disks/config", tags=["System"],
         summary="Aktuelle Disk-Überwachungskonfiguration")
def get_disk_config():
    from stats import get_disk_config as _cfg
    return _cfg()

class DiskConfigModel(BaseModel):
    monitored_mounts: list[str]

@app.post("/api/disks/config", tags=["System"],
          summary="Disk-Überwachung konfigurieren")
def set_disk_config(req: DiskConfigModel):
    from stats import set_disk_config as _set
    _set({"monitored_mounts": req.monitored_mounts})
    return {"ok": True, "monitored_mounts": req.monitored_mounts}


# ─── Custom Data ────────────────────────────────────────────
@app.get("/api/custom", tags=["Custom Data"],
         summary="Alle registrierten Custom-Datenquellen")
def get_custom_data():
    return {"entries": _custom_data, "count": len(_custom_data)}

@app.get("/api/custom/{key}", tags=["Custom Data"])
def get_custom_entry(key: str):
    if key not in _custom_data:
        return {"error": f"Key '{key}' nicht gefunden"}
    return _custom_data[key]

@app.put("/api/custom/{key}", tags=["Custom Data"],
         summary="Custom-Datenquelle registrieren/aktualisieren")
def put_custom_entry(key: str, entry: CustomDataEntry):
    """Externe Scripte können per PUT eigene Daten registrieren.

    Beispiel (z.B. als Cronjob):
    ```
    curl -X PUT http://localhost:8071/api/custom/pihole \\
      -H 'Content-Type: application/json' \\
      -H 'X-API-Token: DEIN_TOKEN' \\
      -d '{"label":"Pi-hole Blocked","value":"1234","unit":"heute","icon":"🛡️"}'
    ```
    """
    _custom_data[key] = {
        "key": key, **entry.model_dump(),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return {"ok": True, "key": key}

@app.delete("/api/custom/{key}", tags=["Custom Data"])
def delete_custom_entry(key: str):
    if key in _custom_data:
        del _custom_data[key]
        return {"ok": True}
    return {"error": f"Key '{key}' nicht gefunden"}


# ─── WebSocket ──────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_clients.discard(ws)
    except Exception:
        ws_clients.discard(ws)

async def _ws_push_loop():
    while True:
        if ws_clients:
            try:
                # WICHTIG: Blocking Calls in Thread-Pool auslagern!
                # collect_stats() nutzt psutil/Docker SDK (synchron)
                # refresh_led_states() macht HTTP zu HW-Proxy (synchron)
                stats = await asyncio.to_thread(collect_stats)

                # Simulation überschreibt Temperatur systemweit
                # WICHTIG: Kopie erstellen, um den Stats-Cache nicht zu korrumpieren!
                if _sim_temp is not None and stats.get("cpu"):
                    stats = {**stats, "cpu": {**stats["cpu"], "temp": _sim_temp}}

                # System-Daten an LED Engine für reaktive Effekte
                if leds and stats.get("cpu"):
                    leds.update_system_data(
                        stats["cpu"].get("temp", 40),
                        stats["cpu"].get("percent", 10),
                    )

                # LED-States vom HW-Proxy holen (aktuell berechnete Farben)
                if leds:
                    await asyncio.to_thread(leds.refresh_led_states)

                led_state = leds.get_ws_state() if leds else {}
                oled_state = oled.get_ws_state() if oled else {}
                fan_state = fan.get_state() if fan else {}
                payload = json.dumps({
                    "type": "stats",
                    "data": {
                        "stats": stats,
                        "fan": fan_state,
                        "leds": led_state,
                        "oled": oled_state,
                        "custom_data": _custom_data,
                    },
                })
                disconnected = set()
                for ws in ws_clients.copy():
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        disconnected.add(ws)
                ws_clients -= disconnected
            except Exception as e:
                logger.error(f"WS Push: {e}")
        await asyncio.sleep(WS_STATS_INTERVAL)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
