"""
PyroPlus — OLED Pixel-Buffer Renderer (128x64, 1-Bit)
Reine Pixel-Operationen auf bytearray. Kein PIL fuer Text/Formen.
Identisch zum Frontend engine.js — pixelgenaues Rendering.
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
