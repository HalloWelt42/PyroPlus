"""
PyroPlus: Pixel-Primitive auf dem 1-Bit-Puffer (128x64).
Reine Pixel-Operationen auf bytearray; PIL nur für die PNG-Ausgabe.
"""

from oled.font import FONT, CHAR_SPACING, get_glyph
from oled.sprites import SPRITES

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


def draw_sprite(buf: bytearray, name: str, x: int, y: int, scale: int = 1):
    """Pixel-Art Sprite rendern."""
    rows = SPRITES.get(name)
    if not rows:
        return
    for ry, row in enumerate(rows):
        for rx in range(len(row)):
            if row[rx] == '1':
                for dy in range(scale):
                    for dx in range(scale):
                        set_pixel(buf, x + rx * scale + dx, y + ry * scale + dy, 1)


def draw_icon(buf: bytearray, icon_rows: list[str], x: int, y: int):
    """Icon aus Zeilen-Strings rendern (8x8 oder 16x16)."""
    for ry, row in enumerate(icon_rows):
        for rx in range(len(row)):
            if row[rx] == '1':
                set_pixel(buf, x + rx, y + ry, 1)


def draw_marquee(buf: bytearray, text: str, y: int, offset: int, scale: int = 1):
    """Laufschrift."""
    total_w = len(text) * CHAR_SPACING * scale
    x = W - (offset % (total_w + W))
    draw_text(buf, text, x, y, scale)


def draw_sparkline(buf: bytearray, values: list, x: int, y: int, w: int, h: int):
    """Mini-Verlaufsgraph mit Rahmen."""
    if not values or len(values) < 2:
        return
    mx = max(max(values), 1)
    mn = min(min(values), 0)
    rng = mx - mn or 1
    step = w / (len(values) - 1)
    # Rahmen
    draw_rect(buf, x, y, x + w - 1, y + h - 1, filled=False)
    # Linie
    for i in range(len(values) - 1):
        x0 = round(x + 1 + i * step)
        y0 = round(y + h - 2 - ((values[i] - mn) / rng) * (h - 3))
        x1 = round(x + 1 + (i + 1) * step)
        y1 = round(y + h - 2 - ((values[i + 1] - mn) / rng) * (h - 3))
        draw_line(buf, x0, y0, x1, y1)


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


FAN_8 = [
    ['00011000','00010100','00100100','11100111','11100111','00100100','00101000','00011000'],
    ['00111000','01010000','00100110','00100111','11100100','01100100','00001010','00011100'],
    ['00110000','01100100','00100100','00100111','11100100','00100100','00100110','00001100'],
    ['00011100','00001010','01100100','11100100','00100111','00100110','01010000','00111000'],
]
FAN_16 = [
    ['0000001111000000','0000011111100000','0000111001100000','0001110001100000',
     '0011100001100000','0111000001100000','0111000001100000','0011111111111100',
     '0011111111111100','0000011000001110','0000011000001110','0000011000011100',
     '0000011000111000','0000011001110000','0000011111100000','0000001111000000'],
    ['0000000110000000','0001100110000000','0001110011000000','0000111001110000',
     '0000011100110000','0000001111111100','0000011111111100','0011111111100000',
     '0011111111100000','0000110011100000','0001100111000000','0000111011100000',
     '0000011001110000','0000001100111000','0000001100011000','0000000110000000'],
    ['0000001111000000','0000011111100000','0000011100110000','0000011000011100',
     '0000011000001110','0000011000001110','0011111111111100','0011111111111100',
     '0111000001100000','0111000001100000','0011100001100000','0001110001100000',
     '0000111001100000','0000011111100000','0000001111000000','0000000000000000'],
    ['0000000110000000','0000001100011000','0000001100111000','0000011001110000',
     '0000111011100000','0001100111000000','0011111111100000','0000011111111100',
     '0000001111111100','0000011100110000','0000111001110000','0001110011000000',
     '0001100110000000','0000000110000000','0000000000000000','0000000000000000'],
]


def draw_fan_icon(buf: bytearray, x: int, y: int, size: int, frame: int):
    """Animiertes Lueftersymbol."""
    frames = FAN_16 if size >= 16 else FAN_8
    rows = frames[frame % len(frames)]
    s = 16 if size >= 16 else 8
    scale = max(1, size // s)
    for ry, row in enumerate(rows):
        for rx in range(len(row)):
            if row[rx] == '1':
                for dy in range(scale):
                    for dx in range(scale):
                        set_pixel(buf, x + rx * scale + dx, y + ry * scale + dy, 1)


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
