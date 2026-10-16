"""
PyroPlus: Pixel-Primitive auf dem 1-Bit-Puffer (128x64).
Reine Pixel-Operationen auf bytearray; PIL nur für die PNG-Ausgabe.
"""

from oled.font import FONT, CHAR_SPACING, get_glyph

W, H = 128, 64


def create_buffer() -> bytearray:
    """Leeren Pixel-Buffer erstellen."""
    return bytearray(W * H)


def set_pixel(buf: bytearray, x: int, y: int, val: int = 1):
    """Einzelnes Pixel setzen."""
    if 0 <= x < W and 0 <= y < H:
        buf[y * W + x] = val


def get_pixel(buf: bytearray, x: int, y: int) -> int:
    """Pixel-Wert lesen."""
    if 0 <= x < W and 0 <= y < H:
        return buf[y * W + x]
    return 0


def draw_text(buf: bytearray, text: str, sx: int, sy: int,
              scale_x: int = 1, scale_y: int | None = None):
    """Text mit Bitmap-Font rendern. Identisch zum Frontend."""
    if scale_y is None:
        scale_y = scale_x
    cx = sx
    for ch in text:
        rows = get_glyph(ch)
        if rows is None:
            cx += 4 * scale_x
            continue
        for ry, row in enumerate(rows):
            for rx in range(len(row)):
                if row[rx] == '1':
                    for dy in range(scale_y):
                        for dx in range(scale_x):
                            px = cx + rx * scale_x + dx
                            py = sy + ry * scale_y + dy
                            if 0 <= px < W and 0 <= py < H:
                                buf[py * W + px] = 1
        cx += CHAR_SPACING * scale_x


def draw_text_ex(buf: bytearray, text: str, x: int, y: int,
                  scale_x: int = 1, scale_y: int = 1,
                  invert: bool = False, border: bool = False,
                  align: str = "left", box_w: int = 0):
    """Erweitertes Text-Rendering mit Invert, Rahmen und Ausrichtung.

    invert: Weisser Hintergrund, schwarzer Text
    border: 1px Rahmen um die Textbox
    align:  'left', 'center', 'right' (innerhalb box_w)
    box_w:  Breite der Ausrichtungs-Box (0 = auto)
    """
    char_count = len(text)
    text_w = max(1, char_count * CHAR_SPACING * scale_x - scale_x)
    text_h = 7 * scale_y
    # Padding fuer Invert / Border
    pad = 1 if (invert or border) else 0
    total_w = (box_w if box_w > 0 else text_w) + pad * 2
    total_h = text_h + pad * 2

    # Ausrichtung berechnen
    if box_w > 0 and align == "center":
        tx = x + pad + (box_w - text_w) // 2
    elif box_w > 0 and align == "right":
        tx = x + pad + box_w - text_w
    else:
        tx = x + pad

    # Invert: Weisser Block
    if invert:
        for dy in range(total_h):
            for dx in range(total_w):
                set_pixel(buf, x + dx, y + dy, 1)
        # Text als 0 (schwarz auf weiss)
        _draw_text_val(buf, text, tx, y + pad, scale_x, scale_y, 0)
    else:
        draw_text(buf, text, tx, y + pad, scale_x, scale_y)

    # Rahmen
    if border and not invert:
        # Oben + Unten
        for dx in range(total_w):
            set_pixel(buf, x + dx, y, 1)
            set_pixel(buf, x + dx, y + total_h - 1, 1)
        # Links + Rechts
        for dy in range(total_h):
            set_pixel(buf, x, y + dy, 1)
            set_pixel(buf, x + total_w - 1, y + dy, 1)


def _draw_text_val(buf: bytearray, text: str, sx: int, sy: int,
                   scale_x: int, scale_y: int, val: int):
    """Text mit beliebigem Pixel-Wert (0 oder 1) zeichnen."""
    cx = sx
    for ch in text:
        rows = get_glyph(ch)
        if rows is None:
            cx += 4 * scale_x
            continue
        for ry, row in enumerate(rows):
            for rx in range(len(row)):
                if row[rx] == '1':
                    for dy in range(scale_y):
                        for dx in range(scale_x):
                            px = cx + rx * scale_x + dx
                            py = sy + ry * scale_y + dy
                            if 0 <= px < W and 0 <= py < H:
                                buf[py * W + px] = val
        cx += CHAR_SPACING * scale_x


