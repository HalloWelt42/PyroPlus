"""
PyroPlus: FastAPI-Backend.

Swagger-UI: http://host:8071/docs

Bereiche: System, Lüfter, LEDs, OLED (eigener Router unter oled/api.py),
Schnellzugriff, Fremddaten, WebSocket. Alle Zustände gehören dem Backend.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

import hw_client
from config import (
    API_TOKEN, APP_NAME, DATA_DIR, HOST, OLED_RENDER_INTERVAL, PORT, TOKEN_FILE, VERSION,
    VERSION_VOLL, WEATHER_REFRESH_SECONDS, WS_STATS_INTERVAL,
)
from effects.engine import LEDEngine
from fan.controller import FanController
from oled.api import router as oled_router
from oled.engine import OledEngine
from oled.store import OledStore
from oled.weather import OpenMeteoProvider, WeatherService
from stats import collect_stats

logger = logging.getLogger("api")

fan: Optional[FanController] = None
oled: Optional[OledEngine] = None
leds: Optional[LEDEngine] = None
ws_clients: set[WebSocket] = set()
_custom_data: dict[str, dict] = {}
_sim_temp: float | None = None


# Token-Prüfung

OPEN_PATHS = {"/api/token", "/docs", "/openapi.json", "/redoc", "/health"}


class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path
        if path in OPEN_PATHS or path.startswith("/ws"):
            return await call_next(request)
        token = request.headers.get("X-API-Token") or request.query_params.get("token")
        if token != API_TOKEN:
            return JSONResponse(status_code=401, content={"error": "Ungültiger API-Token"})
        return await call_next(request)


def build_oled_engine() -> OledEngine:
    store = OledStore(DATA_DIR)
    store.ensure_initialised()
    weather = WeatherService(OpenMeteoProvider(), store.load_weather(), WEATHER_REFRESH_SECONDS)
    return OledEngine(store, weather, collect_stats,
                      fan_state_provider=lambda: fan.get_state() if fan else {},
                      render_interval=OLED_RENDER_INTERVAL, app_version=VERSION)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global fan, oled, leds
    logger.info(f"=== {APP_NAME} {VERSION_VOLL} startet ===")
    logger.info(f"API-Token: {API_TOKEN[:8]}... (gespeichert in {TOKEN_FILE})")
    logger.info(f"Hardware-Proxy: {hw_client.health()}")

    fan = FanController()
    fan.start()
    oled = build_oled_engine()
    app.state.oled = oled
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
app.include_router(oled_router)


# Modelle

class ColorModel(BaseModel):
    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)


class FanManualSpeed(BaseModel):
    speed: float = Field(ge=0.0, le=100.0)


class FanFineSettings(BaseModel):
    hysteresis: Optional[float] = Field(None, ge=0.5, le=10.0)
    threshold_on: Optional[float] = Field(None, ge=35, le=80)
    threshold_off: Optional[float] = Field(None, ge=30, le=75)
    case_profile: Optional[str] = None


class CurvePoint(BaseModel):
    temp: float = Field(ge=20.0, le=85.0)
    speed: float = Field(ge=0.0, le=100.0)


class FanCurveRequest(BaseModel):
    points: list[CurvePoint] = Field(min_length=2)


class LEDIndividualColor(BaseModel):
    index: int = Field(ge=0, le=3)
    color: ColorModel


class CustomDataEntry(BaseModel):
    label: str = Field(max_length=100, description="Anzeigename")
    value: str = Field(max_length=1000, description="Wert (Text oder Zahl)")
    unit: str = Field("", max_length=20, description="Einheit (optional)")
    icon: str = Field("", max_length=8, description="Symbol (optional)")
    category: str = Field("custom", max_length=50, description="Kategorie")
    url: str = Field("", max_length=500, description="Verweis (optional)")


class SimulateTemp(BaseModel):
    temp: Optional[float] = Field(None, ge=0, le=120, description="Leer = Simulation beenden")


class DiskConfigModel(BaseModel):
    monitored_mounts: list[str]


# System

@app.get("/api/token", tags=["System"], summary="API-Token abrufen (ohne Anmeldung)")
def get_api_token() -> dict[str, str]:
    """Die Oberfläche holt den Token beim Start."""
    return {"token": API_TOKEN, "info": "Sende diesen Token als X-API-Token Header"}


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "version": VERSION, "voll": VERSION_VOLL}


@app.get("/api/info", tags=["System"])
def get_info() -> dict[str, str]:
    return {"app": APP_NAME, "version": VERSION, "voll": VERSION_VOLL}


@app.get("/api/stats", tags=["System"])
def get_stats() -> dict[str, Any]:
    return collect_stats()


@app.get("/api/state", tags=["System"], summary="Kompletter Systemstatus")
def get_full_state() -> dict[str, Any]:
    if leds:
        leds.refresh_led_states()
    return {
        "version": VERSION,
        "voll": VERSION_VOLL,
        "hw_proxy": hw_client.health(),
        "fan": fan.get_state() if fan else {},
        "oled": _oled_payload(),
        "leds": leds.get_state() if leds else {},
        "stats": _stats_with_simulation(collect_stats()),
        "custom_data": _custom_data,
    }


def _oled_payload() -> dict[str, Any]:
    """Vollständiger OLED-Zustand für den Gesamtstatus."""
    if oled is None:
        return {}
    return oled.get_state().model_dump(mode="json", by_alias=True)


def _oled_live() -> dict[str, Any]:
    """Leichter Live-Zustand für den WebSocket; die Bildschirme holt die Oberfläche bei Versionswechsel."""
    if oled is None:
        return {}
    return oled.get_live().model_dump(mode="json", by_alias=True)


def _stats_with_simulation(stats: dict[str, Any]) -> dict[str, Any]:
    if _sim_temp is not None and stats.get("cpu"):
        return {**stats, "cpu": {**stats["cpu"], "temp": _sim_temp}}
    return stats


# Lüfter

@app.get("/api/fan", tags=["Lüfter"])
def fan_get_state() -> dict[str, Any]:
    return fan.get_state() if fan else {}


@app.post("/api/fan/mode/{mode}", tags=["Lüfter"], summary="Lüfter-Modus: auto | manual | off")
def fan_set_mode(mode: str) -> dict[str, Any]:
    if mode not in ("auto", "manual", "off"):
        return {"error": "Ungültiger Modus. Erlaubt: auto, manual, off"}
    fan.set_mode(mode)
    return {"ok": True, "mode": mode}


@app.post("/api/fan/profile/{name}", tags=["Lüfter"], summary="Profil: silent | balanced | performance | custom")
def fan_set_profile(name: str) -> dict[str, Any]:
    return fan.set_profile(name)


@app.post("/api/fan/curve", tags=["Lüfter"], summary="Eigene Temperaturkurve setzen")
def fan_set_curve(req: FanCurveRequest) -> dict[str, Any]:
    fan.set_curve([{"temp": p.temp, "speed": p.speed} for p in req.points])
    return {"ok": True, **fan.get_state()}


@app.post("/api/fan/manual-speed", tags=["Lüfter"], summary="Manuelle Geschwindigkeit (0 bis 100 %)")
def fan_set_manual_speed(req: FanManualSpeed) -> dict[str, Any]:
    fan.set_manual_speed(req.speed)
    return {"ok": True, "speed": req.speed}


@app.post("/api/fan/settings", tags=["Lüfter"], summary="Feineinstellungen (Hysterese, Gehäuselüfter)")
def fan_set_fine_settings(req: FanFineSettings) -> dict[str, Any]:
    fan.set_fine_settings(hysteresis=req.hysteresis, threshold_on=req.threshold_on,
                          threshold_off=req.threshold_off, case_profile=req.case_profile)
    return {"ok": True, **fan.get_state()}


@app.get("/api/fan/duty-for-temp", tags=["Lüfter"], summary="PWM-Leistung für eine Temperatur")
def fan_duty_for_temp(temp: float = Query()) -> dict[str, float]:
    return {"temp": temp, "duty": round(fan.get_duty_for_temp(temp), 1)}


# Simulation

@app.post("/api/simulate/temp", tags=["Simulation"], summary="Temperatur simulieren (wirkt auf LEDs und Lüfter)")
def simulate_temp(req: SimulateTemp) -> dict[str, Any]:
    global _sim_temp
    if req.temp is None:
        _sim_temp = None
        echte_temp = hw_client.get_temp()
        if fan:
            fan.sim_temp = None
            fan.current_temp = echte_temp
        if leds:
            leds.update_system_data(echte_temp, leds.cpu_load)
        return {"ok": True, "simulation": False}
    _sim_temp = float(req.temp)
    if leds:
        leds.update_system_data(_sim_temp, leds.cpu_load)
    if fan:
        fan.sim_temp = _sim_temp
    return {"ok": True, "simulation": True, "temp": _sim_temp}


# LEDs

@app.get("/api/leds", tags=["WS2812B LEDs"])
def leds_get_state() -> dict[str, Any]:
    return leds.get_state() if leds else {}


@app.get("/api/leds/effects", tags=["WS2812B LEDs"], summary="Alle verfügbaren LED-Effekte")
def leds_get_effects() -> dict[str, Any]:
    return leds.get_effects_list()


@app.post("/api/leds/effect/{name}", tags=["WS2812B LEDs"], summary="Effekt aktivieren ('off' schaltet aus)")
def leds_set_effect(name: str) -> dict[str, Any]:
    if name != "off" and name not in leds.EFFECTS:
        return {"error": f"Unbekannter Effekt: {name}"}
    leds.set_effect(name)
    return {"ok": True, "effect": name}


@app.post("/api/leds/color", tags=["WS2812B LEDs"], summary="Primärfarbe (RGB)")
def leds_set_color(color: ColorModel) -> dict[str, Any]:
    leds.set_color(color.r, color.g, color.b)
    return {"ok": True, "color": leds.color}


@app.post("/api/leds/color2", tags=["WS2812B LEDs"], summary="Sekundärfarbe (RGB)")
def leds_set_color2(color: ColorModel) -> dict[str, Any]:
    leds.set_color2(color.r, color.g, color.b)
    return {"ok": True, "color2": leds.color2}


@app.post("/api/leds/brightness/{value}", tags=["WS2812B LEDs"], summary="Helligkeit (1 bis 1000)")
def leds_set_brightness(value: int) -> dict[str, Any]:
    leds.set_brightness(value)
    return {"ok": True, "brightness": leds.brightness}


@app.post("/api/leds/speed/{value}", tags=["WS2812B LEDs"], summary="Effekt-Geschwindigkeit (1 bis 1000)")
def leds_set_speed(value: float) -> dict[str, Any]:
    leds.set_speed(value)
    return {"ok": True, "speed": leds.speed}


@app.post("/api/leds/individual", tags=["WS2812B LEDs"], summary="Einzelne LED (Index 0 bis 3)")
def leds_set_individual(req: LEDIndividualColor) -> dict[str, Any]:
    leds.set_individual_color(req.index, req.color.r, req.color.g, req.color.b)
    return {"ok": True, "index": req.index, "color": leds.individual_colors[req.index]}


@app.post("/api/leds/individual-mode/{enabled}", tags=["WS2812B LEDs"])
def leds_set_individual_mode(enabled: bool) -> dict[str, Any]:
    leds.individual_mode = enabled
    hw_client.leds_config(individual_mode=enabled)
    leds._save_settings()
    return {"ok": True, "individual_mode": enabled}


# Schnellzugriff

@app.post("/api/quick/leds-off", tags=["Schnellzugriff"])
def quick_leds_off() -> dict[str, Any]:
    leds.set_effect("off")
    return {"ok": True, "effect": "off"}


@app.post("/api/quick/leds-on", tags=["Schnellzugriff"])
def quick_leds_on() -> dict[str, Any]:
    last = leds.effect if leds.effect and leds.effect != "off" else "static"
    leds.set_effect(last)
    return {"ok": True, "effect": leds.effect}


@app.post("/api/quick/oled-off", tags=["Schnellzugriff"])
def quick_oled_off() -> dict[str, Any]:
    from oled.models import OledMode, OledSettingsPatch
    oled.patch_settings(OledSettingsPatch(mode=OledMode.off))
    return {"ok": True, "mode": "off"}


@app.post("/api/quick/oled-on", tags=["Schnellzugriff"])
def quick_oled_on() -> dict[str, Any]:
    from oled.models import OledMode, OledSettingsPatch
    oled.patch_settings(OledSettingsPatch(mode=OledMode.auto))
    return {"ok": True, "mode": "auto"}


@app.post("/api/quick/fan-auto", tags=["Schnellzugriff"])
def quick_fan_auto() -> dict[str, Any]:
    fan.set_mode("auto")
    return {"ok": True, "mode": "auto"}


@app.post("/api/quick/fan-off", tags=["Schnellzugriff"])
def quick_fan_off() -> dict[str, Any]:
    fan.set_mode("off")
    return {"ok": True, "mode": "off"}


# Laufwerke

@app.get("/api/disks/all", tags=["System"], summary="Alle erkannten Laufwerke")
def get_all_disks() -> dict[str, Any]:
    from stats import get_all_disks as _all
    return {"disks": _all()}


@app.get("/api/disks/config", tags=["System"], summary="Überwachte Laufwerke")
def get_disk_config() -> dict[str, Any]:
    from stats import get_disk_config as _cfg
    return _cfg()


@app.post("/api/disks/config", tags=["System"], summary="Überwachte Laufwerke setzen")
def set_disk_config(req: DiskConfigModel) -> dict[str, Any]:
    from stats import set_disk_config as _set
    _set({"monitored_mounts": req.monitored_mounts})
    return {"ok": True, "monitored_mounts": req.monitored_mounts}


# Fremddaten

@app.get("/api/custom", tags=["Fremddaten"], summary="Alle registrierten Fremddaten")
def get_custom_data() -> dict[str, Any]:
    return {"entries": _custom_data, "count": len(_custom_data)}


@app.get("/api/custom/{key}", tags=["Fremddaten"])
def get_custom_entry(key: str) -> dict[str, Any]:
    if key not in _custom_data:
        return {"error": f"Schlüssel '{key}' nicht gefunden"}
    return _custom_data[key]


@app.put("/api/custom/{key}", tags=["Fremddaten"], summary="Fremddaten registrieren oder aktualisieren")
def put_custom_entry(key: str, entry: CustomDataEntry) -> dict[str, Any]:
    """Externe Skripte können per PUT eigene Werte einblenden."""
    _custom_data[key] = {"key": key, **entry.model_dump(),
                         "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    return {"ok": True, "key": key}


@app.delete("/api/custom/{key}", tags=["Fremddaten"])
def delete_custom_entry(key: str) -> dict[str, Any]:
    if key in _custom_data:
        del _custom_data[key]
        return {"ok": True}
    return {"error": f"Schlüssel '{key}' nicht gefunden"}


# WebSocket

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    ws_clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_clients.discard(ws)
    except Exception:
        ws_clients.discard(ws)


async def _ws_push_loop() -> None:
    while True:
        if ws_clients:
            try:
                stats = _stats_with_simulation(await asyncio.to_thread(collect_stats))
                if leds and stats.get("cpu"):
                    leds.update_system_data(stats["cpu"].get("temp", 40), stats["cpu"].get("percent", 10))
                    await asyncio.to_thread(leds.refresh_led_states)
                payload = json.dumps({
                    "type": "stats",
                    "data": {
                        "stats": stats,
                        "fan": fan.get_state() if fan else {},
                        "leds": leds.get_ws_state() if leds else {},
                        "oled": _oled_live(),
                        "custom_data": _custom_data,
                    },
                })
                getrennt: set[WebSocket] = set()
                for ws in ws_clients.copy():
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        getrennt.add(ws)
                ws_clients.difference_update(getrennt)
            except Exception as fehler:
                logger.error(f"WebSocket-Push: {fehler}")
        await asyncio.sleep(WS_STATS_INTERVAL)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
