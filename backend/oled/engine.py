"""
PyroPlus: OLED-Engine.

Besitzt die Einstellungen, Vorlagen, Profile und Wetterorte, führt die
Render-Schleife, die Rotation und die Hardware-Ausgabe. Jede Änderung läuft
über eine Methode dieser Klasse, wird gespeichert und zählt die
Bildschirm-Version hoch, damit die Oberfläche nachlädt.
"""

from __future__ import annotations

import base64
import logging
import threading
import time
from datetime import datetime
from typing import Callable, Optional
from zoneinfo import ZoneInfo

import hw_client
from oled.compose import RenderContext, render_screen, render_widget
from oled.models import (
    Catalog, GeocodeHit, ImportResult, neue_id, OledBundle, OledLive, OledMode, OledSettings,
    OledSettingsPatch, OledState, Profile, RenderResponse, Screen, WeatherLocation,
    WeatherLocationCreate, WeatherLocationState, WeatherSettings, Widget, WidgetBox, WidgetPreset,
    WidgetRenderResponse,
)
from oled.renderer import buf_to_pil, buf_to_png_base64, ausschnitt_png_base64
from oled.store import OledStore
from oled.values import StatsSnapshot
from oled.weather import WeatherReport, WeatherService
from oled.catalog import build_catalog

logger = logging.getLogger("oled")
TZ = ZoneInfo("Europe/Berlin")

StatsProvider = Callable[[], dict]
FanStateProvider = Callable[[], dict]


class NotFound(Exception):
    pass


