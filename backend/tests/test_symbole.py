"""Symbolbibliothek: Katalog vollständig, Daten je Größe vorhanden, Lüfter dreht, Zuordnungen."""

from oled import symbole_daten
from oled.renderer import create_buffer
from oled.symbole import (
    GROESSEN, KATALOG, KATEGORIEN, LUEFTER_BILDER, draw_luefter, draw_symbol, passende_groesse,
    symbol, symbol_fuer_wetter, vorgabe_fuer_quelle,
)


def _gesetzt(buf: bytearray) -> int:
    return sum(1 for b in buf if b)


def test_jedes_symbol_hat_alle_groessen() -> None:
    assert len(KATALOG) >= 100
    for s in KATALOG:
        daten = symbole_daten.SYMBOLE.get(s.id)
        assert daten, f"{s.id} fehlt in den erzeugten Daten"
        for g in GROESSEN:
            assert g in daten, f"{s.id}: Größe {g} fehlt"
            buf = create_buffer()
            assert draw_symbol(buf, s.id, 0, 0, g) == g
            assert _gesetzt(buf) > 0, f"{s.id} in {g} ist leer"
            assert all(not buf[y * 128 + x] for y in range(64) for x in range(g, 128)), f"{s.id} ragt über {g} hinaus"


def test_kennungen_und_kategorien_eindeutig() -> None:
    ids = [s.id for s in KATALOG]
    assert len(ids) == len(set(ids))
    assert set(s.kategorie for s in KATALOG) == set(KATEGORIEN)
    assert symbol("luefter") is not None and symbol("gibt_es_nicht") is None


def test_luefter_drehbilder_unterscheiden_sich() -> None:
    for g in GROESSEN:
        bilder = symbole_daten.LUEFTER[g]
        assert len(bilder) == LUEFTER_BILDER
        erster, zweiter = create_buffer(), create_buffer()
        draw_luefter(erster, 0, 0, g, 0)
        draw_luefter(zweiter, 0, 0, g, 3)
        assert _gesetzt(erster) > 0 and erster != zweiter


def test_groessenwahl_rundet_nach_unten() -> None:
    assert passende_groesse(None) == 16
    assert passende_groesse(12) == 8
    assert passende_groesse(24) == 24
    assert passende_groesse(48) == 32
    assert passende_groesse(4) == 8


def test_unbekanntes_symbol_zeichnet_nichts() -> None:
    buf = create_buffer()
    draw_symbol(buf, "gibt_es_nicht", 0, 0, 16)
    assert _gesetzt(buf) == 0


def test_vorgaben_fuer_quellen() -> None:
    assert vorgabe_fuer_quelle("cpu.temp") == "thermometer"
    assert vorgabe_fuer_quelle("disk.percent.1") == "laufwerk"
    assert vorgabe_fuer_quelle("zeit.uhr") == "uhr"
    assert symbol(vorgabe_fuer_quelle("irgendwas.neues")) is not None


def test_wetterzustand_zu_symbol() -> None:
    assert symbol_fuer_wetter("Gewitter") == "gewitter"
    assert symbol_fuer_wetter("Leichter Regen") == "regen"
    assert symbol_fuer_wetter("Klar", nacht=True) == "mond"
    assert symbol_fuer_wetter("Bewölkt") == "wolke"
    assert symbol(symbol_fuer_wetter("")) is not None
