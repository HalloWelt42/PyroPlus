"""
PyroPlus: Katalog für die Oberfläche.

Erzeugt aus den Registrierungen in values.py und modes.py die Liste der Reiter,
Datenquellen (je Laufwerk aufgefächert) und Darstellungsarten. Die Oberfläche
kennt keine Quelle und keine Darstellungsart, die hier nicht steht.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from oled.models import Catalog, DisplayModeInfo, SourceInfo, SymbolInfo, Tab, TabInfo, ValueType
from oled.modes import all_modes
from oled.symbole import GROESSEN, KATEGORIEN, alle_symbole
from oled.values import StatsSnapshot, ValueContext, all_sources, resolve
from oled.weather import WeatherReport

TAB_LABELS: dict[Tab, str] = {
    Tab.cpu: "CPU",
    Tab.ram: "Arbeitsspeicher",
    Tab.disk: "Laufwerke",
    Tab.net: "Netzwerk",
    Tab.fan: "Lüfter",
    Tab.zeit: "Zeiten",
    Tab.wetter: "Wetter",
    Tab.text: "Texte",
    Tab.layout: "Layout",
}


def build_catalog(stats: StatsSnapshot, now: datetime,
                  weather: Optional[WeatherReport]) -> Catalog:
    quellen: list[SourceInfo] = []
    for definition in all_sources():
        if definition.per_disk:
            for index, disk in enumerate(stats.disks):
                gruppe = f"{disk.label or disk.mount or 'Laufwerk ' + str(index)} ({disk.mount})"
                kennung = f"{definition.id}.{index}"
                quellen.append(SourceInfo(
                    id=kennung, tab=definition.tab, label=definition.label, unit=definition.unit,
                    value_type=definition.value_type, description=definition.description,
                    group=gruppe, example=_beispiel(kennung, stats, now, weather),
                ))
            continue
        quellen.append(SourceInfo(
            id=definition.id, tab=definition.tab, label=definition.label, unit=definition.unit,
            value_type=definition.value_type, description=definition.description,
            uses_location=definition.uses_location,
            example=_beispiel(definition.id, stats, now, weather),
        ))

    arten = [
        DisplayModeInfo(id=m.id, label=m.label, description=m.description, for_types=m.for_types,
                        fields=m.fields, defaults=m.defaults, variants=m.variants)
        for m in all_modes()
    ]
    reiter = [TabInfo(id=tab, label=TAB_LABELS[tab]) for tab in Tab]
    symbole = [SymbolInfo(id=s.id, label=s.label, category=s.kategorie) for s in alle_symbole()]
    return Catalog(tabs=reiter, sources=quellen, modes=arten, symbols=symbole,
                   symbol_categories=list(KATEGORIEN), symbol_sizes=list(GROESSEN))


def _beispiel(source_id: str, stats: StatsSnapshot, now: datetime,
              weather: Optional[WeatherReport]) -> str:
    try:
        wert = resolve(source_id, ValueContext(stats=stats, now=now, weather=weather))
    except Exception:
        return ""
    if wert.text:
        return wert.text
    return ""


def value_type_of(source_id: str) -> Optional[ValueType]:
    from oled.values import get_source
    definition = get_source(source_id)
    return definition.value_type if definition else None
