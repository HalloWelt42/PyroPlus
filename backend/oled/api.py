"""
PyroPlus: Schnittstelle des OLED-Bereichs unter /api/oled.

Alle Antworten sind Modelle aus oled/models.py.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from oled.engine import NotFound, OledEngine
from oled.migrate import migrate_screen
from oled.models import (
    Catalog, GeocodeHit, ImportResult, OledBundle, OledMode, OledSettings, OledSettingsPatch,
    OledState, Profile, ProfileCreate, RenderRequest, RenderResponse, Screen, ScreenOrder,
    WeatherLocation, WeatherLocationCreate, WeatherLocationState, WeatherSettings, Widget, WidgetPreset,
)
from oled.templates import TemplateCatalog, screen_template, template_catalog, widget_template

router = APIRouter(prefix="/api/oled", tags=["OLED"])


def _engine(request: Request) -> OledEngine:
    return request.app.state.oled


def _fehler(fehler: Exception) -> HTTPException:
    if isinstance(fehler, NotFound):
        return HTTPException(status_code=404, detail=str(fehler))
    if isinstance(fehler, ValueError):
        return HTTPException(status_code=409, detail=str(fehler))
    return HTTPException(status_code=500, detail=str(fehler))


class Ok(BaseModel):
    ok: bool = True


# Zustand und Einstellungen

@router.get("", response_model=OledState, summary="Zustand inklusive Bildschirmen")
def oled_state(request: Request) -> OledState:
    return _engine(request).get_state()


@router.patch("/settings", response_model=OledSettings, summary="Einstellungen teilweise ändern")
def oled_patch_settings(patch: OledSettingsPatch, request: Request) -> OledSettings:
    try:
        return _engine(request).patch_settings(patch)
    except Exception as fehler:
        raise _fehler(fehler)


@router.get("/catalog", response_model=Catalog, summary="Datenquellen und Darstellungsarten")
def oled_catalog(request: Request) -> Catalog:
    return _engine(request).catalog()


@router.post("/render", response_model=RenderResponse, summary="Entwurf rendern (Bild + Rahmen)")
def oled_render(req: RenderRequest, request: Request) -> RenderResponse:
    return _engine(request).render_draft(req.screen, req.simulate)


# Bildschirme

@router.get("/screens", response_model=list[Screen])
def oled_screens(request: Request) -> list[Screen]:
    return _engine(request).list_screens()


@router.put("/screens", response_model=list[Screen], summary="Alle Bildschirme ersetzen")
def oled_replace_screens(screens: list[Screen], request: Request) -> list[Screen]:
    if not screens:
        raise HTTPException(status_code=409, detail="Mindestens ein Bildschirm ist nötig")
    return _engine(request).replace_screens(screens)


@router.post("/screens", response_model=Screen, status_code=201)
def oled_add_screen(screen: Screen, request: Request) -> Screen:
    return _engine(request).add_screen(screen)


@router.post("/screens/order", response_model=list[Screen], summary="Reihenfolge setzen")
def oled_reorder(order: ScreenOrder, request: Request) -> list[Screen]:
    return _engine(request).reorder_screens(order.ids)


@router.get("/screens/{screen_id}", response_model=Screen)
def oled_get_screen(screen_id: str, request: Request) -> Screen:
    try:
        return _engine(request)._screen_by_id(screen_id)
    except Exception as fehler:
        raise _fehler(fehler)


@router.put("/screens/{screen_id}", response_model=Screen)
def oled_update_screen(screen_id: str, screen: Screen, request: Request) -> Screen:
    try:
        return _engine(request).update_screen(screen_id, screen)
    except Exception as fehler:
        raise _fehler(fehler)


@router.delete("/screens/{screen_id}", response_model=Ok)
def oled_delete_screen(screen_id: str, request: Request) -> Ok:
    try:
        _engine(request).delete_screen(screen_id)
    except Exception as fehler:
        raise _fehler(fehler)
    return Ok()


@router.post("/screens/{screen_id}/duplicate", response_model=Screen, status_code=201)
def oled_duplicate_screen(screen_id: str, request: Request) -> Screen:
    try:
        return _engine(request).duplicate_screen(screen_id)
    except Exception as fehler:
        raise _fehler(fehler)


@router.post("/screens/{screen_id}/activate", response_model=OledSettings, summary="Bildschirm anzeigen")
def oled_activate_screen(screen_id: str, request: Request) -> OledSettings:
    try:
        return _engine(request).activate(screen_id)
    except Exception as fehler:
        raise _fehler(fehler)


# Vorlagen

@router.get("/presets", response_model=list[WidgetPreset])
def oled_presets(request: Request) -> list[WidgetPreset]:
    return list(_engine(request).presets)


@router.post("/presets", response_model=WidgetPreset, status_code=201)
def oled_add_preset(preset: WidgetPreset, request: Request) -> WidgetPreset:
    return _engine(request).add_preset(preset)


@router.put("/presets/{preset_id}", response_model=WidgetPreset)
def oled_update_preset(preset_id: str, preset: WidgetPreset, request: Request) -> WidgetPreset:
    try:
        return _engine(request).update_preset(preset_id, preset)
    except Exception as fehler:
        raise _fehler(fehler)


@router.delete("/presets/{preset_id}", response_model=Ok)
def oled_delete_preset(preset_id: str, request: Request) -> Ok:
    try:
        _engine(request).delete_preset(preset_id)
    except Exception as fehler:
        raise _fehler(fehler)
    return Ok()


# Profile

@router.get("/profiles", response_model=list[Profile])
def oled_profiles(request: Request) -> list[Profile]:
    return list(_engine(request).profiles)


@router.post("/profiles", response_model=Profile, status_code=201, summary="Aktuellen Stand als Profil sichern")
def oled_save_profile(daten: ProfileCreate, request: Request) -> Profile:
    return _engine(request).save_profile(daten.name)


@router.post("/profiles/{profile_id}/apply", response_model=OledSettings)
def oled_apply_profile(profile_id: str, request: Request) -> OledSettings:
    try:
        return _engine(request).apply_profile(profile_id)
    except Exception as fehler:
        raise _fehler(fehler)


@router.delete("/profiles/{profile_id}", response_model=Ok)
def oled_delete_profile(profile_id: str, request: Request) -> Ok:
    try:
        _engine(request).delete_profile(profile_id)
    except Exception as fehler:
        raise _fehler(fehler)
    return Ok()


# Wetterorte

@router.get("/weather/locations", response_model=list[WeatherLocationState])
def oled_weather_locations(request: Request) -> list[WeatherLocationState]:
    return _engine(request).weather_states()


@router.post("/weather/locations", response_model=WeatherLocation, status_code=201)
def oled_add_location(daten: WeatherLocationCreate, request: Request) -> WeatherLocation:
    return _engine(request).add_location(daten)


@router.delete("/weather/locations/{location_id}", response_model=Ok)
def oled_delete_location(location_id: str, request: Request) -> Ok:
    try:
        _engine(request).delete_location(location_id)
    except Exception as fehler:
        raise _fehler(fehler)
    return Ok()


@router.post("/weather/locations/{location_id}/default", response_model=WeatherSettings)
def oled_default_location(location_id: str, request: Request) -> WeatherSettings:
    try:
        return _engine(request).set_default_location(location_id)
    except Exception as fehler:
        raise _fehler(fehler)


@router.post("/weather/refresh", response_model=Ok, summary="Wetter neu laden (alle oder ein Ort)")
def oled_weather_refresh(request: Request, location_id: str | None = Query(None, alias="locationId")) -> Ok:
    try:
        _engine(request).refresh_weather(location_id)
    except Exception as fehler:
        raise _fehler(fehler)
    return Ok()


@router.get("/weather/search", response_model=list[GeocodeHit], summary="Ortssuche")
def oled_weather_search(request: Request, q: str = Query(min_length=2, max_length=80)) -> list[GeocodeHit]:
    try:
        return _engine(request).geocode(q)
    except Exception as fehler:
        raise HTTPException(status_code=502, detail=f"Ortssuche nicht erreichbar: {fehler}")


# Vorlagen (mitgeliefert)

@router.get("/templates", response_model=TemplateCatalog, summary="Mitgelieferte Bildschirm- und Widgetvorlagen")
def oled_templates() -> TemplateCatalog:
    return template_catalog()


@router.post("/templates/screens/{template_id}", response_model=Screen, status_code=201,
             summary="Bildschirmvorlage als neuen Bildschirm einfügen")
def oled_add_template_screen(template_id: str, request: Request) -> Screen:
    screen = screen_template(template_id)
    if screen is None:
        raise HTTPException(status_code=404, detail=f"Vorlage {template_id} nicht gefunden")
    return _engine(request).add_screen(screen)


@router.get("/templates/widgets/{template_id}", response_model=Widget,
            summary="Widgetvorlage mit neuer Kennung holen")
def oled_template_widget(template_id: str) -> Widget:
    widget = widget_template(template_id)
    if widget is None:
        raise HTTPException(status_code=404, detail=f"Vorlage {template_id} nicht gefunden")
    return widget


# Austausch

@router.get("/export", response_model=OledBundle, summary="Alles exportieren")
def oled_export(request: Request) -> OledBundle:
    return _engine(request).export_bundle()


@router.post("/import", response_model=ImportResult, summary="Export übernehmen")
def oled_import(bundle: OledBundle, request: Request, replace: bool = Query(False)) -> ImportResult:
    return _engine(request).import_bundle(bundle, replace)


class LegacyImport(BaseModel):
    """Sicherung des alten Editors (Browser-Speicher) in das Backend übernehmen."""
    screens: list[dict[str, Any]] = Field(default_factory=list)
    widget_presets: list[dict[str, Any]] = Field(default_factory=list, alias="widgetPresets")
    profiles: list[dict[str, Any]] = Field(default_factory=list)
    weather_cities: list[dict[str, Any]] = Field(default_factory=list, alias="weatherCities")
    rotation_interval: int | None = Field(None, alias="rotationInterval")

    model_config = {"populate_by_name": True}


@router.post("/import-legacy", response_model=ImportResult, summary="Alte Editor-Sicherung übernehmen")
def oled_import_legacy(daten: LegacyImport, request: Request, replace: bool = Query(False)) -> ImportResult:
    from oled.migrate import migrate_frontend_backup
    from oled.store import OledStore
    engine = _engine(request)
    pixel_dir = engine.store.data_dir / OledStore.LEGACY_PIXEL_DIR
    screens = [s for s in (migrate_screen(r, pixel_dir, i) for i, r in enumerate(daten.screens)) if s]
    presets, profiles, wetter = migrate_frontend_backup(
        {"widgetPresets": daten.widget_presets, "profiles": daten.profiles, "weatherCities": daten.weather_cities},
        pixel_dir,
    )
    settings = OledSettings(screens=screens, rotation_interval=daten.rotation_interval or 10)
    if replace and not screens:
        raise HTTPException(status_code=409, detail="Ersetzen ohne Bildschirme ist nicht erlaubt")
    bundle = OledBundle(settings=settings, presets=presets, profiles=profiles, weather=wetter)
    return engine.import_bundle(bundle, replace)


__all__ = ["router"]
