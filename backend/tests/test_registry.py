"""Registrierungen: jede Darstellungsart im Enum ist registriert und umgekehrt; Katalog ist vollständig."""

from datetime import datetime

from oled.catalog import build_catalog
from oled.models import DisplayMode, Tab, ValueType
from oled.modes import all_modes, get_mode
from oled.values import StatsSnapshot, all_sources, get_source, split_disk_source


def test_alle_darstellungsarten_registriert() -> None:
    registriert = {m.id for m in all_modes()}
    assert registriert == set(DisplayMode)


def test_jede_darstellungsart_hat_vorgaben_und_felder() -> None:
    for m in all_modes():
        assert m.label
        assert m.for_types
        for feld in m.fields:
            assert feld[0].islower() and "_" not in feld, f"{m.id}: Feld {feld} muss camelCase sein"


def test_quellen_decken_alle_reiter() -> None:
    reiter = {q.tab for q in all_sources()}
    assert reiter == set(Tab)


def test_laufwerksquelle_mit_index() -> None:
    assert split_disk_source("disk.used.2") == ("disk.used", 2)
    assert split_disk_source("cpu.temp") == ("cpu.temp", None)
    assert get_source("disk.percent.7") is not None
    assert get_source("gibt.es.nicht") is None


def test_katalog_faechert_laufwerke_auf(stats_dict: dict) -> None:
    katalog = build_catalog(StatsSnapshot.model_validate(stats_dict), datetime(2026, 10, 16, 12, 0), None)
    laufwerke = [q for q in katalog.sources if q.tab == Tab.disk]
    assert {q.id for q in laufwerke} >= {"disk.used.0", "disk.used.1", "disk.percent.1"}
    assert all(q.group for q in laufwerke)
    beispiel = next(q for q in katalog.sources if q.id == "cpu.temp")
    assert beispiel.example == "43.5"
    wetter = next(q for q in katalog.sources if q.id == "wetter.temp")
    assert wetter.uses_location
    assert {m.id for m in katalog.modes} == set(DisplayMode)
    assert len(katalog.tabs) == len(Tab)


def test_modus_passt_zur_wertart() -> None:
    text = get_mode(DisplayMode.text)
    assert text is not None and ValueType.time in text.for_types
    balken = get_mode(DisplayMode.balken)
    assert balken is not None and ValueType.string not in balken.for_types