def draw_line(buf: bytearray, x0: int, y0: int, x1: int, y1: int):
    """Bresenham-Linie."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        set_pixel(buf, x0, y0, 1)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def draw_rect(buf: bytearray, x0: int, y0: int, x1: int, y1: int, filled: bool = False):
    """Rechteck (Outline oder gefuellt)."""
    a, b = min(x0, x1), min(y0, y1)
    c, d = max(x0, x1), max(y0, y1)
    if filled:
        for y in range(b, d + 1):
            for x in range(a, c + 1):
                set_pixel(buf, x, y, 1)
    else:
        for x in range(a, c + 1):
            set_pixel(buf, x, b, 1)
            set_pixel(buf, x, d, 1)
        for y in range(b + 1, d):
            set_pixel(buf, a, y, 1)
            set_pixel(buf, c, y, 1)


def draw_bar(buf: bytearray, x: int, y: int, w: int, h: int, pct: float):
    """Fortschrittsbalken mit Rahmen + Fuellung."""
    # Rahmen
    draw_rect(buf, x, y, x + w - 1, y + h - 1, filled=False)
    # Fuellung
    fw = round((w - 2) * min(1.0, max(0.0, pct / 100.0)))
    for j in range(1, h - 1):
        for i in range(fw):
            set_pixel(buf, x + 1 + i, y + j, 1)


def draw_hline(buf: bytearray, x: int, y: int, length: int):
    """Horizontale Linie."""
    for i in range(length):
        set_pixel(buf, x + i, y, 1)


def draw_vline(buf: bytearray, x: int, y: int, length: int):
    """Vertikale Linie."""
    for i in range(length):
        set_pixel(buf, x, y + i, 1)


def draw_marquee(buf: bytearray, text: str, y: int, offset: int, scale: int = 1):
    """Laufschrift."""
    total_w = len(text) * CHAR_SPACING * scale
    x = W - (offset % (total_w + W))
    draw_text(buf, text, x, y, scale)


def draw_sparkline(buf: bytearray, values: list, x: int, y: int, w: int, h: int, filled: bool = False):
    """Verlaufsgraph mit Rahmen; mit filled wird die Fläche unter der Linie gefüllt."""
    if not values or len(values) < 2:
        draw_rect(buf, x, y, x + w - 1, y + h - 1, filled=False)
        return
    mx = max(max(values), 1)
    mn = min(min(values), 0)
    rng = mx - mn or 1
    step = (w - 3) / (len(values) - 1)
    boden = y + h - 2
    draw_rect(buf, x, y, x + w - 1, y + h - 1, filled=False)
    punkte = [(round(x + 1 + i * step), round(boden - ((v - mn) / rng) * (h - 3))) for i, v in enumerate(values)]
    for (x0, y0), (x1, y1) in zip(punkte, punkte[1:]):
        draw_line(buf, x0, y0, x1, y1)
        if filled:
            for px in range(x0, x1 + 1):
                anteil = (px - x0) / (x1 - x0) if x1 != x0 else 0
                py = round(y0 + (y1 - y0) * anteil)
                for fy in range(py, boden + 1):
                    set_pixel(buf, px, fy, 1)


def draw_gauge(buf: bytearray, pct: float, x: int, y: int, r: int, label: str | None = None):
    """Halbkreis-Fortschrittsanzeige; label leer = Prozentwert."""
    import math
    cx, cy = x + r, y + r
    clamped = max(0, min(100, pct))
    # Winkelschritt so, dass der Bogen ohne Lücken bleibt (etwa ein Pixel Bogenlänge)
    schritt = min(2.0, 57.3 / max(1, r))
    a = 180.0
    while a <= 360.0:
        rad = math.radians(a)
        set_pixel(buf, round(cx + r * math.cos(rad)), round(cy + r * math.sin(rad)), 1)
        a += schritt
    # Gefüllter Bogen
    end_angle = 180 + (clamped / 100) * 180
    a = 180.0
    while a <= end_angle:
        rad = math.radians(a)
        for ri in range(r - 2, r + 1):
            set_pixel(buf, round(cx + ri * math.cos(rad)), round(cy + ri * math.sin(rad)), 1)
        a += schritt
    # Wert zentriert
    text = label if label else f"{round(clamped)}%"
    tw = len(text) * 6
    draw_text(buf, text, cx - tw // 2, cy - 3, 1)


def draw_section_header(buf: bytearray, text: str, x: int, y: int, w: int):
    """Section Header: ── LABEL ──"""
    tw = len(text) * 6
    line_l = max(0, (w - tw - 4) // 2)
    line_r = max(0, w - tw - 4 - line_l)
    for i in range(line_l):
        set_pixel(buf, x + i, y + 3, 1)
    draw_text(buf, text, x + line_l + 2, y, 1)
    for i in range(line_r):
        set_pixel(buf, x + line_l + 2 + tw + 2 + i, y + 3, 1)


def draw_ring(buf: bytearray, pct: float, x: int, y: int, r: int, label: str | None = None):
    """Voller Ring, der sich im Uhrzeigersinn von oben füllt; Wert in der Mitte, wenn er hineinpasst."""
    import math
    cx, cy = x + r, y + r
    anteil = max(0.0, min(100.0, pct)) / 100.0
    dicke = 2 if r < 12 else 3
    schritt = min(2.0, 57.3 / max(1, r))
    a = 0.0
    while a < 360.0:
        rad = math.radians(a)
        set_pixel(buf, round(cx + r * math.cos(rad)), round(cy + r * math.sin(rad)), 1)
        a += schritt
    ende = -90.0 + 360.0 * anteil
    a = -90.0
    while a <= ende:
        rad = math.radians(a)
        for ri in range(r - dicke, r + 1):
            set_pixel(buf, round(cx + ri * math.cos(rad)), round(cy + ri * math.sin(rad)), 1)
        a += schritt
    text = label if label is not None else f"{round(pct)}%"
    tw = len(text) * CHAR_SPACING - 1
    if text and tw <= 2 * r - 2 * dicke - 2:
        draw_text(buf, text, cx - tw // 2, cy - 3, 1)


def draw_bar_v(buf: bytearray, x: int, y: int, w: int, h: int, pct: float):
    """Senkrechter Balken mit Rahmen, füllt sich von unten."""
    draw_rect(buf, x, y, x + w - 1, y + h - 1, filled=False)
    fh = round((h - 2) * max(0.0, min(1.0, pct / 100.0)))
    for j in range(fh):
        for i in range(1, w - 1):
            set_pixel(buf, x + i, y + h - 2 - j, 1)


def draw_steps(buf: bytearray, x: int, y: int, w: int, h: int, n: int, pct: float):
    """Stufenanzeige: n Felder nebeneinander, gefüllt bis zum Anteil."""
    n = max(2, n)
    luecke = 2 if w // n >= 6 else 1
    feld = max(1, (w - (n - 1) * luecke) // n)
    voll = round(n * max(0.0, min(1.0, pct / 100.0)))
    for i in range(n):
        fx = x + i * (feld + luecke)
        draw_rect(buf, fx, y, fx + feld - 1, y + h - 1, filled=i < voll)


_SEGMENTE = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
    "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g",
}


def draw_seven_segment(buf: bytearray, text: str, x: int, y: int, h: int) -> int:
    """Ziffern als Siebensegmentanzeige mit Höhe h; andere Zeichen in der Pixelschrift. Liefert die Breite."""
    h = max(7, h)
    t = max(1, round(h / 8))
    dw = max(4, round(h * 0.55))
    luecke = max(1, t)
    mitte = y + (h - t) // 2
    cx = x
    for zeichen in text:
        if zeichen in _SEGMENTE:
            seg = _SEGMENTE[zeichen]
            if "a" in seg:
                draw_rect(buf, cx + 1, y, cx + dw - 2, y + t - 1, filled=True)
            if "g" in seg:
                draw_rect(buf, cx + 1, mitte, cx + dw - 2, mitte + t - 1, filled=True)
            if "d" in seg:
                draw_rect(buf, cx + 1, y + h - t, cx + dw - 2, y + h - 1, filled=True)
            if "f" in seg:
                draw_rect(buf, cx, y + 1, cx + t - 1, mitte - 1, filled=True)
            if "b" in seg:
                draw_rect(buf, cx + dw - t, y + 1, cx + dw - 1, mitte - 1, filled=True)
            if "e" in seg:
                draw_rect(buf, cx, mitte + t, cx + t - 1, y + h - 2, filled=True)
            if "c" in seg:
                draw_rect(buf, cx + dw - t, mitte + t, cx + dw - 1, y + h - 2, filled=True)
            cx += dw + luecke
        elif zeichen == ":":
            draw_rect(buf, cx, y + h // 3 - t // 2, cx + t - 1, y + h // 3 - t // 2 + t - 1, filled=True)
            draw_rect(buf, cx, y + 2 * h // 3 - t // 2, cx + t - 1, y + 2 * h // 3 - t // 2 + t - 1, filled=True)
            cx += t + luecke
        elif zeichen == ".":
            draw_rect(buf, cx, y + h - t, cx + t - 1, y + h - 1, filled=True)
            cx += t + luecke
        elif zeichen == " ":
            cx += dw // 2
        else:
            skala = max(1, round(h / 7))
            draw_text(buf, zeichen, cx, y + (h - 7 * skala) // 2, skala, skala)
            cx += CHAR_SPACING * skala
    return cx - x


def buf_to_pil(buf: bytearray):
    """Pixel-Buffer zu PIL Image (1-bit) konvertieren."""
    from PIL import Image
    img = Image.new("1", (W, H), 0)
    pixels = img.load()
    for y in range(H):
        for x in range(W):
            if buf[y * W + x]:
                pixels[x, y] = 1
    return img


def buf_to_png_base64(buf: bytearray) -> str:
    """Pixel-Buffer direkt zu Base64-PNG (128x64, nativ)."""
    import base64
    import io
    img = buf_to_pil(buf)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return base64.b64encode(out.getvalue()).decode()


def ausschnitt_png_base64(buf: bytearray, x: int, y: int, w: int, h: int) -> str:
    """Ein Ausschnitt des Puffers als Base64-PNG, genau w x h Pixel."""
    import base64
    import io
    img = buf_to_pil(buf).crop((x, y, x + w, y + h))
    out = io.BytesIO()
    img.save(out, format="PNG")
    return base64.b64encode(out.getvalue()).decode()
