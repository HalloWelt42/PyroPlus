"""
PyroPlus: Datenmodell des OLED-Bereichs.

Alle Modelle, die über die Schnittstelle laufen oder gespeichert werden, stehen
hier. JSON-Feldnamen sind camelCase (Alias), Python-Attribute snake_case.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

W = 128
H = 64

SCHEMA_VERSION = 2


def neue_id() -> str:
    return uuid4().hex


def jetzt() -> datetime:
    return datetime.now(timezone.utc)


class ApiModel(BaseModel):
    """Basis für alle Modelle der Schnittstelle."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


# Aufzählungen

class OledMode(str, Enum):
    """Betriebsart des Displays: auto rotiert, manual zeigt einen festen Bildschirm, off ist dunkel."""
    auto = "auto"
    manual = "manual"
    off = "off"


class Align(str, Enum):
    left = "left"
    center = "center"
    right = "right"


class Rotation(int, Enum):
    r0 = 0
    r90 = 90
    r180 = 180
    r270 = 270


class ValueType(str, Enum):
    """Art des Werts einer Datenquelle; bestimmt die passenden Darstellungsarten."""
    number = "number"
    percent = "percent"
    string = "string"
    time = "time"
    animated = "animated"
    shape = "shape"
    bitmap = "bitmap"


class Tab(str, Enum):
    cpu = "cpu"
    ram = "ram"
    disk = "disk"
    net = "net"
    fan = "fan"
    zeit = "zeit"
    wetter = "wetter"
    text = "text"
    layout = "layout"


class DisplayMode(str, Enum):
    """Darstellungsart eines Widgets. Größen sind Optionen, keine eigenen Arten."""
    text = "text"
    text_invertiert = "text_invertiert"
    text_rahmen = "text_rahmen"
    balken = "balken"
    balken_label = "balken_label"
    balken_label_in = "balken_label_in"
    gauge = "gauge"
    sparkline = "sparkline"
    laufschrift = "laufschrift"
    fan_icon = "fan_icon"
    fan_icon_rpm = "fan_icon_rpm"
    linie_h = "linie_h"
    linie_v = "linie_v"
    rahmen = "rahmen"
    block = "block"
    section = "section"
    bitmap = "bitmap"


class ScreenKind(str, Enum):
    """Bildschirmart: frei zusammengestellt aus Widgets oder ein fertiger Wetterbildschirm."""
    widgets = "widgets"
    weather_compact = "weather_compact"
    weather_hourly = "weather_hourly"
    weather_daily = "weather_daily"


# Widgets und Bildschirme

class WidgetOpts(ApiModel):
    """Fachliche Optionen eines Widgets. Welche davon gelten, sagt die Darstellungsart im Katalog."""

    scale_x: int = Field(1, ge=1, le=8, description="Horizontale Vergrößerung der Schrift")
    scale_y: Optional[int] = Field(None, ge=1, le=8, description="Vertikale Vergrößerung; leer = wie horizontal")
    prefix: str = Field("", max_length=40)
    suffix: str = Field("", max_length=40)
    decimals: Optional[int] = Field(None, ge=0, le=3, description="Dezimalstellen; leer = Vorgabe der Quelle")
    thousands: bool = Field(False, description="Tausendertrenner (1.234)")
    invert: bool = False
    border: bool = False
    align: Align = Align.left
    box_w: int = Field(0, ge=0, le=W, description="Breite der Ausrichtungsbox; 0 = Textbreite")
    width: Optional[int] = Field(None, ge=1, le=W)
    height: Optional[int] = Field(None, ge=1, le=H)
    radius: Optional[int] = Field(None, ge=4, le=32)
    size: Optional[int] = Field(None, ge=8, le=48)
    text: Optional[str] = Field(None, max_length=500)
    rotate: Rotation = Rotation.r0
    location_id: Optional[str] = Field(None, description="Wetterort; leer = Vorgabeort")
    bitmap: Optional[str] = Field(None, description="Base64, Bits zeilenweise gepackt, width x height")

    @model_validator(mode="before")
    @classmethod
    def _altes_format(cls, daten: Any) -> Any:
        """Nimmt Schlüssel des alten Editors an und wirft Editor-Hilfswerte weg."""
        if not isinstance(daten, dict):
            return daten
        bereinigt: dict[str, Any] = {}
        for schluessel, wert in daten.items():
            if schluessel.startswith("_"):
                continue
            if schluessel == "tsep":
                bereinigt["thousands"] = bool(wert)
            elif schluessel == "scale" and "scaleX" not in daten and "scale_x" not in daten:
                bereinigt["scaleX"] = wert
                bereinigt.setdefault("scaleY", wert)
            elif schluessel == "decimals" and wert is not None and int(wert) < 0:
                bereinigt["decimals"] = None
            elif schluessel == "rotate" and wert not in (0, 90, 180, 270):
                bereinigt["rotate"] = 0
            else:
                bereinigt[schluessel] = wert
        return bereinigt

    @property
    def scale_y_effektiv(self) -> int:
        return self.scale_y if self.scale_y is not None else self.scale_x


