"""
PyroPlus: Symbolbibliothek für das Display.

Alle Symbole kommen aus einer Quelle: der mitgelieferten Symbolschrift der
Oberfläche. Das Werkzeug tools/symbole-erzeugen.py rastert daraus je Symbol
Pixelbilder in festen Größen und schreibt sie nach oled/symbole_daten.py.
Dieses Modul kennt den Katalog (Kennung, Name, Gruppe, Glyphe) und zeichnet.

Das Lüftersymbol liegt zusätzlich als Folge von Drehbildern vor, damit es sich
flüssig mit der Drehzahl dreht.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

GROESSEN: tuple[int, ...] = (8, 16, 24, 32)
LUEFTER_BILDER = 32          # Drehbilder je Größe über eine volle Umdrehung
LUEFTER_KENNUNG = "luefter"


@dataclass(frozen=True)
class SymbolDef:
    id: str
    label: str
    kategorie: str
    glyphe: str              # Name in der Symbolschrift


# Reihenfolge = Reihenfolge in der Oberfläche
_KATALOG: list[SymbolDef] = []


def _s(kategorie: str, *eintraege: tuple[str, str, str]) -> None:
    for id_, label, glyphe in eintraege:
        _KATALOG.append(SymbolDef(id_, label, kategorie, glyphe))


_s("Wetter",
   ("sonne", "Sonne", "sun"), ("mond", "Mond", "moon"), ("wolke", "Wolke", "cloud"),
   ("wolke_sonne", "Wolke mit Sonne", "cloud-sun"), ("wolke_mond", "Wolke mit Mond", "cloud-moon"),
   ("regen", "Regen", "cloud-rain"), ("starkregen", "Starkregen", "cloud-showers-heavy"),
   ("sonne_regen", "Sonne und Regen", "cloud-sun-rain"), ("gewitter", "Gewitter", "cloud-bolt"),
   ("schnee", "Schnee", "snowflake"), ("nebel", "Nebel", "smog"), ("wind", "Wind", "wind"),
   ("tornado", "Tornado", "tornado"), ("regenbogen", "Regenbogen", "rainbow"),
   ("tropfen", "Tropfen", "droplet"), ("wasser", "Wasser", "water"), ("schirm", "Schirm", "umbrella"),
   ("thermometer", "Thermometer", "temperature-half"), ("thermometer_heiss", "Thermometer heiß", "temperature-high"),
   ("thermometer_kalt", "Thermometer kalt", "temperature-low"))
_s("System",
   ("chip", "Prozessor", "microchip"), ("speicher", "Arbeitsspeicher", "memory"),
   ("laufwerk", "Laufwerk", "hard-drive"), ("server", "Server", "server"), ("luefter", "Lüfter", "fan"),
   ("tacho", "Tacho", "gauge-high"), ("blitz", "Blitz", "bolt"), ("stecker", "Stecker", "plug"),
   ("strom", "Ein/Aus", "power-off"), ("batterie_halb", "Batterie halb", "battery-half"),
   ("batterie_voll", "Batterie voll", "battery-full"), ("zahnrad", "Zahnrad", "gear"),
   ("datenbank", "Datenbank", "database"), ("terminal", "Terminal", "terminal"), ("code", "Code", "code"),
   ("diskette", "Diskette", "floppy-disk"), ("sd_karte", "Speicherkarte", "sd-card"),
   ("bildschirm", "Bildschirm", "display"), ("tastatur", "Tastatur", "keyboard"))
_s("Netzwerk",
   ("netzwerk", "Netzwerk", "network-wired"), ("wlan", "WLAN", "wifi"), ("globus", "Globus", "globe"),
   ("pfeil_hoch", "Pfeil hoch", "arrow-up"), ("pfeil_runter", "Pfeil runter", "arrow-down"),
   ("pfeile", "Pfeile hin und her", "arrow-right-arrow-left"), ("download", "Download", "download"),
   ("upload", "Upload", "upload"), ("signal", "Signal", "signal"), ("ethernet", "Ethernet", "ethernet"),
   ("rss", "Feed", "rss"), ("wolke_runter", "Aus der Wolke", "cloud-arrow-down"),
   ("wolke_hoch", "In die Wolke", "cloud-arrow-up"), ("satellit", "Satellitenschüssel", "satellite-dish"))
_s("Zeit",
   ("uhr", "Uhr", "clock"), ("kalender", "Kalender", "calendar-days"), ("sanduhr", "Sanduhr", "hourglass-half"),
   ("stoppuhr", "Stoppuhr", "stopwatch"), ("glocke", "Glocke", "bell"))
_s("Status",
   ("haken", "Haken", "check"), ("kreuz", "Kreuz", "xmark"), ("warnung", "Warnung", "triangle-exclamation"),
   ("info", "Info", "circle-info"), ("haken_kreis", "Haken im Kreis", "circle-check"),
   ("schloss", "Schloss", "lock"), ("schloss_offen", "Schloss offen", "lock-open"), ("auge", "Auge", "eye"),
   ("herz", "Herz", "heart"), ("stern", "Stern", "star"), ("haus", "Haus", "house"), ("feuer", "Feuer", "fire"),
   ("flagge", "Flagge", "flag"), ("schild", "Schild", "shield-halved"), ("standort", "Standort", "location-dot"),
   ("gluehbirne", "Glühbirne", "lightbulb"), ("play", "Wiedergabe", "play"), ("pause", "Pause", "pause"),
   ("stopp", "Stopp", "stop"), ("lautsprecher", "Lautsprecher", "volume-high"), ("stumm", "Stumm", "volume-xmark"),
   ("kreis", "Kreis", "circle"), ("quadrat", "Quadrat", "square"))
_s("Deko",
   ("musik", "Musik", "music"), ("geschenk", "Geschenk", "gift"), ("baum", "Baum", "tree"),
   ("katze", "Katze", "cat"), ("hund", "Hund", "dog"), ("pfote", "Pfote", "paw"), ("schneemann", "Schneemann", "snowman"),
   ("rakete", "Rakete", "rocket"), ("gamepad", "Gamepad", "gamepad"), ("tasse", "Tasse", "mug-saucer"),
   ("smiley", "Smiley", "face-smile"), ("totenkopf", "Totenkopf", "skull"), ("geist", "Geist", "ghost"),
   ("pokal", "Pokal", "trophy"), ("krone", "Krone", "crown"), ("diamant", "Diamant", "gem"),
   ("puzzle", "Puzzle", "puzzle-piece"), ("roboter", "Roboter", "robot"), ("atom", "Atom", "atom"),
   ("drache", "Drache", "dragon"), ("pizza", "Pizza", "pizza-slice"), ("keks", "Keks", "cookie"),
   ("kuchen", "Kuchen", "cake-candles"), ("zuckerstange", "Zuckerstange", "candy-cane"),
   ("zauberhut", "Zauberhut", "hat-wizard"), ("blatt", "Blatt", "leaf"), ("berg", "Berg", "mountain"),
   ("fahrrad", "Fahrrad", "bicycle"), ("auto", "Auto", "car"), ("flugzeug", "Flugzeug", "plane"),
   ("zug", "Zug", "train"), ("schiff", "Schiff", "ship"), ("kamera", "Kamera", "camera"),
   ("brief", "Brief", "envelope"), ("telefon", "Telefon", "phone"), ("nutzer", "Person", "user"),
   ("schluessel", "Schlüssel", "key"), ("werkzeug", "Schraubenschlüssel", "wrench"),
   ("medaille", "Medaille", "medal"), ("wuerfel", "Würfel", "dice"), ("magnet", "Magnet", "magnet"),
   ("kolben", "Kolben", "flask"), ("radioaktiv", "Radioaktiv", "radiation"), ("virus", "Virus", "virus"),
   ("recycling", "Recycling", "recycle"), ("bombe", "Bombe", "bomb"), ("eis", "Eis", "ice-cream"),
   ("burger", "Burger", "burger"), ("apfel", "Apfel", "apple-whole"), ("karotte", "Karotte", "carrot"),
   ("weinglas", "Weinglas", "wine-glass"), ("bier", "Bier", "beer-mug-empty"))

KATALOG: tuple[SymbolDef, ...] = tuple(_KATALOG)
_NACH_ID: dict[str, SymbolDef] = {s.id: s for s in KATALOG}
KATEGORIEN: tuple[str, ...] = tuple(dict.fromkeys(s.kategorie for s in KATALOG))


def alle_symbole() -> tuple[SymbolDef, ...]:
    return KATALOG


def symbol(id_: str) -> Optional[SymbolDef]:
    return _NACH_ID.get(id_)


def passende_groesse(gewuenscht: Optional[int]) -> int:
    """Nächste vorhandene Größe, nie größer als gewünscht (mindestens die kleinste)."""
    wunsch = gewuenscht or 16
    passend = [g for g in GROESSEN if g <= wunsch]
    return passend[-1] if passend else GROESSEN[0]


# Vorgaben: welches Symbol zu einer Datenquelle passt (für "Symbol + Wert")

_QUELLEN_SYMBOLE: dict[str, str] = {
    "cpu.temp": "thermometer", "cpu.temp_min": "thermometer_kalt", "cpu.temp_max": "thermometer_heiss",
    "cpu.temp_range": "thermometer", "cpu.temp_pct": "thermometer", "cpu.percent": "chip",
    "cpu.cores": "chip", "cpu.load": "tacho",
    "fan.rpm": "luefter", "fan.duty": "luefter", "fan.level": "luefter", "fan.case": "luefter",
    "fan.mode": "luefter", "fan.rpm_pct": "luefter", "fan.pwm_level": "luefter",
    "net.rx": "download", "net.tx": "upload", "net.rx_raw": "download", "net.tx_raw": "upload",
    "net.traffic": "pfeile", "net.ip": "netzwerk", "net.interface": "ethernet", "net.hostname": "server",
    "wetter.temp": "thermometer", "wetter.gefuehlt": "thermometer", "wetter.wind": "wind",
    "wetter.windricht": "wind", "wetter.boeen": "wind", "wetter.druck": "tacho", "wetter.druck_msl": "tacho",
    "wetter.niederschlag": "regen", "wetter.feuchte": "tropfen", "wetter.wolken": "wolke",
    "wetter.zustand": "wolke_sonne", "wetter.tag_nacht": "sonne", "wetter.ort": "standort",
    "wetter.sunrise": "sonne", "wetter.sunset": "mond", "wetter.kombi": "wolke_sonne",
    "wetter.wind_kombi": "wind",
    "zeit.uptime": "stoppuhr", "zeit.uptime_s": "stoppuhr", "zeit.datum": "kalender",
    "zeit.datum_kurz": "kalender", "zeit.tag": "kalender", "zeit.tag_lang": "kalender",
    "zeit.tag_datum": "kalender", "zeit.jahr": "kalender",
}
_TAB_SYMBOLE: dict[str, str] = {
    "cpu": "chip", "ram": "speicher", "disk": "laufwerk", "net": "netzwerk", "fan": "luefter",
    "zeit": "uhr", "wetter": "wolke_sonne", "text": "info", "layout": "quadrat",
}


def vorgabe_fuer_quelle(quelle_id: str) -> str:
    """Symbol, das zu einer Datenquelle passt; Laufwerke sind je Index aufgefächert."""
    if quelle_id in _QUELLEN_SYMBOLE:
        return _QUELLEN_SYMBOLE[quelle_id]
    tab = quelle_id.split(".", 1)[0]
    return _TAB_SYMBOLE.get(tab, "info")


# Wetterzustand (Text aus dem Wetterbericht) zu Symbol

def symbol_fuer_wetter(zustand: str, nacht: bool = False) -> str:
    z = (zustand or "").lower()
    if "gewitter" in z or "thunder" in z:
        return "gewitter"
    if "schnee" in z or "snow" in z or "graupel" in z:
        return "schnee"
    if ("stark" in z and "regen" in z) or "heavy" in z or "schauer" in z:
        return "starkregen"
    if "regen" in z or "rain" in z or "niesel" in z or "drizzle" in z:
        return "regen"
    if "nebel" in z or "fog" in z or "mist" in z or "dunst" in z:
        return "nebel"
    if "bedeckt" in z or "bewölkt" in z and "leicht" not in z or "overcast" in z:
        return "wolke"
    if "wolk" in z or "cloud" in z or "heiter" in z:
        return "wolke_mond" if nacht else "wolke_sonne"
    return "mond" if nacht else "sonne"


# Zeichnen

@lru_cache(maxsize=None)
def _zeilen(id_: str, groesse: int) -> tuple[str, ...]:
    """Zeilen aus 0/1 für ein Symbol in einer vorhandenen Größe."""
    from oled import symbole_daten
    hex_daten = symbole_daten.SYMBOLE.get(id_, {}).get(groesse)
    return _entpacken(hex_daten, groesse) if hex_daten else ()


@lru_cache(maxsize=None)
def _luefter_zeilen(groesse: int, bild: int) -> tuple[str, ...]:
    from oled import symbole_daten
    bilder = symbole_daten.LUEFTER.get(groesse, ())
    if not bilder:
        return ()
    return _entpacken(bilder[bild % len(bilder)], groesse)


def _entpacken(hex_daten: str, groesse: int) -> tuple[str, ...]:
    daten = bytes.fromhex(hex_daten)
    breite_bytes = (groesse + 7) // 8
    zeilen: list[str] = []
    for y in range(groesse):
        bits = "".join(f"{daten[y * breite_bytes + i]:08b}" for i in range(breite_bytes))
        zeilen.append(bits[:groesse])
    return tuple(zeilen)


def _malen(buf: bytearray, zeilen: tuple[str, ...], x: int, y: int) -> None:
    from oled.renderer import set_pixel
    for ry, zeile in enumerate(zeilen):
        for rx, bit in enumerate(zeile):
            if bit == "1":
                set_pixel(buf, x + rx, y + ry, 1)


def draw_symbol(buf: bytearray, id_: str, x: int, y: int, groesse: Optional[int] = None) -> int:
    """Zeichnet ein Symbol; liefert die tatsächlich verwendete Größe."""
    g = passende_groesse(groesse)
    _malen(buf, _zeilen(id_, g), x, y)
    return g


def draw_luefter(buf: bytearray, x: int, y: int, groesse: Optional[int], bild: int) -> int:
    """Zeichnet das Lüftersymbol im Drehbild `bild` (0 bis LUEFTER_BILDER - 1)."""
    g = passende_groesse(groesse)
    _malen(buf, _luefter_zeilen(g, bild), x, y)
    return g
