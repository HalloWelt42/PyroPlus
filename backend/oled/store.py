"""
PyroPlus: Persistenz des OLED-Bereichs.

Vier JSON-Dateien unter data/, atomar geschrieben (Temporärdatei, dann
umbenennen). Beim ersten Start mit altem Bestand (oled_settings.json, Schema 1)
wird einmalig migriert; die alten Dateien bleiben unangetastet.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional, TypeVar

from pydantic import BaseModel, TypeAdapter

from oled.migrate import MigrationResult, migrate_v1
from oled.models import OledSettings, Profile, Screen, WeatherSettings, WidgetPreset

logger = logging.getLogger("oled.store")

T = TypeVar("T", bound=BaseModel)


def _schreibe_atomar(pfad: Path, inhalt: str) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    tmp.write_text(inhalt, encoding="utf-8")
    os.replace(tmp, pfad)


class OledStore:
    SETTINGS = "oled.json"
    PRESETS = "oled_presets.json"
    PROFILES = "oled_profiles.json"
    WEATHER = "weather.json"
    LEGACY_SETTINGS = "oled_settings.json"
    LEGACY_BACKUP = "frontend_backup.json"
    LEGACY_PIXEL_DIR = "pixel_screens"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    # Allgemein

    def _lese(self, name: str) -> Optional[Any]:
        pfad = self.data_dir / name
        if not pfad.exists():
            return None
        try:
            return json.loads(pfad.read_text(encoding="utf-8"))
        except Exception as fehler:
            logger.error(f"{name} lesen: {fehler}")
            return None

    def _schreibe(self, name: str, modell: BaseModel | list[BaseModel]) -> None:
        if isinstance(modell, list):
            inhalt = json.dumps([m.model_dump(mode="json", by_alias=True) for m in modell],
                                indent=2, ensure_ascii=False)
        else:
            inhalt = json.dumps(modell.model_dump(mode="json", by_alias=True), indent=2, ensure_ascii=False)
        _schreibe_atomar(self.data_dir / name, inhalt + "\n")

    def _lese_liste(self, name: str, typ: type[T]) -> list[T]:
        roh = self._lese(name)
        if not isinstance(roh, list):
            return []
        ergebnis: list[T] = []
        for eintrag in roh:
            try:
                ergebnis.append(typ.model_validate(eintrag))
            except Exception as fehler:
                logger.warning(f"{name}: Eintrag übersprungen ({fehler})")
        return ergebnis

    # Erststart und Migration

    def ensure_initialised(self) -> Optional[MigrationResult]:
        """Legt fehlende Dateien an; migriert alten Bestand genau einmal."""
        if (self.data_dir / self.SETTINGS).exists():
            return None
        legacy = self._lese(self.LEGACY_SETTINGS)
        if legacy is None:
            self.save_settings(OledSettings(screens=[default_screen()]))
            self._ensure_weather()
            return None
        logger.info("Alter Bestand gefunden, migriere oled_settings.json nach Schema 2")
        ergebnis = migrate_v1(
            legacy,
            pixel_dir=self.data_dir / self.LEGACY_PIXEL_DIR,
            frontend_backup=self._lese(self.LEGACY_BACKUP),
        )
        self.save_settings(ergebnis.settings)
        self.save_presets(ergebnis.presets)
        self.save_profiles(ergebnis.profiles)
        wetter = ergebnis.weather
        self.save_weather(wetter)
        logger.info(f"Migration: {len(ergebnis.settings.screens)} Bildschirme, "
                    f"{len(ergebnis.presets)} Vorlagen, {len(ergebnis.profiles)} Profile, "
                    f"{len(wetter.locations)} Wetterorte")
        return ergebnis

    def _default_weather(self) -> WeatherSettings:
        """Ohne gespeicherte Orte bleibt die Liste leer; Wetterwerte zeigen dann '--'."""
        return WeatherSettings()

    def _ensure_weather(self) -> None:
        if not (self.data_dir / self.WEATHER).exists():
            self.save_weather(self._default_weather())

    # Einstellungen

    def load_settings(self) -> OledSettings:
        roh = self._lese(self.SETTINGS)
        if roh is None:
            return OledSettings(screens=[default_screen()])
        try:
            settings = OledSettings.model_validate(roh)
        except Exception as fehler:
            logger.error(f"oled.json ungültig, Vorgaben werden genutzt: {fehler}")
            return OledSettings(screens=[default_screen()])
        if not settings.screens:
            settings.screens = [default_screen()]
        return settings

    def save_settings(self, settings: OledSettings) -> None:
        self._schreibe(self.SETTINGS, settings)

    # Vorlagen

    def load_presets(self) -> list[WidgetPreset]:
        return self._lese_liste(self.PRESETS, WidgetPreset)

    def save_presets(self, presets: list[WidgetPreset]) -> None:
        self._schreibe(self.PRESETS, list(presets))

    # Profile

    def load_profiles(self) -> list[Profile]:
        return self._lese_liste(self.PROFILES, Profile)

    def save_profiles(self, profiles: list[Profile]) -> None:
        self._schreibe(self.PROFILES, list(profiles))

    # Wetter

    def load_weather(self) -> WeatherSettings:
        roh = self._lese(self.WEATHER)
        if roh is None:
            wetter = self._default_weather()
            self.save_weather(wetter)
            return wetter
        try:
            wetter = WeatherSettings.model_validate(roh)
        except Exception as fehler:
            logger.error(f"weather.json ungültig: {fehler}")
            return self._default_weather()
        return wetter

    def save_weather(self, wetter: WeatherSettings) -> None:
        self._schreibe(self.WEATHER, wetter)


def default_screen() -> Screen:
    """Erster Bildschirm bei leerem Bestand: Uhr, Datum, CPU, RAM, IP."""
    from oled.models import DisplayMode, Widget, WidgetOpts
    return Screen(name="Uhr + System", widgets=[
        Widget(source="zeit.uhr_blink", display=DisplayMode.text, x=0, y=0,
               name="Uhr", opts=WidgetOpts(scale_x=3, scale_y=3)),
        Widget(source="zeit.tag_datum", display=DisplayMode.text, x=0, y=24, name="Datum"),
        Widget(source="cpu.temp", display=DisplayMode.text, x=0, y=36, name="CPU",
               opts=WidgetOpts(prefix="CPU ", suffix=" C")),
        Widget(source="ram.percent", display=DisplayMode.text, x=0, y=46, name="RAM",
               opts=WidgetOpts(prefix="RAM ", suffix="%")),
        Widget(source="net.ip", display=DisplayMode.text, x=0, y=56, name="IP"),
    ])


ScreenList = TypeAdapter(list[Screen])
