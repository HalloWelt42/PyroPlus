#!/usr/bin/env python3
"""
Gemeinsame Blöcke in die Mockup-Seiten einsetzen und prüfen.

Aufruf:
  tools/mockups-bloecke.py            alle Seiten unter mockups/*.html füllen
  tools/mockups-bloecke.py --pruefen  nur prüfen (Blöcke gleich, Textregeln), Exit 1 bei Verstoß

Marken in den Seiten:  <!-- block:NAME --> ... <!-- /block:NAME -->
Blockquellen:          mockups/_bloecke/NAME.html
Dateien mit Präfix _ sind Vorlagen, keine Seiten.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
MOCKUPS = WURZEL / "mockups"
BLOECKE = MOCKUPS / "_bloecke"
MARKE = re.compile(r"(<!-- block:([a-z0-9-]+) -->)(.*?)(<!-- /block:\2 -->)", re.S)

VERBOTEN = [
    ("!important", "kein !important"),
    ("—", "kein Gedankenstrich"),
    ("–", "kein Halbgeviertstrich"),
    ("„", "keine typografischen Anführungszeichen"),
    ("“", "keine typografischen Anführungszeichen"),
    ("’", "kein typografischer Apostroph"),
    ("border-left:", "keine einseitigen Ränder"),
    ("border-right:", "keine einseitigen Ränder"),
    ("https://cdn", "keine CDN-Verweise"),
]


def lese_bloecke() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8").strip() for p in BLOECKE.glob("*.html")}


def fuelle(seite: Path, bloecke: dict[str, str]) -> bool:
    inhalt = seite.read_text(encoding="utf-8")

    def ersetze(m: re.Match) -> str:
        name = m.group(2)
        if name not in bloecke:
            raise SystemExit(f"{seite.name}: Block '{name}' fehlt unter _bloecke/")
        return f"{m.group(1)}\n{bloecke[name]}\n{m.group(4)}"

    neu = MARKE.sub(ersetze, inhalt)
    if neu != inhalt:
        seite.write_text(neu, encoding="utf-8")
        return True
    return False


def pruefe(seite: Path, bloecke: dict[str, str]) -> list[str]:
    fehler: list[str] = []
    inhalt = seite.read_text(encoding="utf-8")
    for m in MARKE.finditer(inhalt):
        name, koerper = m.group(2), m.group(3).strip()
        if name not in bloecke:
            fehler.append(f"Block '{name}' unbekannt")
        elif koerper != bloecke[name]:
            fehler.append(f"Block '{name}' weicht von _bloecke/{name}.html ab")
    for muster, grund in VERBOTEN:
        if muster in inhalt:
            fehler.append(f"{grund} ('{muster}')")
    return fehler


def main() -> int:
    nur_pruefen = "--pruefen" in sys.argv
    bloecke = lese_bloecke()
    seiten = sorted(p for p in MOCKUPS.glob("*.html") if not p.name.startswith("_"))
    dateien = seiten + [MOCKUPS / "stil.css"] + sorted(BLOECKE.glob("*.html"))
    gesamt = 0
    if not nur_pruefen:
        for seite in seiten:
            if fuelle(seite, bloecke):
                print(f"gefüllt: {seite.name}")
    for datei in dateien:
        fehler = pruefe(datei, bloecke) if datei.suffix == ".html" else [
            g for m, g in VERBOTEN if m in datei.read_text(encoding="utf-8")]
        for f in fehler:
            print(f"{datei.name}: {f}")
        gesamt += len(fehler)
    print(f"{len(seiten)} Seiten, {gesamt} Verstöße")
    return 1 if gesamt else 0


if __name__ == "__main__":
    raise SystemExit(main())
