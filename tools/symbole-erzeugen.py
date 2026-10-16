#!/usr/bin/env python3
"""Erzeugt backend/oled/symbole_daten.py aus der Symbolschrift der Oberfläche.

Quelle: frontend/static/fonts/fa-solid-900.woff2 und fontawesome.min.css (Name zu Codepunkt).
Welche Symbole gerastert werden, bestimmt der Katalog in backend/oled/symbole.py.
Jedes Symbol wird groß gezeichnet, auf die Zielgröße verkleinert und auf 1 Bit
geschwellt; das Lüftersymbol zusätzlich in Drehbildern über eine volle Umdrehung.

Aufruf (aus dem Projektordner):
    backend/.venv/bin/python tools/symbole-erzeugen.py [--vorschau DATEI]
Braucht fonttools und brotli (backend/requirements-dev.txt).
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "backend"))

from oled.symbole import GROESSEN, KATALOG, LUEFTER_BILDER, LUEFTER_KENNUNG  # noqa: E402

SCHRIFT = WURZEL / "frontend/static/fonts/fa-solid-900.woff2"
STIL = WURZEL / "frontend/static/fonts/fontawesome.min.css"
ZIEL = WURZEL / "backend/oled/symbole_daten.py"
GROSS = 256                  # Rastergröße vor dem Verkleinern
SCHWELLE = {8: 140, 16: 136, 24: 132, 32: 128}   # kleine Größen härter schwellen, damit Lücken bleiben


def codepunkte() -> dict[str, int]:
    css = STIL.read_text(encoding="utf-8")
    namen: dict[str, int] = {}
    for selektoren, code in re.findall(r'((?:\.fa-[a-z0-9-]+(?:::?before)?,?)+)\{content:"\\([0-9a-f]+)"\}', css):
        for name in re.findall(r"\.fa-([a-z0-9-]+)", selektoren):
            namen[name] = int(code, 16)
    return namen


def schrift_laden() -> ImageFont.FreeTypeFont:
    from fontTools.ttLib import TTFont
    font = TTFont(str(SCHRIFT))
    font.flavor = None
    puffer = io.BytesIO()
    font.save(puffer)
    puffer.seek(0)
    return ImageFont.truetype(puffer, GROSS)


def glyphe_gross(schrift: ImageFont.FreeTypeFont, zeichen: str) -> Image.Image:
    """Glyphe in Graustufen, auf den Inhalt zugeschnitten."""
    leinwand = Image.new("L", (GROSS * 2, GROSS * 2), 0)
    ImageDraw.Draw(leinwand).text((GROSS // 2, GROSS // 2), zeichen, font=schrift, fill=255)
    rahmen = leinwand.getbbox()
    if not rahmen:
        raise ValueError(f"leere Glyphe {zeichen!r}")
    return leinwand.crop(rahmen)


def quadratisch(bild: Image.Image, rand: int = 0) -> Image.Image:
    seite = max(bild.size) + 2 * rand
    q = Image.new("L", (seite, seite), 0)
    q.paste(bild, ((seite - bild.width) // 2, (seite - bild.height) // 2))
    return q


def rastern(bild: Image.Image, groesse: int) -> list[str]:
    """Verkleinert ein Graustufenbild proportional auf groesse x groesse und schwellt auf 1 Bit."""
    faktor = groesse / max(bild.size)
    neu = bild.resize((max(1, round(bild.width * faktor)), max(1, round(bild.height * faktor))), Image.LANCZOS)
    zelle = Image.new("L", (groesse, groesse), 0)
    zelle.paste(neu, ((groesse - neu.width) // 2, (groesse - neu.height) // 2))
    schwelle = SCHWELLE[groesse]
    return ["".join("1" if zelle.getpixel((x, y)) >= schwelle else "0" for x in range(groesse)) for y in range(groesse)]


def packen(zeilen: list[str]) -> str:
    daten = bytearray()
    for zeile in zeilen:
        for i in range(0, len(zeile), 8):
            daten.append(int(zeile[i:i + 8].ljust(8, "0"), 2))
    return daten.hex()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vorschau", help="Textdatei mit allen Symbolen als ASCII-Bild")
    args = parser.parse_args()

    punkte = codepunkte()
    schrift = schrift_laden()
    symbole: dict[str, dict[int, str]] = {}
    vorschau: list[str] = []
    fehlend: list[str] = []
    for s in KATALOG:
        if s.glyphe not in punkte:
            fehlend.append(f"{s.id} ({s.glyphe})")
            continue
        gross = glyphe_gross(schrift, chr(punkte[s.glyphe]))
        symbole[s.id] = {}
        for g in GROESSEN:
            zeilen = rastern(gross, g)
            symbole[s.id][g] = packen(zeilen)
            if args.vorschau and g in (8, 16):
                vorschau.append(f"{s.id} {g}:")
                vorschau.extend("".join("#" if b == "1" else "." for b in z) for z in zeilen)
                vorschau.append("")
    if fehlend:
        print("Nicht in der Schrift:", ", ".join(fehlend), file=sys.stderr)

    # Lüfter: Drehbilder aus der großen Glyphe, Drehung um die Mitte
    luefter_def = next(s for s in KATALOG if s.id == LUEFTER_KENNUNG)
    basis = quadratisch(glyphe_gross(schrift, chr(punkte[luefter_def.glyphe])), rand=GROSS // 4)
    luefter: dict[int, list[str]] = {g: [] for g in GROESSEN}
    for i in range(LUEFTER_BILDER):
        winkel = -360.0 * i / LUEFTER_BILDER
        gedreht = basis.rotate(winkel, resample=Image.BICUBIC, expand=False)
        rahmen = gedreht.getbbox()
        inhalt = gedreht.crop(rahmen) if rahmen else gedreht
        for g in GROESSEN:
            luefter[g].append(packen(rastern(quadratisch(inhalt), g)))

    zeilen_aus = [
        '"""Erzeugt von tools/symbole-erzeugen.py, nicht von Hand ändern."""',
        "",
        "# Symbolkennung -> Größe -> Zeilen als Hex (jede Zeile beginnt an einer Bytegrenze)",
        "SYMBOLE: dict[str, dict[int, str]] = {",
    ]
    for id_, groessen in symbole.items():
        zeilen_aus.append(f"    {id_!r}: {{")
        for g, hexdaten in groessen.items():
            zeilen_aus.append(f"        {g}: {hexdaten!r},")
        zeilen_aus.append("    },")
    zeilen_aus.append("}")
    zeilen_aus.append("")
    zeilen_aus.append(f"# Lüfter: Größe -> {LUEFTER_BILDER} Drehbilder über eine Umdrehung")
    zeilen_aus.append("LUEFTER: dict[int, tuple[str, ...]] = {")
    for g, bilder in luefter.items():
        zeilen_aus.append(f"    {g}: (")
        zeilen_aus.extend(f"        {b!r}," for b in bilder)
        zeilen_aus.append("    ),")
    zeilen_aus.append("}")
    ZIEL.write_text("\n".join(zeilen_aus) + "\n", encoding="utf-8")
    print(f"{len(symbole)} Symbole in {len(GROESSEN)} Größen, Lüfter mit {LUEFTER_BILDER} Drehbildern -> {ZIEL.relative_to(WURZEL)}")
    if args.vorschau:
        Path(args.vorschau).write_text("\n".join(vorschau), encoding="utf-8")
        print(f"Vorschau: {args.vorschau}")


if __name__ == "__main__":
    main()
