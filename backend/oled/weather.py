"""
PyroPlus: Wetterdaten für mehrere Orte.

Ein Anbieter (Protocol) liefert einen Bericht je Ort. Der Dienst hält die Orte,
den Zwischenspeicher und entscheidet, wann nachgeladen wird. Standardanbieter
ist Open-Meteo (ohne Schlüssel). Ein anderer Anbieter wird nur hier getauscht.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Optional, Protocol

import httpx
from pydantic import BaseModel, Field

from oled.models import GeocodeHit, WeatherLocation, WeatherLocationState, WeatherSettings

logger = logging.getLogger("oled.weather")


class WeatherCurrent(BaseModel):
    temperature: Optional[float] = None
    apparent_temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    wind_gusts: Optional[float] = None
    cloud_cover: Optional[float] = None
    pressure: Optional[float] = None
    pressure_msl: Optional[float] = None
    precipitation: Optional[float] = None
    weather_code: Optional[int] = None
    condition_text: str = "--"
    is_day: bool = True
    sunrise: str = ""
    sunset: str = ""


class WeatherHour(BaseModel):
    time: str = ""
    temperature: Optional[float] = None
    weather_code: Optional[int] = None
    condition_text: str = ""
    precipitation_probability: Optional[float] = None


class WeatherDay(BaseModel):
    date: str = ""
    temperature_max: Optional[float] = None
    temperature_min: Optional[float] = None
    weather_code: Optional[int] = None
    condition_text: str = ""
    sunrise: str = ""
    sunset: str = ""
    precipitation_probability: Optional[float] = None


class WeatherReport(BaseModel):
    location_id: str
    location_name: str
    current: WeatherCurrent = Field(default_factory=WeatherCurrent)
    hourly: list[WeatherHour] = Field(default_factory=list)
    daily: list[WeatherDay] = Field(default_factory=list)
    fetched_at: float = 0.0


def wmo_text(code: Optional[int]) -> str:
    """WMO-Wettercode als kurzer deutscher Text (passend zur 5x7-Schrift)."""
    if code is None:
        return "--"
    if code == 0:
        return "Klar"
    if code <= 3:
        return "Bewölkt"
    if code <= 49:
        return "Nebel"
    if code <= 59:
        return "Niesel"
    if code <= 69:
        return "Regen"
    if code <= 79:
        return "Schnee"
    if code <= 84:
        return "Schauer"
    return "Gewitter"


class WeatherProvider(Protocol):
    def fetch(self, location: WeatherLocation) -> WeatherReport: ...
    def geocode(self, query: str) -> list[GeocodeHit]: ...


class OpenMeteoProvider:
    """Open-Meteo: Vorhersage und Ortssuche, ohne Schlüssel."""

    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    def fetch(self, location: WeatherLocation) -> WeatherReport:
        params = {
            "latitude": location.lat,
            "longitude": location.lon,
            "current": ",".join([
                "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "weather_code",
                "cloud_cover", "surface_pressure", "pressure_msl", "precipitation", "is_day",
            ]),
            "hourly": "temperature_2m,weather_code,precipitation_probability",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_probability_max",
            "forecast_days": 7,
            "timezone": "auto",
        }
        antwort = httpx.get(self.FORECAST_URL, params=params, timeout=self.timeout)
        antwort.raise_for_status()
        daten = antwort.json()
        return self._parse(location, daten)

    def _parse(self, location: WeatherLocation, daten: dict) -> WeatherReport:
        c = daten.get("current", {}) or {}
        current = WeatherCurrent(
            temperature=c.get("temperature_2m"),
            apparent_temperature=c.get("apparent_temperature"),
            humidity=c.get("relative_humidity_2m"),
            wind_speed=c.get("wind_speed_10m"),
            wind_direction=c.get("wind_direction_10m"),
            wind_gusts=c.get("wind_gusts_10m"),
            cloud_cover=c.get("cloud_cover"),
            pressure=c.get("surface_pressure"),
            pressure_msl=c.get("pressure_msl"),
            precipitation=c.get("precipitation"),
            weather_code=c.get("weather_code"),
            condition_text=wmo_text(c.get("weather_code")),
            is_day=bool(c.get("is_day", 1)),
        )

        hourly: list[WeatherHour] = []
        h = daten.get("hourly", {}) or {}
        zeiten = h.get("time", []) or []
        jetzt_stunde = datetime.now().hour
        for i, t in enumerate(zeiten):
            try:
                stunde = int(str(t)[-5:-3])
            except ValueError:
                stunde = i
            if stunde < jetzt_stunde and not hourly:
                continue
            hourly.append(WeatherHour(
                time=str(t),
                temperature=_at(h.get("temperature_2m"), i),
                weather_code=_at(h.get("weather_code"), i),
                condition_text=wmo_text(_at(h.get("weather_code"), i)),
                precipitation_probability=_at(h.get("precipitation_probability"), i),
            ))
            if len(hourly) >= 24:
                break

        daily: list[WeatherDay] = []
        d = daten.get("daily", {}) or {}
        for i, datum in enumerate(d.get("time", []) or []):
            sr = str(_at(d.get("sunrise"), i) or "")
            ss = str(_at(d.get("sunset"), i) or "")
            daily.append(WeatherDay(
                date=str(datum),
                temperature_max=_at(d.get("temperature_2m_max"), i),
                temperature_min=_at(d.get("temperature_2m_min"), i),
                weather_code=_at(d.get("weather_code"), i),
                condition_text=wmo_text(_at(d.get("weather_code"), i)),
                sunrise=sr[-5:] if len(sr) >= 5 else sr,
                sunset=ss[-5:] if len(ss) >= 5 else ss,
                precipitation_probability=_at(d.get("precipitation_probability_max"), i),
            ))
        if daily:
            current.sunrise = daily[0].sunrise
            current.sunset = daily[0].sunset

        return WeatherReport(location_id=location.id, location_name=location.name,
                             current=current, hourly=hourly, daily=daily, fetched_at=time.time())

    def geocode(self, query: str) -> list[GeocodeHit]:
        antwort = httpx.get(self.GEOCODE_URL, params={"name": query, "count": 8, "language": "de"},
                            timeout=self.timeout)
        antwort.raise_for_status()
        treffer: list[GeocodeHit] = []
        for r in antwort.json().get("results", []) or []:
            treffer.append(GeocodeHit(name=str(r.get("name", "")), country=str(r.get("country", "")),
                                      admin=str(r.get("admin1", "")),
                                      lat=float(r.get("latitude", 0.0)), lon=float(r.get("longitude", 0.0))))
        return treffer


def _at(liste: Optional[list], index: int):
    if liste is None or index >= len(liste):
        return None
    return liste[index]


class WeatherService:
    """Orte, Zwischenspeicher und Nachladen. Thread-sicher."""

    def __init__(self, provider: WeatherProvider, settings: WeatherSettings,
                 refresh_seconds: int = 600) -> None:
        self.provider = provider
        self.settings = settings
        self.refresh_seconds = refresh_seconds
        self._reports: dict[str, WeatherReport] = {}
        self._failed_at: dict[str, float] = {}
        self._lock = threading.Lock()

    # Orte

    def report_for(self, location_id: Optional[str]) -> Optional[WeatherReport]:
        """Bericht für einen Ort; leer = Vorgabeort."""
        ort = self.settings.location_by_id(location_id) or self.settings.default_location()
        if ort is None:
            return None
        with self._lock:
            return self._reports.get(ort.id)

    def states(self) -> list[WeatherLocationState]:
        ergebnis: list[WeatherLocationState] = []
        vorgabe = self.settings.default_location()
        with self._lock:
            for ort in self.settings.locations:
                bericht = self._reports.get(ort.id)
                zusammenfassung = ""
                if bericht and bericht.current.temperature is not None:
                    zusammenfassung = f"{bericht.current.temperature:.1f} °C, {bericht.current.condition_text}"
                ergebnis.append(WeatherLocationState(
                    location=ort,
                    is_default=bool(vorgabe and vorgabe.id == ort.id),
                    fetched_at=datetime.fromtimestamp(bericht.fetched_at) if bericht else None,
                    ok=bericht is not None,
                    summary=zusammenfassung,
                ))
        return ergebnis

    def any_ok(self) -> bool:
        with self._lock:
            return bool(self._reports)

    def forget(self, location_id: str) -> None:
        with self._lock:
            self._reports.pop(location_id, None)
            self._failed_at.pop(location_id, None)

    # Nachladen

    def refresh_due(self, force: bool = False) -> None:
        """Lädt alle Orte nach, deren Bericht älter als refresh_seconds ist."""
        jetzt = time.time()
        for ort in list(self.settings.locations):
            with self._lock:
                bericht = self._reports.get(ort.id)
                fehlgeschlagen = self._failed_at.get(ort.id, 0.0)
            frisch = bericht is not None and jetzt - bericht.fetched_at < self.refresh_seconds
            kuerzlich_fehlgeschlagen = jetzt - fehlgeschlagen < 60
            if force or (not frisch and not kuerzlich_fehlgeschlagen):
                self.refresh_location(ort)

    def refresh_location(self, ort: WeatherLocation) -> bool:
        try:
            bericht = self.provider.fetch(ort)
        except Exception as fehler:
            logger.error(f"Wetter {ort.name}: {fehler}")
            with self._lock:
                self._failed_at[ort.id] = time.time()
            return False
        with self._lock:
            self._reports[ort.id] = bericht
            self._failed_at.pop(ort.id, None)
        logger.info(f"Wetter {ort.name}: {bericht.current.temperature} °C, {bericht.current.condition_text}")
        return True

    def geocode(self, query: str) -> list[GeocodeHit]:
        return self.provider.geocode(query)
