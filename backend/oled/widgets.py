"""
PyroPlus — OLED Widget-Rendering
Alle atomaren Widgets, identisch zum Frontend.
Arbeitet auf bytearray Pixel-Buffer.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from oled.renderer import (
    draw_text, draw_text_ex, draw_bar, draw_hline, draw_vline,
    draw_rect, draw_sprite, draw_icon, draw_marquee,
    draw_sparkline, draw_gauge, draw_section_header,
)
from oled.icons import ICONS_8x8, condition_to_icon

TZ = ZoneInfo("Europe/Berlin")

# History für Sparklines (Backend sammelt selbst)
_history = {"cpu": [], "temp": [], "ram": []}
HIST_LEN = 30


def update_history(stats: dict):
    """Wird jede Sekunde vom Render-Loop aufgerufen."""
    cpu = stats.get("cpu", {})
    ram = stats.get("ram", {})
    _history["cpu"].append(cpu.get("percent", 0))
    _history["temp"].append(cpu.get("temp", 0))
    _history["ram"].append(ram.get("percent", 0))
    for k in _history:
        if len(_history[k]) > HIST_LEN:
            _history[k] = _history[k][-HIST_LEN:]


def _pad(n: int, length: int = 3) -> str:
    """Zahl rechtsbuendig mit fuehrenden Leerzeichen."""
    s = str(n)
    return s if len(s) >= length else ' ' * (length - len(s)) + s


def _tsd(n: float) -> str:
    """Tausenderpunkt: 24214 -> 24.214"""
    return f"{round(n):,}".replace(",", ".")


def _format_bytes(b: float) -> str:
    """Bytes/s formatieren."""
    if b > 1048576:
        return f"{b / 1048576:.1f} MB/s"
    if b > 1024:
        return f"{round(b / 1024)} KB/s"
    return f"{round(b)} B/s"


def render_widget(buf: bytearray, widget: dict, stats: dict,
                  weather: dict | None = None, weather_location: str = ""):
    """Ein Widget in den Pixel-Buffer rendern."""
    x = widget.get("x", 0)
    y = widget.get("y", 0)
    wt = widget.get("type", "")

    # Skalierung: scaleX/scaleY direkt vom Frontend, Fallback auf font-key
    raw_sx = widget.get("scaleX")
    raw_sy = widget.get("scaleY")
    if raw_sx is not None or raw_sy is not None:
        scale_x = int(raw_sx) if raw_sx is not None else 1
        scale_y = int(raw_sy) if raw_sy is not None else scale_x
    else:
        font_key = widget.get("font", "sm")
        scale_map = {"sm": 1, "md": 1, "lg": 2, "xl": 3}
        s = scale_map.get(font_key, 1)
        scale_x, scale_y = s, s

    cpu = stats.get("cpu", {})
    ram = stats.get("ram", {})
    disks = stats.get("disks", [])
    uptime_d = stats.get("uptime", {})
    net = stats.get("network", {})
    now = datetime.now(TZ)
    w = weather or {}

    prefix = widget.get("prefix", "")
    # Erweiterte Darstellung
    w_invert = widget.get("invert", False)
    w_border = widget.get("border", False)
    w_align = widget.get("align", "left")
    w_boxW = widget.get("boxW", 0)

    def _txt(text: str):
        """Text mit optionalem Invert/Border/Align rendern."""
        if w_invert or w_border or (w_align and w_align != "left"):
            draw_text_ex(buf, text, x, y, scale_x, scale_y,
                         invert=w_invert, border=w_border,
                         align=w_align, box_w=w_boxW)
        else:
            draw_text(buf, text, x, y, scale_x, scale_y)

    # ═══ ZEIT ═══
    if wt == "clock":
        colon = ":" if now.second % 2 == 0 else " "
        text = f"{now.strftime('%H')}{colon}{now.strftime('%M')}"
        _txt(text)

    elif wt == "clock_s":
        _txt(now.strftime("%H:%M:%S"))

    elif wt == "clock_l":
        colon = ":" if now.second % 2 == 0 else " "
        _txt(f"{now.strftime('%H')}{colon}{now.strftime('%M')}")

    elif wt == "date":
        _txt(now.strftime("%d.%m.%Y"))

    elif wt == "weekday":
        days = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        _txt(days[now.weekday()])

    # ═══ CPU ═══
    elif wt == "cpu_temp":
        t = round(cpu.get("temp", 0))
        _txt(f"{prefix}{_pad(t)}\u00b0")

    elif wt == "cpu_pct":
        p = round(cpu.get("percent", 0))
        _txt(f"{prefix}{_pad(p)}%")

    elif wt == "cpu_cores":
        _txt(f"{prefix}{cpu.get('cores', 4)}")

    elif wt == "cpu_bar":
        bw = widget.get("w", widget.get("width", 60))
        bh = widget.get("h", widget.get("height", 6))
        draw_bar(buf, x, y, bw, bh, cpu.get("percent", 0))

    # ═══ RAM ═══
    elif wt == "ram_used":
        val = ram.get("used_gb", 0)
        _txt(f"{prefix}{_tsd(val)} G" if widget.get("tsep") else f"{prefix}{round(val)} G")

    elif wt == "ram_total":
        val = ram.get("total_gb", 0)
        _txt(f"{prefix}{_tsd(val)} G" if widget.get("tsep") else f"{prefix}{round(val)} G")

    elif wt == "ram_pct":
        p = round(ram.get("percent", 0))
        _txt(f"{prefix}{_pad(p)}%")

    elif wt == "ram_bar":
        bw = widget.get("w", widget.get("width", 60))
        bh = widget.get("h", widget.get("height", 6))
        draw_bar(buf, x, y, bw, bh, ram.get("percent", 0))

    # ═══ DISK ═══
    elif wt == "disk_name":
        di = widget.get("diskIdx", 0)
        d = disks[di] if di < len(disks) else {}
        _txt(f"{prefix}{d.get('label', d.get('mount', '?'))}")

    elif wt == "disk_used":
        di = widget.get("diskIdx", 0)
        d = disks[di] if di < len(disks) else {}
        val = d.get("used_gb", 0)
        _txt(f"{prefix}{_tsd(val)} G" if widget.get("tsep") else f"{prefix}{round(val)} G")

    elif wt == "disk_total":
        di = widget.get("diskIdx", 0)
        d = disks[di] if di < len(disks) else {}
        val = d.get("total_gb", 0)
        _txt(f"{prefix}{_tsd(val)} G" if widget.get("tsep") else f"{prefix}{round(val)} G")

    elif wt == "disk_pct":
        di = widget.get("diskIdx", 0)
        d = disks[di] if di < len(disks) else {}
        p = round(d.get("percent", 0))
        _txt(f"{prefix}{_pad(p)}%")

    elif wt == "disk_bar":
        di = widget.get("diskIdx", 0)
        d = disks[di] if di < len(disks) else {}
        bw = widget.get("w", widget.get("width", 60))
        bh = widget.get("h", widget.get("height", 6))
        draw_bar(buf, x, y, bw, bh, d.get("percent", 0))

    # ═══ NETZWERK ═══
    elif wt == "net_ip":
        _txt(f"{prefix}{net.get('ip', '0.0.0.0')}")

    elif wt == "net_if":
        _txt(f"{prefix}{net.get('interface', '?')}")

    elif wt == "net_rx":
        _txt(f"{prefix}{_format_bytes(net.get('rx_bytes_sec', 0))}")

    elif wt == "net_tx":
        _txt(f"{prefix}{_format_bytes(net.get('tx_bytes_sec', 0))}")

    # ═══ SYSTEM ═══
    elif wt == "uptime":
        _txt(f"{prefix}{uptime_d.get('formatted', '0:00')}")

    # ═══ WETTER ═══
    elif wt == "w_temp":
        temp = w.get("temperature", w.get("temp", "--"))
        _txt(f"{temp}\u00b0")

    elif wt == "w_temp_sm":
        temp = w.get("temperature", w.get("temp", "--"))
        _txt(f"{temp}\u00b0C")

    elif wt == "w_cond":
        cond = w.get("condition_text", w.get("condition", "?"))
        _txt(str(cond)[:12])

    elif wt == "w_hum":
        hum = w.get("humidity", "--")
        _txt(f"{hum}%")

    elif wt == "w_wind":
        spd = w.get("wind_speed", w.get("windspeed", "--"))
        _txt(f"{spd}km/h")

    elif wt == "w_press":
        prs = w.get("pressure", "--")
        _txt(f"{prs}hPa")

    elif wt == "w_icon" or wt == "w_icon_sm":
        cond = w.get("condition_text", w.get("condition", ""))
        icon_name = condition_to_icon(cond)
        icon_rows = ICONS_8x8.get(icon_name, ICONS_8x8.get("sun_cloud", []))
        draw_icon(buf, icon_rows, x, y)

    elif wt == "w_sunrise":
        sr = str(w.get("sunrise", "--"))[:5]
        icon_rows = ICONS_8x8.get("sun", [])
        draw_icon(buf, icon_rows, x, y)
        draw_text(buf, sr, x + 10, y, scale_x, scale_y)

    elif wt == "w_sunset":
        ss = str(w.get("sunset", "--"))[:5]
        icon_rows = ICONS_8x8.get("moon", [])
        draw_icon(buf, icon_rows, x, y)
        draw_text(buf, ss, x + 10, y, scale_x, scale_y)

    elif wt == "w_uv":
        uv = w.get("uv_index", w.get("uv", "--"))
        _txt(f"UV{uv}")

    elif wt == "w_loc" or wt == "w_location":
        loc = widget.get("text") or weather_location or "---"
        _txt(loc[:14])

    # ═══ DEKO ═══
    elif wt == "label":
        text = widget.get("text", "Text")
        _txt(text)

    elif wt == "marquee":
        import time
        text = widget.get("text", "PyroPlus")
        offset = int(time.time() * 30) % (len(text) * 6 * scale_x + 128)
        draw_marquee(buf, text, y, offset, scale_x)

    elif wt == "line_h":
        lw = widget.get("w", widget.get("width", 60))
        draw_hline(buf, x, y, lw)

    elif wt == "line_v":
        lh = widget.get("h", widget.get("height", 20))
        draw_vline(buf, x, y, lh)

    elif wt == "rect_o":
        rw = widget.get("w", widget.get("width", 40))
        rh = widget.get("h", widget.get("height", 20))
        draw_rect(buf, x, y, x + rw - 1, y + rh - 1, filled=False)

    elif wt == "rect_f":
        rw = widget.get("w", widget.get("width", 40))
        rh = widget.get("h", widget.get("height", 20))
        draw_rect(buf, x, y, x + rw - 1, y + rh - 1, filled=True)

    # ═══ SPRITES ═══
    elif wt in ("snowman", "snowflake", "heart", "star", "cat_spr",
                "dog_spr", "tree_spr", "sun_spr", "moon_spr",
                "music_spr", "skull_spr", "gift_spr", "bell_spr"):
        sprite_name = {
            "cat_spr": "cat", "dog_spr": "dog", "tree_spr": "tree",
            "sun_spr": "sun_deco", "moon_spr": "moon_deco",
            "music_spr": "music", "skull_spr": "skull",
            "gift_spr": "gift", "bell_spr": "bell",
        }.get(wt, wt)
        sp_scale = widget.get("scale", widget.get("scaleX", 1))
        draw_sprite(buf, sprite_name, x, y, int(sp_scale) if sp_scale else 1)

    # ═══ SPARKLINES ═══
    elif wt == "spark_cpu":
        bw = widget.get("w", widget.get("width", 60))
        bh = widget.get("h", widget.get("height", 20))
        draw_sparkline(buf, _history["cpu"], x, y, bw, bh)

    elif wt == "spark_temp":
        bw = widget.get("w", widget.get("width", 60))
        bh = widget.get("h", widget.get("height", 20))
        draw_sparkline(buf, _history["temp"], x, y, bw, bh)

    elif wt == "spark_ram":
        bw = widget.get("w", widget.get("width", 60))
        bh = widget.get("h", widget.get("height", 20))
        draw_sparkline(buf, _history["ram"], x, y, bw, bh)

    # ═══ GAUGES ═══
    elif wt == "gauge_cpu":
        r = widget.get("radius", 12)
        draw_gauge(buf, cpu.get("percent", 0), x, y, r)

    elif wt == "gauge_ram":
        r = widget.get("radius", 12)
        draw_gauge(buf, ram.get("percent", 0), x, y, r)

    elif wt == "gauge_disk":
        di = widget.get("diskIdx", 0)
        d = disks[di] if di < len(disks) else {}
        r = widget.get("radius", 12)
        draw_gauge(buf, d.get("percent", 0), x, y, r)

    elif wt == "gauge_temp":
        r = widget.get("radius", 12)
        draw_gauge(buf, min(100, cpu.get("temp", 0) / 80 * 100), x, y, r)

    # ═══ SECTION HEADER ═══
    elif wt == "section":
        sw = widget.get("w", widget.get("width", 60))
        text = widget.get("text", "Label")
        draw_section_header(buf, text, x, y, sw)