class Widget(ApiModel):
    id: str = Field(default_factory=neue_id)
    source: str = Field(min_length=1, max_length=64, description="Datenquelle, z. B. cpu.temp")
    display: DisplayMode
    x: int = Field(0, ge=0, le=W - 1)
    y: int = Field(0, ge=0, le=H - 1)
    name: str = Field("", max_length=60)
    opts: WidgetOpts = Field(default_factory=WidgetOpts)


class Screen(ApiModel):
    id: str = Field(default_factory=neue_id)
    name: str = Field("", max_length=60)
    kind: ScreenKind = ScreenKind.widgets
    widgets: list[Widget] = Field(default_factory=list)
    location_id: Optional[str] = Field(None, description="Wetterort für Wetterbildschirme")
    enabled: bool = Field(True, description="Nimmt an der Rotation teil")
    duration: Optional[int] = Field(None, ge=1, le=3600, description="Anzeigedauer in Sekunden; leer = Rotationsintervall")


class OledSettings(ApiModel):
    schema_version: int = SCHEMA_VERSION
    mode: OledMode = OledMode.auto
    brightness: int = Field(200, ge=0, le=255)
    rotation_interval: int = Field(10, ge=1, le=3600, description="Sekunden je Bildschirm bei Rotation")
    current_screen_id: Optional[str] = None
    screens: list[Screen] = Field(default_factory=list)

    def screen_by_id(self, screen_id: Optional[str]) -> Optional[Screen]:
        for screen in self.screens:
            if screen.id == screen_id:
                return screen
        return None


class OledSettingsPatch(ApiModel):
    """Teilweise Änderung der Einstellungen; nur gesetzte Felder werden übernommen."""
    mode: Optional[OledMode] = None
    brightness: Optional[int] = Field(None, ge=0, le=255)
    rotation_interval: Optional[int] = Field(None, ge=1, le=3600)
    current_screen_id: Optional[str] = None


class ScreenOrder(ApiModel):
    ids: list[str]


# Vorlagen und Profile

class WidgetPreset(ApiModel):
    """Gespeichertes Widget zum späteren Einbauen."""
    id: str = Field(default_factory=neue_id)
    name: str = Field(min_length=1, max_length=60)
    source: str = Field(min_length=1, max_length=64)
    display: DisplayMode
    opts: WidgetOpts = Field(default_factory=WidgetOpts)
    created: datetime = Field(default_factory=jetzt)


class Profile(ApiModel):
    """Benannter Schnappschuss aller Bildschirme."""
    id: str = Field(default_factory=neue_id)
    name: str = Field(min_length=1, max_length=60)
    created: datetime = Field(default_factory=jetzt)
    screens: list[Screen] = Field(default_factory=list)
    rotation_interval: int = Field(10, ge=1, le=3600)