class OledEngine:
    def __init__(self, store: OledStore, weather: WeatherService, stats_provider: StatsProvider,
                 fan_state_provider: Optional[FanStateProvider] = None,
                 render_interval: float = 0.2, app_version: str = "") -> None:
        self.store = store
        self.weather = weather
        self._stats_provider = stats_provider
        self._fan_state_provider = fan_state_provider
        self.render_interval = render_interval
        self.app_version = app_version

        self._lock = threading.RLock()
        self.settings: OledSettings = store.load_settings()
        self.presets: list[WidgetPreset] = store.load_presets()
        self.profiles: list[Profile] = store.load_profiles()
        self.screens_version = 1
        self.preview: Optional[str] = None
        self.last_boxes: list[WidgetBox] = []

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._rotation_reset = False

        self.hardware = hw_client.oled_available()
        hw_client.oled_brightness(self.settings.brightness)
        self._ensure_current()
        logger.info(f"OLED-Hardware: {self.hardware}, {len(self.settings.screens)} Bildschirme")

    # Hilfen

    def _ensure_current(self) -> None:
        if self.settings.screen_by_id(self.settings.current_screen_id) is None and self.settings.screens:
            self.settings.current_screen_id = self.settings.screens[0].id

    def _save(self, bump: bool = True) -> None:
        self._ensure_current()
        self.store.save_settings(self.settings)
        if bump:
            self.screens_version += 1

    def _snapshot(self) -> StatsSnapshot:
        roh = dict(self._stats_provider() or {})
        if self._fan_state_provider is not None:
            fan = dict(roh.get("fan") or {})
            fan.update({k: v for k, v in (self._fan_state_provider() or {}).items()
                        if k in ("current_duty", "case_on", "mode", "current_rpm")})
            if "current_rpm" in fan and not fan.get("rpm"):
                fan["rpm"] = fan["current_rpm"]
            roh["fan"] = fan
        return StatsSnapshot.model_validate(roh)

    def _context(self, stats: StatsSnapshot, simulate: Optional[dict[str, float]] = None) -> RenderContext:
        return RenderContext(stats=stats, now=datetime.now(TZ),
                             weather_for=self.weather.report_for, simulate=simulate or {})

    def _screen_by_id(self, screen_id: str) -> Screen:
        screen = self.settings.screen_by_id(screen_id)
        if screen is None:
            raise NotFound(f"Bildschirm {screen_id} nicht gefunden")
        return screen

    # Rendern

    def render_draft(self, screen: Screen, simulate: Optional[dict[str, float]] = None) -> RenderResponse:
        """Rendert einen Entwurf ohne ihn zu speichern oder anzuzeigen."""
        stats = self._snapshot()
        buf, boxes = render_screen(screen, self._context(stats, simulate))
        return RenderResponse(image_base64=buf_to_png_base64(buf), boxes=boxes)

    def render_widget_preview(self, widget: Widget, simulate: Optional[dict[str, float]] = None) -> WidgetRenderResponse:
        """Rendert ein einzelnes Widget bei 0/0 und schneidet das Bild auf seinen Rahmen zu."""
        kopie = widget.model_copy(deep=True)
        kopie.x, kopie.y = 0, 0
        buf, box = render_widget(kopie, self._context(self._snapshot(), simulate))
        if box.w <= 0 or box.h <= 0:
            return WidgetRenderResponse(image_base64="", width=0, height=0, box=box)
        return WidgetRenderResponse(image_base64=ausschnitt_png_base64(buf, box.x, box.y, box.w, box.h),
                                    width=box.w, height=box.h, box=box)

    def render_current(self, stats: Optional[StatsSnapshot] = None) -> None:
        """Rendert den aktiven Bildschirm, zeigt ihn an und merkt die Vorschau."""
        with self._lock:
            settings = self.settings
            screen = settings.screen_by_id(settings.current_screen_id)
            mode = settings.mode
        if stats is None:
            stats = self._snapshot()
        if mode == OledMode.off or screen is None:
            buf, boxes = bytearray(128 * 64), []
        else:
            buf, boxes = render_screen(screen, self._context(stats))
        if mode != OledMode.off:
            self._send(buf)
        self.preview = buf_to_png_base64(buf)
        self.last_boxes = boxes

    def _send(self, buf: bytearray) -> None:
        if not self.hardware:
            return
        import io
        img = buf_to_pil(buf)
        out = io.BytesIO()
        img.save(out, format="PNG")
        hw_client.oled_display(base64.b64encode(out.getvalue()).decode())

    # Schleife

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="oled-render")
        self._thread.start()
        logger.info("OLED-Engine gestartet")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        hw_client.oled_clear()

    def _rotation_screens(self) -> list[Screen]:
        return [s for s in self.settings.screens if s.enabled]

    def _loop(self) -> None:
        last_rotate = time.time()
        last_stats = 0.0
        last_weather = 0.0
        stats: Optional[StatsSnapshot] = None
        while self._running:
            try:
                now = time.time()
                if self._rotation_reset:
                    last_rotate = now
                    self._rotation_reset = False
                if now - last_stats >= 1.0 or stats is None:
                    stats = self._snapshot()
                    last_stats = now
                if now - last_weather >= 30.0:
                    self.weather.refresh_due()
                    last_weather = now
                self.render_current(stats)
                if self._rotate_if_due(now, last_rotate):
                    last_rotate = now
            except Exception as fehler:
                logger.error(f"OLED-Schleife: {fehler}")
            time.sleep(self.render_interval)

    def _rotate_if_due(self, now: float, last_rotate: float) -> bool:
        """Schaltet in der Betriebsart auto zum nächsten aktiven Bildschirm; True bei Wechsel."""
        with self._lock:
            if self.settings.mode != OledMode.auto:
                return False
            kandidaten = self._rotation_screens()
            if len(kandidaten) < 2:
                return False
            aktuell = self.settings.screen_by_id(self.settings.current_screen_id)
            dauer = (aktuell.duration if aktuell and aktuell.duration else self.settings.rotation_interval)
            if now - last_rotate < dauer:
                return False
            ids = [s.id for s in kandidaten]
            if self.settings.current_screen_id in ids:
                naechster = ids[(ids.index(self.settings.current_screen_id) + 1) % len(ids)]
            else:
                naechster = ids[0]
            self.settings.current_screen_id = naechster
            return True

    # Einstellungen

    def patch_settings(self, patch: OledSettingsPatch) -> OledSettings:
        with self._lock:
            if patch.mode is not None:
                self.settings.mode = patch.mode
                if patch.mode == OledMode.off:
                    hw_client.oled_clear()
            if patch.brightness is not None:
                self.settings.brightness = patch.brightness
                hw_client.oled_brightness(patch.brightness)
            if patch.rotation_interval is not None:
                self.settings.rotation_interval = patch.rotation_interval
            if patch.current_screen_id is not None:
                self._screen_by_id(patch.current_screen_id)
                self.settings.current_screen_id = patch.current_screen_id
                self._rotation_reset = True
            self._save(bump=False)
            self.screens_version += 1
            return self.settings

    def activate(self, screen_id: str) -> OledSettings:
        return self.patch_settings(OledSettingsPatch(current_screen_id=screen_id))

    # Bildschirme

    def list_screens(self) -> list[Screen]:
        with self._lock:
            return list(self.settings.screens)

    def replace_screens(self, screens: list[Screen]) -> list[Screen]:
        with self._lock:
            self.settings.screens = list(screens)
            self._save()
            return list(self.settings.screens)

    def add_screen(self, screen: Screen) -> Screen:
        with self._lock:
            if self.settings.screen_by_id(screen.id) is not None:
                screen.id = neue_id()
            if not screen.name:
                screen.name = f"Bildschirm {len(self.settings.screens) + 1}"
            self.settings.screens.append(screen)
            if self.settings.current_screen_id is None:
                self.settings.current_screen_id = screen.id
            self._save()
            return screen

    def update_screen(self, screen_id: str, screen: Screen) -> Screen:
        with self._lock:
            alt = self._screen_by_id(screen_id)
            screen.id = alt.id
            index = self.settings.screens.index(alt)
            self.settings.screens[index] = screen
            self._save()
            return screen

    def delete_screen(self, screen_id: str) -> None:
        with self._lock:
            screen = self._screen_by_id(screen_id)
            if len(self.settings.screens) <= 1:
                raise ValueError("Der letzte Bildschirm kann nicht gelöscht werden")
            self.settings.screens.remove(screen)
            if self.settings.current_screen_id == screen_id:
                self.settings.current_screen_id = self.settings.screens[0].id
            self._save()

    def duplicate_screen(self, screen_id: str) -> Screen:
        with self._lock:
            original = self._screen_by_id(screen_id)
            kopie = original.model_copy(deep=True)
            kopie.id = neue_id()
            kopie.name = f"{original.name} Kopie"
            for widget in kopie.widgets:
                widget.id = neue_id()
            index = self.settings.screens.index(original)
            self.settings.screens.insert(index + 1, kopie)
            self._save()
            return kopie

    def reorder_screens(self, ids: list[str]) -> list[Screen]:
        with self._lock:
            nach_id = {s.id: s for s in self.settings.screens}
            neu = [nach_id[i] for i in ids if i in nach_id]
            rest = [s for s in self.settings.screens if s.id not in ids]
            self.settings.screens = neu + rest
            self._save()
            return list(self.settings.screens)

    # Vorlagen

    def add_preset(self, preset: WidgetPreset) -> WidgetPreset:
        with self._lock:
            self.presets.append(preset)
            self.store.save_presets(self.presets)
            return preset

    def update_preset(self, preset_id: str, preset: WidgetPreset) -> WidgetPreset:
        with self._lock:
            for i, p in enumerate(self.presets):
                if p.id == preset_id:
                    preset.id = preset_id
                    self.presets[i] = preset
                    self.store.save_presets(self.presets)
                    return preset
            raise NotFound(f"Vorlage {preset_id} nicht gefunden")

    def delete_preset(self, preset_id: str) -> None:
        with self._lock:
            vorher = len(self.presets)
            self.presets = [p for p in self.presets if p.id != preset_id]
            if len(self.presets) == vorher:
                raise NotFound(f"Vorlage {preset_id} nicht gefunden")
            self.store.save_presets(self.presets)

    # Profile

    def save_profile(self, name: str) -> Profile:
        """Aktuellen Stand unter einem Namen sichern; gleicher Name überschreibt."""
        with self._lock:
            profil = Profile(name=name, screens=[s.model_copy(deep=True) for s in self.settings.screens],
                             rotation_interval=self.settings.rotation_interval)
            self.profiles = [p for p in self.profiles if p.name != name] + [profil]
            self.store.save_profiles(self.profiles)
            return profil

    def delete_profile(self, profile_id: str) -> None:
        with self._lock:
            vorher = len(self.profiles)
            self.profiles = [p for p in self.profiles if p.id != profile_id]
            if len(self.profiles) == vorher:
                raise NotFound(f"Profil {profile_id} nicht gefunden")
            self.store.save_profiles(self.profiles)

    def apply_profile(self, profile_id: str) -> OledSettings:
        with self._lock:
            for p in self.profiles:
                if p.id == profile_id:
                    self.settings.screens = [s.model_copy(deep=True) for s in p.screens]
                    self.settings.rotation_interval = p.rotation_interval
                    self.settings.current_screen_id = self.settings.screens[0].id if self.settings.screens else None
                    self._save()
                    return self.settings
            raise NotFound(f"Profil {profile_id} nicht gefunden")

    # Wetterorte

    def weather_states(self) -> list[WeatherLocationState]:
        return self.weather.states()

    def add_location(self, daten: WeatherLocationCreate) -> WeatherLocation:
        with self._lock:
            ort = WeatherLocation(name=daten.name, lat=daten.lat, lon=daten.lon, country=daten.country)
            self.weather.settings.locations.append(ort)
            if self.weather.settings.default_location_id is None:
                self.weather.settings.default_location_id = ort.id
            self.store.save_weather(self.weather.settings)
        threading.Thread(target=self.weather.refresh_location, args=(ort,), daemon=True).start()
        return ort

    def delete_location(self, location_id: str) -> None:
        with self._lock:
            orte = self.weather.settings.locations
            if len(orte) <= 1:
                raise ValueError("Der letzte Wetterort kann nicht gelöscht werden")
            if not any(o.id == location_id for o in orte):
                raise NotFound(f"Wetterort {location_id} nicht gefunden")
            self.weather.settings.locations = [o for o in orte if o.id != location_id]
            if self.weather.settings.default_location_id == location_id:
                self.weather.settings.default_location_id = self.weather.settings.locations[0].id
            self.weather.forget(location_id)
            self.store.save_weather(self.weather.settings)

    def set_default_location(self, location_id: str) -> WeatherSettings:
        with self._lock:
            if self.weather.settings.location_by_id(location_id) is None:
                raise NotFound(f"Wetterort {location_id} nicht gefunden")
            self.weather.settings.default_location_id = location_id
            self.store.save_weather(self.weather.settings)
            return self.weather.settings

    def refresh_weather(self, location_id: Optional[str] = None) -> None:
        if location_id is None:
            self.weather.refresh_due(force=True)
            return
        ort = self.weather.settings.location_by_id(location_id)
        if ort is None:
            raise NotFound(f"Wetterort {location_id} nicht gefunden")
        self.weather.refresh_location(ort)

    def geocode(self, query: str) -> list[GeocodeHit]:
        return self.weather.geocode(query)

    # Katalog, Zustand, Austausch

    def catalog(self) -> Catalog:
        stats = self._snapshot()
        return build_catalog(stats, datetime.now(TZ), self.weather.report_for(None))

    def get_live(self) -> OledLive:
        with self._lock:
            return OledLive(mode=self.settings.mode, brightness=self.settings.brightness,
                            rotation_interval=self.settings.rotation_interval,
                            current_screen_id=self.settings.current_screen_id,
                            screens_version=self.screens_version, preview=self.preview)

    def get_state(self) -> OledState:
        with self._lock:
            return OledState(mode=self.settings.mode, brightness=self.settings.brightness,
                             rotation_interval=self.settings.rotation_interval,
                             current_screen_id=self.settings.current_screen_id,
                             screens_version=self.screens_version, preview=self.preview,
                             available=True, hardware=self.hardware, screens=list(self.settings.screens),
                             weather_ok=self.weather.any_ok(), version=self.app_version)

    def export_bundle(self) -> OledBundle:
        with self._lock:
            return OledBundle(app_version=self.app_version, settings=self.settings.model_copy(deep=True),
                              presets=list(self.presets), profiles=list(self.profiles),
                              weather=self.weather.settings.model_copy(deep=True))

    def import_bundle(self, bundle: OledBundle, replace: bool) -> ImportResult:
        """Übernimmt einen Export. replace=True ersetzt den Bestand, sonst wird ergänzt."""
        with self._lock:
            if replace:
                self.settings = bundle.settings
                self.presets = list(bundle.presets)
                self.profiles = list(bundle.profiles)
                if bundle.weather.locations:
                    self.weather.settings.locations = list(bundle.weather.locations)
                    self.weather.settings.default_location_id = bundle.weather.default_location_id
            else:
                vorhandene = {s.id for s in self.settings.screens}
                for screen in bundle.settings.screens:
                    if screen.id in vorhandene:
                        screen.id = neue_id()
                    self.settings.screens.append(screen)
                self.presets.extend(bundle.presets)
                namen = {p.name for p in self.profiles}
                self.profiles.extend(p for p in bundle.profiles if p.name not in namen)
                bekannt = {(round(o.lat, 3), round(o.lon, 3)) for o in self.weather.settings.locations}
                for ort in bundle.weather.locations:
                    if (round(ort.lat, 3), round(ort.lon, 3)) not in bekannt:
                        self.weather.settings.locations.append(ort)
            if not self.settings.screens:
                from oled.store import default_screen
                self.settings.screens = [default_screen()]
            self._save()
            self.store.save_presets(self.presets)
            self.store.save_profiles(self.profiles)
            self.store.save_weather(self.weather.settings)
            return ImportResult(screens=len(bundle.settings.screens), presets=len(bundle.presets),
                                profiles=len(bundle.profiles), locations=len(bundle.weather.locations))
