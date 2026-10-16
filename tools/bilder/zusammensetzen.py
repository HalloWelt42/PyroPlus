"""Setzt die rohen Aufnahmen zu den README-Bildern zusammen (Gerätebild, Tafeln mit Beschriftung).

Aufruf: python3 tools/bilder/zusammensetzen.py   (nach aufnehmen.mjs; schreibt nach .github/bilder)
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROH = Path(__file__).parent / "roh"
AUS = Path(__file__).resolve().parents[2] / ".github/bilder"
AUS.mkdir(parents=True, exist_ok=True)

SCHWARZ = (0, 0, 0)
TAFEL_HINTERGRUND = (31, 35, 39)
BESCHRIFTUNG = (168, 176, 186)
RAND = (62, 67, 74)
APP_HINTERGRUND = (0, 0, 0)

FONT_KANDIDATEN = [
    Path.home() / "Library/Fonts/Barlow-SemiBold.ttf",
    Path.home() / "Library/Fonts/Barlow-Medium.ttf",
    Path.home() / "Library/Fonts/ChakraPetch-SemiBold.ttf",
    Path.home() / "Library/Fonts/ChakraPetch-Medium.ttf",
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/System/Library/Fonts/Helvetica.ttc"),
]


def schrift(groesse: int) -> ImageFont.FreeTypeFont:
    for kandidat in FONT_KANDIDATEN:
        if kandidat.exists():
            return ImageFont.truetype(str(kandidat), groesse)
    return ImageFont.load_default()


def laden(name: str) -> Image.Image:
    return Image.open(ROH / f"{name}.png").convert("RGBA")


def ausschnitt(name: str, links: int, oben: int, rechts: int, unten: int) -> Image.Image:
    return laden(name).crop((links, oben, rechts, unten))


def breite_setzen(bild: Image.Image, breite: int) -> Image.Image:
    return bild.resize((breite, round(bild.height * breite / bild.width)), Image.LANCZOS)


def hoehe_setzen(bild: Image.Image, hoehe: int) -> Image.Image:
    return bild.resize((round(bild.width * hoehe / bild.height), hoehe), Image.LANCZOS)


def abrunden(bild: Image.Image, radius: int) -> Image.Image:
    maske = Image.new("L", bild.size, 0)
    ImageDraw.Draw(maske).rounded_rectangle((0, 0, bild.width - 1, bild.height - 1), radius=radius, fill=255)
    ergebnis = bild.copy()
    ergebnis.putalpha(maske)
    return ergebnis


def beschriften(zeichner: ImageDraw.ImageDraw, x: int, y: int, text: str, groesse: int = 26) -> None:
    """Großbuchstaben mit leichtem Buchstabenabstand, wie eine Tafelüberschrift."""
    f = schrift(groesse)
    for zeichen in text.upper():
        zeichner.text((x, y), zeichen, font=f, fill=BESCHRIFTUNG)
        x += int(zeichner.textlength(zeichen, font=f)) + 2


def laptop(bildschirm: Image.Image) -> Image.Image:
    """Rechner mit dunklem Rahmen und flachem Fuß."""
    rand, radius, fuss_hoehe, fuss_ueberstand = 22, 34, 26, 110
    breite = bildschirm.width + 2 * rand
    hoehe = bildschirm.height + 2 * rand
    geraet = Image.new("RGBA", (breite + 2 * fuss_ueberstand, hoehe + fuss_hoehe + 8), (0, 0, 0, 0))
    z = ImageDraw.Draw(geraet)
    z.rounded_rectangle((fuss_ueberstand, 0, fuss_ueberstand + breite - 1, hoehe - 1), radius=radius, fill=(22, 25, 29))
    z.rounded_rectangle((fuss_ueberstand + 1, 1, fuss_ueberstand + breite - 2, hoehe - 2), radius=radius, outline=(58, 63, 70), width=2)
    geraet.alpha_composite(abrunden(bildschirm, 10), (fuss_ueberstand + rand, rand))
    # Kamera
    z.ellipse((fuss_ueberstand + breite // 2 - 4, 7, fuss_ueberstand + breite // 2 + 4, 15), fill=(45, 50, 58))
    # Fuß
    z.rounded_rectangle((0, hoehe - 2, geraet.width - 1, hoehe + fuss_hoehe), radius=14, fill=(52, 57, 64))
    z.rectangle((0, hoehe - 2, geraet.width - 1, hoehe + 6), fill=(52, 57, 64))
    z.rounded_rectangle((geraet.width // 2 - 120, hoehe - 2, geraet.width // 2 + 120, hoehe + 8), radius=6, fill=(40, 44, 50))
    return geraet


def telefon(bildschirm: Image.Image, statusleiste: int = 54) -> Image.Image:
    """Telefon mit abgerundetem Rahmen; oben ein Streifen in der App-Farbe mit der Kamerainsel."""
    rand, radius = 16, 64
    schirm = Image.new("RGBA", (bildschirm.width, bildschirm.height + statusleiste), APP_HINTERGRUND + (255,))
    schirm.alpha_composite(bildschirm, (0, statusleiste))
    schirm = abrunden(schirm, radius - rand)
    geraet = Image.new("RGBA", (schirm.width + 2 * rand, schirm.height + 2 * rand), (0, 0, 0, 0))
    z = ImageDraw.Draw(geraet)
    z.rounded_rectangle((0, 0, geraet.width - 1, geraet.height - 1), radius=radius, fill=(44, 48, 55))
    z.rounded_rectangle((2, 2, geraet.width - 3, geraet.height - 3), radius=radius - 2, outline=(70, 76, 84), width=2)
    geraet.alpha_composite(schirm, (rand, rand))
    insel_breite, insel_hoehe = 120, 32
    links = geraet.width // 2 - insel_breite // 2
    z.rounded_rectangle((links, rand + 12, links + insel_breite, rand + 12 + insel_hoehe), radius=16, fill=(0, 0, 0))
    return geraet


def geraetebild() -> None:
    leinwand = Image.new("RGBA", (2400, 1400), SCHWARZ + (255,))
    rechner = laptop(breite_setzen(laden("editor"), 1600))
    handy = telefon(breite_setzen(laden("m-display"), 420))
    leinwand.alpha_composite(rechner, (90, 90))
    leinwand.alpha_composite(handy, (1830, 1400 - handy.height - 60))
    leinwand.convert("RGB").save(AUS / "geraete.png", optimize=True)


def tafeln(dateiname: str, teile: list[tuple[str, Image.Image]], breite: int = 2400, abstand: int = 40, hoehe: int | None = None) -> None:
    """Mehrere Bilder nebeneinander mit Überschrift; alle Teile bekommen dieselbe Höhe."""
    anzahl = len(teile)
    if hoehe is None:
        teil_breite = (breite - (anzahl + 1) * abstand) // anzahl
        skaliert = [(t, breite_setzen(b, teil_breite)) for t, b in teile]
    else:
        skaliert = [(t, hoehe_setzen(b, hoehe)) for t, b in teile]
        breite = sum(b.width for _, b in skaliert) + (anzahl + 1) * abstand
    kopf = 44
    hoehe_gesamt = max(b.height for _, b in skaliert)
    leinwand = Image.new("RGBA", (breite, abstand + kopf + hoehe_gesamt + abstand), TAFEL_HINTERGRUND + (255,))
    z = ImageDraw.Draw(leinwand)
    x = abstand
    for titel, bild in skaliert:
        beschriften(z, x + 2, abstand + 4, titel)
        rahmen = Image.new("RGBA", (bild.width + 2, bild.height + 2), RAND + (255,))
        rahmen = abrunden(rahmen, 26)
        rahmen.alpha_composite(abrunden(bild, 25), (1, 1))
        leinwand.alpha_composite(rahmen, (x, abstand + kopf))
        x += bild.width + abstand
    leinwand.convert("RGB").save(AUS / dateiname, optimize=True)


def main() -> None:
    geraetebild()
    # Rechner-Aufnahmen sind 2880 x 1800 (1440 x 900 bei doppelter Dichte)
    arbeitsbereich = (956, 248, 2880, 1800)
    tafeln("display.png", [
        ("Widget hinzufügen: Quelle, Darstellung, Symbol", ausschnitt("hinzufuegen", *arbeitsbereich)),
        ("Bausteine: fertige Widgets in echter Pixelgröße", ausschnitt("bausteine", *arbeitsbereich)),
    ])
    tafeln("pixel.png", [("Pixelbild zeichnen: Werkzeuge, Stiftbreite, Zuschneiden", ausschnitt("pixel", *arbeitsbereich))])
    tafeln("vorlagen.png", [("Bildschirmvorlagen: fertig, danach frei bearbeitbar", ausschnitt("vorlagen", 320, 106, 2560, 1682))])
    tafeln("luefter-leds.png", [
        ("Lüfter: Schwellwerte und Temperaturkurve", ausschnitt("fan", 482, 0, 2880, 1466)),
        ("LEDs: Farben, Effekte, Spielereien", ausschnitt("leds", 482, 0, 2880, 1466)),
    ])
    tafeln("handy.png", [
        ("Display", laden("m-display")),
        ("Vorlage einfügen", laden("m-vorlagen")),
        ("Lüfter", laden("m-fan")),
        ("LEDs", laden("m-leds")),
    ], hoehe=1000)
    for datei in sorted(AUS.glob("*.png")):
        bild = Image.open(datei)
        print(f"{datei.name}: {bild.size[0]} x {bild.size[1]}, {datei.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
