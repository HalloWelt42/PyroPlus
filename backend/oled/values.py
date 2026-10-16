"""
PyroPlus: Datenquellen und Wertauflösung.

Jede Datenquelle ist hier genau einmal registriert: Kennung, Reiter, Beschriftung,
Einheit, Wertart und die Funktion, die den Wert aus dem Kontext liest. Der
Katalog für die Oberfläche wird aus dieser Registrierung erzeugt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from oled.models import Tab, ValueType, WidgetOpts
from oled.weather import WeatherReport

TZ = ZoneInfo("Europe/Berlin")

TAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
TAGE_LANG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


# Typisierter Schnappschuss der Systemwerte

class CpuStats(BaseModel):
    model_config = ConfigDict(extra="ignore")
    temp: float = 0.0
    temp_min: float = 0.0
    temp_max: float = 0.0
    percent: float = 0.0
    cores: int = 4


class RamStats(BaseModel):
    model_config = ConfigDict(extra="ignore")
    total_gb: float = 0.0
    used_gb: float = 0.0
    available_gb: float = 0.0
    percent: float = 0.0


class DiskStats(BaseModel):
    model_config = ConfigDict(extra="ignore")
    label: str = ""
    mount: str = ""
    total_gb: float = 0.0
    used_gb: float = 0.0
    available_gb: float = 0.0
    percent: float = 0.0
    model: str = ""
    fstype: str = ""


class NetStats(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ip: str = "0.0.0.0"
    interface: str = ""
    hostname: str = ""
    rx_bytes_sec: float = 0.0
    tx_bytes_sec: float = 0.0


class FanStats(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rpm: int = 0
    pwm_level: int = 0
    level_name: str = "Aus"
    current_duty: float = 0.0
    case_on: bool = False
    mode: str = ""


class UptimeStats(BaseModel):
    model_config = ConfigDict(extra="ignore")
    seconds: int = 0
    formatted: str = "0m"


class StatsSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cpu: CpuStats = Field(default_factory=CpuStats)
    ram: RamStats = Field(default_factory=RamStats)
    disks: list[DiskStats] = Field(default_factory=list)
    network: NetStats = Field(default_factory=NetStats)
    fan: FanStats = Field(default_factory=FanStats)
    uptime: UptimeStats = Field(default_factory=UptimeStats)
    history: dict[str, list[float]] = Field(default_factory=dict)

    def disk(self, index: int) -> DiskStats:
        if 0 <= index < len(self.disks):
            return self.disks[index]
        return DiskStats()


# Wert und Kontext

@dataclass
class Value:
    """Aufgelöster Wert: Text für die Anzeige, Zahl und Prozent für Balken und Gauge."""
    text: str = ""
    number: Optional[float] = None
    percent: Optional[float] = None

    @property
    def percent_or_number(self) -> float:
        if self.percent is not None:
            return max(0.0, min(100.0, self.percent))
        if self.number is not None:
            return max(0.0, min(100.0, self.number))
        return 0.0


@dataclass
class ValueContext:
    stats: StatsSnapshot
    now: datetime
    opts: WidgetOpts = field(default_factory=WidgetOpts)
    weather: Optional[WeatherReport] = None
    disk_index: int = 0
    simulate: dict[str, float] = field(default_factory=dict)

    @property
    def history(self) -> dict[str, list[float]]:
        return self.stats.history


Resolver = Callable[[ValueContext], Value]


@dataclass(frozen=True)
class SourceDef:
    id: str
    tab: Tab
    label: str
    value_type: ValueType
    resolver: Resolver
    unit: str = ""
    description: str = ""
    decimals: int = 0
    per_disk: bool = False
    uses_location: bool = False


_SOURCES: dict[str, SourceDef] = {}
_DISK_SUFFIX = re.compile(r"^(disk\.\w+)\.(\d+)$")


def source(id: str, tab: Tab, label: str, value_type: ValueType, unit: str = "",
           description: str = "", decimals: int = 0, per_disk: bool = False,
           uses_location: bool = False) -> Callable[[Resolver], Resolver]:
    """Registriert eine Datenquelle."""
    def wrap(fn: Resolver) -> Resolver:
        _SOURCES[id] = SourceDef(id, tab, label, value_type, fn, unit, description,
                                 decimals, per_disk, uses_location)
        return fn
    return wrap


def all_sources() -> list[SourceDef]:
    return list(_SOURCES.values())


def split_disk_source(source_id: str) -> tuple[str, Optional[int]]:
    """'disk.used.2' -> ('disk.used', 2); sonst (id, None)."""
    treffer = _DISK_SUFFIX.match(source_id)
    if treffer:
        return treffer.group(1), int(treffer.group(2))
    return source_id, None


def get_source(source_id: str) -> Optional[SourceDef]:
    basis, _ = split_disk_source(source_id)
    return _SOURCES.get(basis)


# Formatierung

def format_number(wert: float, decimals: int, thousands: bool) -> str:
    """Zahl deutsch formatieren: Dezimalkomma ist bewusst NICHT im Spiel, die 5x7-Schrift
    zeigt einen Punkt klarer. Tausendertrenner ist der Punkt, dann Dezimaltrenner das Komma."""
    if thousands:
        text = f"{wert:,.{decimals}f}".replace(",", "\u0000").replace(".", ",").replace("\u0000", ".")
        return text
    return f"{wert:.{decimals}f}"


def resolve(source_id: str, ctx: ValueContext) -> Value:
    """Wert einer Quelle inklusive Simulation und Zahlformatierung nach Optionen."""
    basis, disk_index = split_disk_source(source_id)
    definition = _SOURCES.get(basis)
    if definition is None:
        return Value(text=ctx.opts.text or "?")
    if disk_index is not None:
        ctx.disk_index = disk_index

    if source_id in ctx.simulate or basis in ctx.simulate:
        sim = ctx.simulate.get(source_id, ctx.simulate.get(basis, 0.0))
        wert = Value(number=sim, percent=sim if definition.value_type == ValueType.percent else None)
        if definition.value_type in (ValueType.string, ValueType.time):
            wert = definition.resolver(ctx)
    else:
        wert = definition.resolver(ctx)

    if wert.number is not None and definition.value_type in (ValueType.number, ValueType.percent):
        decimals = ctx.opts.decimals if ctx.opts.decimals is not None else definition.decimals
        wert.text = format_number(wert.number, decimals, ctx.opts.thousands)
    return wert


def _bytes_text(b: float) -> str:
    if b > 1048576:
        return f"{b / 1048576:.1f} MB/s"
    if b > 1024:
        return f"{round(b / 1024)} KB/s"
    return f"{round(b)} B/s"


def _clock(zone: str) -> Resolver:
    def lese(ctx: ValueContext) -> Value:
        return Value(text=datetime.now(ZoneInfo(zone)).strftime("%H:%M"))
    return lese


# CPU

@source("cpu.temp", Tab.cpu, "Temperatur", ValueType.number, "°C", decimals=1)
def _cpu_temp(ctx: ValueContext) -> Value:
    t = ctx.stats.cpu.temp
    return Value(number=t, percent=min(100.0, t / 85 * 100))


@source("cpu.percent", Tab.cpu, "Auslastung", ValueType.percent, "%")
def _cpu_percent(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.cpu.percent, percent=ctx.stats.cpu.percent)


@source("cpu.cores", Tab.cpu, "Kerne", ValueType.number)
def _cpu_cores(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.cpu.cores)


@source("cpu.temp_min", Tab.cpu, "Temp Min", ValueType.number, "°C", decimals=1)
def _cpu_temp_min(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.cpu.temp_min)


@source("cpu.temp_max", Tab.cpu, "Temp Max", ValueType.number, "°C", decimals=1)
def _cpu_temp_max(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.cpu.temp_max)


@source("cpu.temp_range", Tab.cpu, "Temp Bereich", ValueType.string, "°C")
def _cpu_temp_range(ctx: ValueContext) -> Value:
    return Value(text=f"{ctx.stats.cpu.temp_min:.1f}-{ctx.stats.cpu.temp_max:.1f}")


@source("cpu.temp_pct", Tab.cpu, "Temp Auslastung", ValueType.percent, "%",
        description="Temperatur bezogen auf 85 °C")
def _cpu_temp_pct(ctx: ValueContext) -> Value:
    p = min(100.0, ctx.stats.cpu.temp / 85 * 100)
    return Value(number=p, percent=p)


@source("cpu.load", Tab.cpu, "CPU + Temp", ValueType.string)
def _cpu_load(ctx: ValueContext) -> Value:
    return Value(text=f"{round(ctx.stats.cpu.percent)}% {ctx.stats.cpu.temp:.1f}C")


# RAM

@source("ram.used", Tab.ram, "Benutzt", ValueType.number, "GB", decimals=1)
def _ram_used(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.ram.used_gb, percent=ctx.stats.ram.percent)


@source("ram.total", Tab.ram, "Gesamt", ValueType.number, "GB", decimals=1)
def _ram_total(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.ram.total_gb)


@source("ram.available", Tab.ram, "Verfügbar", ValueType.number, "GB", decimals=1)
def _ram_available(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.ram.available_gb, percent=100 - ctx.stats.ram.percent)


@source("ram.percent", Tab.ram, "Auslastung", ValueType.percent, "%")
def _ram_percent(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.ram.percent, percent=ctx.stats.ram.percent)


@source("ram.ratio", Tab.ram, "Benutzt/Gesamt", ValueType.string, "GB")
def _ram_ratio(ctx: ValueContext) -> Value:
    return Value(text=f"{ctx.stats.ram.used_gb:.1f}/{ctx.stats.ram.total_gb:.1f}")


@source("ram.free_pct", Tab.ram, "Frei", ValueType.percent, "%")
def _ram_free(ctx: ValueContext) -> Value:
    p = 100 - ctx.stats.ram.percent
    return Value(number=p, percent=p)


# Laufwerke (je Laufwerk, Kennung mit Index-Suffix)

@source("disk.label", Tab.disk, "Name", ValueType.string, per_disk=True)
def _disk_label(ctx: ValueContext) -> Value:
    d = ctx.stats.disk(ctx.disk_index)
    return Value(text=d.label or d.mount or "?")


@source("disk.mount", Tab.disk, "Mountpunkt", ValueType.string, per_disk=True)
def _disk_mount(ctx: ValueContext) -> Value:
    return Value(text=ctx.stats.disk(ctx.disk_index).mount or "?")


@source("disk.used", Tab.disk, "Benutzt", ValueType.number, "GB", decimals=1, per_disk=True)
def _disk_used(ctx: ValueContext) -> Value:
    d = ctx.stats.disk(ctx.disk_index)
    return Value(number=d.used_gb, percent=d.percent)


@source("disk.total", Tab.disk, "Gesamt", ValueType.number, "GB", decimals=1, per_disk=True)
def _disk_total(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.disk(ctx.disk_index).total_gb)


@source("disk.available", Tab.disk, "Verfügbar", ValueType.number, "GB", decimals=1, per_disk=True)
def _disk_available(ctx: ValueContext) -> Value:
    d = ctx.stats.disk(ctx.disk_index)
    return Value(number=d.available_gb, percent=100 - d.percent)


@source("disk.percent", Tab.disk, "Auslastung", ValueType.percent, "%", per_disk=True)
def _disk_percent(ctx: ValueContext) -> Value:
    p = ctx.stats.disk(ctx.disk_index).percent
    return Value(number=p, percent=p)


@source("disk.ratio", Tab.disk, "Benutzt/Gesamt", ValueType.string, "GB", per_disk=True)
def _disk_ratio(ctx: ValueContext) -> Value:
    d = ctx.stats.disk(ctx.disk_index)
    return Value(text=f"{d.used_gb:.1f}/{d.total_gb:.1f}")


@source("disk.free_pct", Tab.disk, "Frei", ValueType.percent, "%", per_disk=True)
def _disk_free(ctx: ValueContext) -> Value:
    p = 100 - ctx.stats.disk(ctx.disk_index).percent
    return Value(number=p, percent=p)


@source("disk.model", Tab.disk, "Modell", ValueType.string, per_disk=True)
def _disk_model(ctx: ValueContext) -> Value:
    return Value(text=ctx.stats.disk(ctx.disk_index).model)


@source("disk.fstype", Tab.disk, "Dateisystem", ValueType.string, per_disk=True)
def _disk_fstype(ctx: ValueContext) -> Value:
    return Value(text=ctx.stats.disk(ctx.disk_index).fstype)


# Netzwerk

@source("net.ip", Tab.net, "IP-Adresse", ValueType.string)
def _net_ip(ctx: ValueContext) -> Value:
    return Value(text=ctx.stats.network.ip or "0.0.0.0")


@source("net.interface", Tab.net, "Schnittstelle", ValueType.string)
def _net_if(ctx: ValueContext) -> Value:
    return Value(text=ctx.stats.network.interface or "?")


@source("net.rx", Tab.net, "Download", ValueType.string)
def _net_rx(ctx: ValueContext) -> Value:
    return Value(text=_bytes_text(ctx.stats.network.rx_bytes_sec))


@source("net.tx", Tab.net, "Upload", ValueType.string)
def _net_tx(ctx: ValueContext) -> Value:
    return Value(text=_bytes_text(ctx.stats.network.tx_bytes_sec))


@source("net.rx_raw", Tab.net, "Download Bytes", ValueType.number, "B/s")
def _net_rx_raw(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.network.rx_bytes_sec)


@source("net.tx_raw", Tab.net, "Upload Bytes", ValueType.number, "B/s")
def _net_tx_raw(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.network.tx_bytes_sec)


@source("net.traffic", Tab.net, "Download/Upload", ValueType.string)
def _net_traffic(ctx: ValueContext) -> Value:
    n = ctx.stats.network
    return Value(text=f"{_bytes_text(n.rx_bytes_sec)} {_bytes_text(n.tx_bytes_sec)}")


@source("net.hostname", Tab.net, "Rechnername", ValueType.string)
def _net_hostname(ctx: ValueContext) -> Value:
    return Value(text=ctx.stats.network.hostname or "PyroPlus")


# Lüfter

@source("fan.rpm", Tab.fan, "Drehzahl", ValueType.number, "RPM")
def _fan_rpm(ctx: ValueContext) -> Value:
    rpm = ctx.stats.fan.rpm
    return Value(number=rpm, percent=min(100.0, rpm / 4000 * 100))


@source("fan.duty", Tab.fan, "PWM-Leistung", ValueType.percent, "%")
def _fan_duty(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.fan.current_duty, percent=ctx.stats.fan.current_duty)


@source("fan.level", Tab.fan, "Stufe", ValueType.string)
def _fan_level(ctx: ValueContext) -> Value:
    return Value(text=ctx.stats.fan.level_name or "?")


@source("fan.case", Tab.fan, "Gehäuselüfter", ValueType.string)
def _fan_case(ctx: ValueContext) -> Value:
    return Value(text="An" if ctx.stats.fan.case_on else "Aus")


@source("fan.mode", Tab.fan, "Modus", ValueType.string)
def _fan_mode(ctx: ValueContext) -> Value:
    return Value(text=ctx.stats.fan.mode or "?")


@source("fan.rpm_pct", Tab.fan, "Drehzahl %", ValueType.percent, "%", description="Drehzahl bezogen auf 4000 RPM")
def _fan_rpm_pct(ctx: ValueContext) -> Value:
    p = min(100.0, ctx.stats.fan.rpm / 4000 * 100)
    return Value(number=p, percent=p)


@source("fan.pwm_level", Tab.fan, "PWM-Stufe", ValueType.number)
def _fan_pwm_level(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.fan.pwm_level)


@source("fan.symbol", Tab.fan, "Lüftersymbol", ValueType.animated, description="Dreht sich mit der Drehzahl")
def _fan_symbol(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.fan.rpm)


@source("fan.symbol_rpm", Tab.fan, "Symbol + Drehzahl", ValueType.animated)
def _fan_symbol_rpm(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.fan.rpm)


# Zeiten

@source("zeit.uhr", Tab.zeit, "Uhrzeit HH:MM", ValueType.time)
def _zeit_uhr(ctx: ValueContext) -> Value:
    return Value(text=ctx.now.strftime("%H:%M"))


@source("zeit.uhr_s", Tab.zeit, "Uhr + Sekunden", ValueType.time)
def _zeit_uhr_s(ctx: ValueContext) -> Value:
    return Value(text=ctx.now.strftime("%H:%M:%S"))


@source("zeit.uhr_blink", Tab.zeit, "Uhr blinkend", ValueType.time)
def _zeit_uhr_blink(ctx: ValueContext) -> Value:
    colon = ":" if ctx.now.second % 2 == 0 else " "
    return Value(text=f"{ctx.now:%H}{colon}{ctx.now:%M}")


@source("zeit.stunde", Tab.zeit, "Stunde", ValueType.number, "h")
def _zeit_stunde(ctx: ValueContext) -> Value:
    return Value(number=ctx.now.hour)


@source("zeit.minute", Tab.zeit, "Minute", ValueType.number, "m")
def _zeit_minute(ctx: ValueContext) -> Value:
    return Value(number=ctx.now.minute)


@source("zeit.sekunde", Tab.zeit, "Sekunde", ValueType.number, "s")
def _zeit_sekunde(ctx: ValueContext) -> Value:
    return Value(number=ctx.now.second)


@source("zeit.datum", Tab.zeit, "Datum TT.MM.JJJJ", ValueType.time)
def _zeit_datum(ctx: ValueContext) -> Value:
    return Value(text=ctx.now.strftime("%d.%m.%Y"))


@source("zeit.datum_kurz", Tab.zeit, "Datum TT.MM.", ValueType.time)
def _zeit_datum_kurz(ctx: ValueContext) -> Value:
    return Value(text=ctx.now.strftime("%d.%m."))


@source("zeit.jahr", Tab.zeit, "Jahr", ValueType.number)
def _zeit_jahr(ctx: ValueContext) -> Value:
    return Value(number=ctx.now.year)


@source("zeit.tag", Tab.zeit, "Wochentag kurz", ValueType.time)
def _zeit_tag(ctx: ValueContext) -> Value:
    return Value(text=TAGE_KURZ[ctx.now.weekday()])


@source("zeit.tag_lang", Tab.zeit, "Wochentag lang", ValueType.time)
def _zeit_tag_lang(ctx: ValueContext) -> Value:
    return Value(text=TAGE_LANG[ctx.now.weekday()])


@source("zeit.tag_datum", Tab.zeit, "Tag + Datum", ValueType.time)
def _zeit_tag_datum(ctx: ValueContext) -> Value:
    return Value(text=f"{TAGE_KURZ[ctx.now.weekday()]} {ctx.now:%d.%m.%Y}")


@source("zeit.uptime", Tab.zeit, "Laufzeit", ValueType.string)
def _zeit_uptime(ctx: ValueContext) -> Value:
    return Value(text=ctx.stats.uptime.formatted or "0m")


@source("zeit.uptime_s", Tab.zeit, "Laufzeit Sekunden", ValueType.number, "s")
def _zeit_uptime_s(ctx: ValueContext) -> Value:
    return Value(number=ctx.stats.uptime.seconds)


@source("zeit.unix", Tab.zeit, "Unix-Zeitstempel", ValueType.number)
def _zeit_unix(ctx: ValueContext) -> Value:
    return Value(number=int(ctx.now.timestamp()))


@source("zeit.iso", Tab.zeit, "ISO-Datum", ValueType.string)
def _zeit_iso(ctx: ValueContext) -> Value:
    return Value(text=ctx.now.strftime("%Y-%m-%dT%H:%M:%S"))


for _kennung, _label, _zone in (
    ("zeit.utc", "UTC", "UTC"),
    ("zeit.new_york", "New York", "America/New_York"),
    ("zeit.london", "London", "Europe/London"),
    ("zeit.paris", "Paris/Berlin", "Europe/Paris"),
    ("zeit.moskau", "Moskau", "Europe/Moscow"),
    ("zeit.dubai", "Dubai", "Asia/Dubai"),
    ("zeit.mumbai", "Mumbai", "Asia/Kolkata"),
    ("zeit.shanghai", "Shanghai", "Asia/Shanghai"),
    ("zeit.tokio", "Tokio", "Asia/Tokyo"),
    ("zeit.sydney", "Sydney", "Australia/Sydney"),
    ("zeit.los_angeles", "Los Angeles", "America/Los_Angeles"),
):
    source(_kennung, Tab.zeit, _label, ValueType.time, description="Weltzeituhr")(_clock(_zone))


# Wetter

def _w(ctx: ValueContext) -> Optional[WeatherReport]:
    return ctx.weather


def _wetter_zahl(attribut: str, decimals: int) -> Resolver:
    def lese(ctx: ValueContext) -> Value:
        bericht = _w(ctx)
        if bericht is None:
            return Value(text="--")
        wert = getattr(bericht.current, attribut, None)
        if wert is None:
            return Value(text="--")
        return Value(number=float(wert))
    return lese


for _kennung, _label, _einheit, _attr, _dec in (
    ("wetter.temp", "Temperatur", "°C", "temperature", 1),
    ("wetter.gefuehlt", "Gefühlt", "°C", "apparent_temperature", 1),
    ("wetter.wind", "Wind", "km/h", "wind_speed", 0),
    ("wetter.windricht", "Windrichtung", "°", "wind_direction", 0),
    ("wetter.boeen", "Böen", "km/h", "wind_gusts", 0),
    ("wetter.druck", "Luftdruck", "hPa", "pressure", 0),
    ("wetter.druck_msl", "Druck (Meer)", "hPa", "pressure_msl", 0),
    ("wetter.niederschlag", "Niederschlag", "mm", "precipitation", 1),
):
    source(_kennung, Tab.wetter, _label, ValueType.number, _einheit, decimals=_dec,
           uses_location=True)(_wetter_zahl(_attr, _dec))


@source("wetter.feuchte", Tab.wetter, "Feuchtigkeit", ValueType.percent, "%", uses_location=True)
def _wetter_feuchte(ctx: ValueContext) -> Value:
    b = _w(ctx)
    if b is None or b.current.humidity is None:
        return Value(text="--")
    return Value(number=b.current.humidity, percent=b.current.humidity)


@source("wetter.wolken", Tab.wetter, "Bewölkung", ValueType.percent, "%", uses_location=True)
def _wetter_wolken(ctx: ValueContext) -> Value:
    b = _w(ctx)
    if b is None or b.current.cloud_cover is None:
        return Value(text="--")
    return Value(number=b.current.cloud_cover, percent=b.current.cloud_cover)


@source("wetter.zustand", Tab.wetter, "Zustand", ValueType.string, uses_location=True)
def _wetter_zustand(ctx: ValueContext) -> Value:
    b = _w(ctx)
    return Value(text=b.current.condition_text if b else "--")


@source("wetter.tag_nacht", Tab.wetter, "Tag/Nacht", ValueType.string, uses_location=True)
def _wetter_tag_nacht(ctx: ValueContext) -> Value:
    b = _w(ctx)
    if b is None:
        return Value(text="--")
    return Value(text="Tag" if b.current.is_day else "Nacht")


@source("wetter.ort", Tab.wetter, "Ort", ValueType.string, uses_location=True)
def _wetter_ort(ctx: ValueContext) -> Value:
    b = _w(ctx)
    return Value(text=b.location_name if b else "--")


@source("wetter.sunrise", Tab.wetter, "Sonnenaufgang", ValueType.time, uses_location=True)
def _wetter_sunrise(ctx: ValueContext) -> Value:
    b = _w(ctx)
    return Value(text=b.current.sunrise if b and b.current.sunrise else "--")


@source("wetter.sunset", Tab.wetter, "Sonnenuntergang", ValueType.time, uses_location=True)
def _wetter_sunset(ctx: ValueContext) -> Value:
    b = _w(ctx)
    return Value(text=b.current.sunset if b and b.current.sunset else "--")


@source("wetter.kombi", Tab.wetter, "Temp + Zustand", ValueType.string, uses_location=True)
def _wetter_kombi(ctx: ValueContext) -> Value:
    b = _w(ctx)
    if b is None or b.current.temperature is None:
        return Value(text="--")
    return Value(text=f"{b.current.temperature:.0f}° {b.current.condition_text}")


@source("wetter.wind_kombi", Tab.wetter, "Wind + Böen", ValueType.string, uses_location=True)
def _wetter_wind_kombi(ctx: ValueContext) -> Value:
    b = _w(ctx)
    if b is None or b.current.wind_speed is None:
        return Value(text="--")
    boeen = b.current.wind_gusts if b.current.wind_gusts is not None else 0.0
    return Value(text=f"{b.current.wind_speed:.0f} ({boeen:.0f}) km/h")


# Texte

@source("text.frei", Tab.text, "Freier Text", ValueType.string)
def _text_frei(ctx: ValueContext) -> Value:
    return Value(text=ctx.opts.text if ctx.opts.text is not None else "Text")


@source("text.laufschrift", Tab.text, "Laufschrift", ValueType.string)
def _text_laufschrift(ctx: ValueContext) -> Value:
    return Value(text=ctx.opts.text if ctx.opts.text is not None else "Laufschrift")


@source("text.mehrzeilig", Tab.text, "Mehrzeilig", ValueType.string, description="Zeilen mit Zeilenumbruch trennen")
def _text_mehrzeilig(ctx: ValueContext) -> Value:
    return Value(text=ctx.opts.text if ctx.opts.text is not None else "Zeile 1\nZeile 2")


@source("text.leer", Tab.text, "Leer", ValueType.string)
def _text_leer(ctx: ValueContext) -> Value:
    return Value(text="")


# Layout

for _kennung, _label in (
    ("layout.linie_h", "Linie waagerecht"),
    ("layout.linie_v", "Linie senkrecht"),
    ("layout.rahmen", "Rahmen"),
    ("layout.block", "Block"),
    ("layout.section", "Trennlinie mit Titel"),
):
    source(_kennung, Tab.layout, _label, ValueType.shape)(lambda ctx: Value())


@source("layout.bitmap", Tab.layout, "Pixelbild", ValueType.bitmap, description="Frei gezeichnetes Bild")
def _layout_bitmap(ctx: ValueContext) -> Value:
    return Value()


LAYOUT_DEFAULT_DISPLAY: dict[str, str] = {
    "layout.linie_h": "linie_h",
    "layout.linie_v": "linie_v",
    "layout.rahmen": "rahmen",
    "layout.block": "block",
    "layout.section": "section",
    "layout.bitmap": "bitmap",
}