class ProfileCreate(ApiModel):
    name: str = Field(min_length=1, max_length=60)


# Wetter

class WeatherLocation(ApiModel):
    id: str = Field(default_factory=neue_id)
    name: str = Field(min_length=1, max_length=60)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    country: str = Field("", max_length=60)


class WeatherLocationCreate(ApiModel):
    name: str = Field(min_length=1, max_length=60)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    country: str = Field("", max_length=60)


class WeatherSettings(ApiModel):
    locations: list[WeatherLocation] = Field(default_factory=list)
    default_location_id: Optional[str] = None

    def location_by_id(self, location_id: Optional[str]) -> Optional[WeatherLocation]:
        for ort in self.locations:
            if ort.id == location_id:
                return ort
        return None

    def default_location(self) -> Optional[WeatherLocation]:
        ort = self.location_by_id(self.default_location_id)
        if ort is None and self.locations:
            return self.locations[0]
        return ort


class GeocodeHit(ApiModel):
    name: str
    country: str = ""
    admin: str = ""
    lat: float
    lon: float


class WeatherLocationState(ApiModel):
    """Ort plus Zustand des Zwischenspeichers."""
    location: WeatherLocation
    is_default: bool
    fetched_at: Optional[datetime] = None
    ok: bool = False
    summary: str = ""


# Katalog

class TabInfo(ApiModel):
    id: Tab
    label: str


class SourceInfo(ApiModel):
    id: str
    tab: Tab
    label: str
    unit: str = ""
    value_type: ValueType
    description: str = ""
    group: str = Field("", description="Gruppenüberschrift, z. B. Name des Laufwerks")
    uses_location: bool = Field(False, description="Quelle hängt an einem Wetterort")
    example: str = Field("", description="Aktueller Wert als Beispiel")


class ModeVariant(ApiModel):
    id: str
    label: str
    opts: WidgetOpts


class DisplayModeInfo(ApiModel):
    id: DisplayMode
    label: str
    description: str = ""
    for_types: list[ValueType]
    fields: list[str] = Field(description="Optionen, die bei dieser Darstellungsart gelten (camelCase)")
    defaults: WidgetOpts
    variants: list[ModeVariant] = Field(default_factory=list)


class Catalog(ApiModel):
    width: int = W
    height: int = H
    tabs: list[TabInfo]
    sources: list[SourceInfo]
    modes: list[DisplayModeInfo]


# Rendern

class WidgetBox(ApiModel):
    id: str
    x: int
    y: int
    w: int
    h: int


class RenderRequest(ApiModel):
    screen: Screen
    simulate: dict[str, float] = Field(default_factory=dict, description="Quelle -> simulierter Zahlenwert")


class RenderResponse(ApiModel):
    image_base64: str
    boxes: list[WidgetBox]
    width: int = W
    height: int = H


# Zustand

class OledLive(ApiModel):
    """Leichter Live-Zustand für den WebSocket."""
    mode: OledMode
    brightness: int
    rotation_interval: int
    current_screen_id: Optional[str]
    screens_version: int
    preview: Optional[str] = None


class OledState(OledLive):
    available: bool
    hardware: bool
    width: int = W
    height: int = H
    screens: list[Screen]
    weather_ok: bool = False
    version: str = ""


# Austausch

class OledBundle(ApiModel):
    """Vollständiger Export des OLED-Bereichs."""
    app_version: str = ""
    exported: datetime = Field(default_factory=jetzt)
    settings: OledSettings
    presets: list[WidgetPreset] = Field(default_factory=list)
    profiles: list[Profile] = Field(default_factory=list)
    weather: WeatherSettings = Field(default_factory=WeatherSettings)


class ImportResult(ApiModel):
    screens: int
    presets: int
    profiles: int
    locations: int
