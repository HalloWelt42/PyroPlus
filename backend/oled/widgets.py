"""
PyroPlus — OLED Widget-Rendering (v2 — dynamisches Datenkatalog-System)
Rendert Widget-Instanzen: source + display + opts → Pixel-Buffer.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from oled.renderer import (
    W, H, draw_text, draw_text_ex, draw_bar, draw_hline, draw_vline,
    draw_rect, draw_sprite, draw_icon, draw_marquee,
    draw_sparkline, draw_gauge, draw_section_header, draw_fan_icon,
)

TZ = ZoneInfo("Europe/Berlin")

# History fuer Sparklines
_history = {"cpu": [], "temp": [], "ram": [], "fan_speed": [], "net_rx": [], "net_tx": []}
HIST_LEN = 30


def update_history(stats: dict):
    """Jede Sekunde aufrufen."""
    cpu = stats.get("cpu", {})
    ram = stats.get("ram", {})
    net = stats.get("network", {})
    fan = stats.get("fan", {})
    _history["cpu"].append(cpu.get("percent", 0))
    _history["temp"].append(cpu.get("temp", 0))
    _history["ram"].append(ram.get("percent", 0))
    _history["fan_speed"].append(fan.get("rpm", 0))
    _history["net_rx"].append(net.get("rx_bytes_sec", 0))
    _history["net_tx"].append(net.get("tx_bytes_sec", 0))
    for k in _history:
        if len(_history[k]) > HIST_LEN:
            _history[k] = _history[k][-HIST_LEN:]


# ═══ Wert-Aufloesung nach source-ID ═══

def _resolve_value(source: str, stats: dict, weather: dict | None, opts: dict) -> str:
    """Wert einer Datenquelle als String."""
    cpu = stats.get("cpu", {})
    ram = stats.get("ram", {})
    disks = stats.get("disks", [])
    net = stats.get("network", {})
    fan = stats.get("fan", {})
    uptime = stats.get("uptime", {})
    w = weather or {}
    now = datetime.now(TZ)
    # Dynamische Disk-ID: "disk.used.2" → base "disk.used", diskIdx 2
    import re
    dm = re.match(r'^(disk\.\w+)\.(\d+)$', source)
    if dm:
        source = dm.group(1)
        opts = {**opts, "diskIdx": int(dm.group(2))}

    di = opts.get("diskIdx", 0)
    disk = disks[di] if di < len(disks) else {}

    days_de = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    days_lang = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    colon = ":" if now.second % 2 == 0 else " "

    resolvers = {
        # CPU
        "cpu.temp":       lambda: f"{cpu.get('temp', 0):.1f}",
        "cpu.percent":    lambda: str(round(cpu.get("percent", 0))),
        "cpu.cores":      lambda: str(cpu.get("cores", 4)),
        "cpu.temp_min":   lambda: f"{cpu.get('temp_min', 0):.1f}",
        "cpu.temp_max":   lambda: f"{cpu.get('temp_max', 0):.1f}",
        "cpu.temp_range": lambda: f"{cpu.get('temp_min', 0):.1f}-{cpu.get('temp_max', 0):.1f}",
        "cpu.temp_pct":   lambda: str(round(min(100, cpu.get("temp", 0) / 85 * 100))),
        "cpu.load":       lambda: f"{round(cpu.get('percent', 0))}% {cpu.get('temp', 0):.1f}C",
        # RAM
        "ram.used":       lambda: f"{ram.get('used_gb', 0):.1f}",
        "ram.total":      lambda: f"{ram.get('total_gb', 0):.1f}",
        "ram.available":  lambda: f"{ram.get('available_gb', 0):.1f}",
        "ram.percent":    lambda: str(round(ram.get("percent", 0))),
        "ram.ratio":      lambda: f"{ram.get('used_gb', 0):.1f}/{ram.get('total_gb', 0):.1f}",
        "ram.free_pct":   lambda: str(round(100 - ram.get("percent", 0))),
        # Disk
        "disk.label":     lambda: disk.get("label", disk.get("mount", "?")),
        "disk.mount":     lambda: disk.get("mount", "?"),
        "disk.used":      lambda: f"{disk.get('used_gb', 0):.1f}",
        "disk.total":     lambda: f"{disk.get('total_gb', 0):.1f}",
        "disk.available": lambda: f"{disk.get('available_gb', 0):.1f}",
        "disk.percent":   lambda: str(round(disk.get("percent", 0))),
        "disk.ratio":     lambda: f"{disk.get('used_gb', 0):.1f}/{disk.get('total_gb', 0):.1f}",
        "disk.free_pct":  lambda: str(round(100 - disk.get("percent", 0))),
        "disk.model":     lambda: disk.get("model", ""),
        "disk.fstype":    lambda: disk.get("fstype", ""),
        # Netzwerk
        "net.ip":         lambda: net.get("ip", "0.0.0.0"),
        "net.interface":  lambda: net.get("interface", "?"),
        "net.rx":         lambda: _fmt_bytes(net.get("rx_bytes_sec", 0)),
        "net.tx":         lambda: _fmt_bytes(net.get("tx_bytes_sec", 0)),
        "net.rx_raw":     lambda: str(net.get("rx_bytes_sec", 0)),
        "net.tx_raw":     lambda: str(net.get("tx_bytes_sec", 0)),
        "net.traffic":    lambda: f"{_fmt_bytes(net.get('rx_bytes_sec', 0))} {_fmt_bytes(net.get('tx_bytes_sec', 0))}",
        "net.hostname":   lambda: "PyroPlus",
        # Luefter
        "fan.rpm":        lambda: str(fan.get("rpm", 0)),
        "fan.duty":       lambda: str(round(fan.get("current_duty", 0))),
        "fan.level":      lambda: fan.get("level_name", "?"),
        "fan.case":       lambda: "An" if fan.get("case_on") else "Aus",
        "fan.mode":       lambda: fan.get("mode", "?"),
        "fan.rpm_pct":    lambda: str(round(min(100, fan.get("rpm", 0) / 4000 * 100))),
        # Zeiten
        "zeit.uhr":       lambda: now.strftime("%H:%M"),
        "zeit.uhr_s":     lambda: now.strftime("%H:%M:%S"),
        "zeit.uhr_blink": lambda: f"{now.strftime('%H')}{colon}{now.strftime('%M')}",
        "zeit.stunde":    lambda: str(now.hour),
        "zeit.minute":    lambda: str(now.minute),
        "zeit.sekunde":   lambda: str(now.second),
        "zeit.datum":     lambda: now.strftime("%d.%m.%Y"),
        "zeit.datum_kurz":lambda: now.strftime("%d.%m."),
        "zeit.jahr":      lambda: str(now.year),
        "zeit.tag":       lambda: days_de[now.weekday()],
        "zeit.tag_lang":  lambda: days_lang[now.weekday()],
        "zeit.tag_datum": lambda: f"{days_de[now.weekday()]} {now.strftime('%d.%m.%Y')}",
        "zeit.uptime":    lambda: uptime.get("formatted", "0:00"),
        "zeit.uptime_s":  lambda: str(uptime.get("seconds", 0)),
        "zeit.unix":      lambda: str(int(now.timestamp())),
        "zeit.iso":       lambda: now.strftime("%Y-%m-%dT%H:%M:%S"),
        # Wetter
        "wetter.temp":       lambda: f"{w.get('temperature', '--')}",
        "wetter.gefuehlt":   lambda: f"{w.get('apparent_temperature', w.get('feels_like', '--'))}",
        "wetter.feuchte":    lambda: str(w.get("humidity", w.get("relative_humidity_2m", "--"))),
        "wetter.wind":       lambda: str(w.get("wind_speed", w.get("wind_speed_10m", "--"))),
        "wetter.windricht":  lambda: str(w.get("wind_direction_10m", w.get("wind_dir", "--"))),
        "wetter.boeen":      lambda: str(w.get("wind_gusts_10m", w.get("wind_gust", "--"))),
        "wetter.wolken":     lambda: str(w.get("cloud_cover", "--")),
        "wetter.druck":      lambda: f"{w.get('surface_pressure', w.get('pressure', '--')):.0f}" if isinstance(w.get("surface_pressure", w.get("pressure")), (int, float)) else "--",
        "wetter.druck_msl":  lambda: f"{w.get('pressure_msl', '--')}",
        "wetter.niederschlag": lambda: f"{w.get('precipitation', 0)}",
        "wetter.zustand":    lambda: w.get("condition_text", "--"),
        "wetter.tag_nacht":  lambda: "Tag" if w.get("is_day") else "Nacht",
        "wetter.ort":        lambda: w.get("location", "--"),
        "wetter.sunrise":    lambda: str(w.get("sunrise", "--")),
        "wetter.sunset":     lambda: str(w.get("sunset", "--")),
        "wetter.kombi":      lambda: f"{w.get('temperature', '--')} {w.get('condition_text', '')}",
        "wetter.wind_kombi": lambda: f"{w.get('wind_speed', w.get('wind_speed_10m', '--'))} ({w.get('wind_gusts_10m', w.get('wind_gust', '--'))}) km/h",
        # Text
        "text.frei":         lambda: opts.get("text", "Text"),
        "text.laufschrift":  lambda: opts.get("text", "Laufschrift"),
        "text.mehrzeilig":   lambda: opts.get("text", "Zeile 1"),
        "text.leer":         lambda: "",
    }
    resolver = resolvers.get(source)
    return resolver() if resolver else opts.get("text", "?")


def _resolve_percent(source: str, stats: dict, weather: dict | None, opts: dict) -> float:
    """Prozentwert (0-100) einer Datenquelle."""
    import re
    dm = re.match(r'^(disk\.\w+)\.(\d+)$', source)
    if dm:
        source = dm.group(1)
        opts = {**opts, "diskIdx": int(dm.group(2))}
    cpu = stats.get("cpu", {})
    ram = stats.get("ram", {})
    disks = stats.get("disks", [])
    fan = stats.get("fan", {})
    w = weather or {}
    di = opts.get("diskIdx", 0)
    disk = disks[di] if di < len(disks) else {}

    pct_map = {
        "cpu.percent":   cpu.get("percent", 0),
        "cpu.temp":      min(100, cpu.get("temp", 0) / 85 * 100),
        "cpu.temp_pct":  min(100, cpu.get("temp", 0) / 85 * 100),
        "ram.percent":   ram.get("percent", 0),
        "ram.free_pct":  100 - ram.get("percent", 0),
        "disk.percent":  disk.get("percent", 0),
        "disk.free_pct": 100 - disk.get("percent", 0),
        "fan.duty":      fan.get("current_duty", 0),
        "fan.rpm_pct":   min(100, fan.get("rpm", 0) / 4000 * 100),
        "wetter.feuchte": float(w.get("humidity", w.get("relative_humidity_2m", 0)) or 0),
        "wetter.wolken":  float(w.get("cloud_cover", 0) or 0),
    }
    return pct_map.get(source, float(_resolve_value(source, stats, weather, opts) or 0))


def _fmt_bytes(b: float) -> str:
    if b > 1048576: return f"{b/1048576:.1f} MB/s"
    if b > 1024: return f"{round(b/1024)} KB/s"
    return f"{round(b)} B/s"


# History-Key Mapping
HISTORY_KEYS = {
    "cpu.percent": "cpu", "cpu.temp": "temp",
    "ram.percent": "ram", "fan.rpm": "fan_speed",
    "net.rx": "net_rx", "net.tx": "net_tx",
}


# ═══ HAUPT-RENDER-FUNKTION ═══

def render_widget(buf: bytearray, widget: dict, stats: dict,
                  weather: dict | None = None):
    """Ein Widget (source + display + opts) in den Buffer rendern."""
    source = widget.get("source", "")
    display = widget.get("display", "zahl")
    x = widget.get("x", 0)
    y = widget.get("y", 0)
    opts = widget.get("opts", {})

    sx = int(opts.get("scaleX", 1))
    sy = int(opts.get("scaleY", sx))
    invert = opts.get("invert", False)
    border = opts.get("border", False)
    align = opts.get("align", "left")
    box_w = opts.get("boxW", 0)

    val = _resolve_value(source, stats, weather, opts)
    full_text = (opts.get("prefix", "") or "") + val + (opts.get("suffix", "") or "")
    has_ex = invert or border or (align and align != "left")

    import time

    if display in ("zahl", "zahl_gross", "zahl_xl", "text"):
        if display == "zahl_gross":
            sx, sy = max(sx, 2), max(sy, 2)
        elif display == "zahl_xl":
            sx, sy = max(sx, 3), max(sy, 3)
        if has_ex:
            draw_text_ex(buf, full_text, x, y, sx, sy,
                         invert=invert, border=border, align=align, box_w=box_w)
        else:
            draw_text(buf, full_text, x, y, sx, sy)

    elif display == "balken":
        pct = _resolve_percent(source, stats, weather, opts)
        draw_bar(buf, x, y, opts.get("width", 60), opts.get("height", 6), pct)

    elif display == "balken_label":
        pct = _resolve_percent(source, stats, weather, opts)
        bw = opts.get("width", 50)
        bh = opts.get("height", 6)
        draw_bar(buf, x, y, bw, bh, pct)
        label = full_text or f"{round(pct)}%"
        draw_text(buf, label, x + bw + 2, y, sx, sy)

    elif display == "gauge":
        pct = _resolve_percent(source, stats, weather, opts)
        draw_gauge(buf, pct, x, y, opts.get("radius", 12))

    elif display == "sparkline":
        hist_key = HISTORY_KEYS.get(source, "")
        data = _history.get(hist_key, [])
        draw_sparkline(buf, data, x, y, opts.get("width", 60), opts.get("height", 20))

    elif display == "laufschrift":
        text = opts.get("text", val or "Laufschrift")
        offset = int(time.time() * 30) % (len(text) * 6 * sx + W)
        draw_marquee(buf, text, y, offset, sx)

    elif display == "linie_h":
        draw_hline(buf, x, y, opts.get("width", 60))

    elif display == "linie_v":
        draw_vline(buf, x, y, opts.get("height", 20))

    elif display == "rahmen":
        draw_rect(buf, x, y, x + opts.get("width", 40) - 1,
                  y + opts.get("height", 20) - 1, filled=False)

    elif display == "block":
        draw_rect(buf, x, y, x + opts.get("width", 40) - 1,
                  y + opts.get("height", 20) - 1, filled=True)

    elif display == "section":
        draw_section_header(buf, opts.get("text", "Label"), x, y, opts.get("width", 60))

    # Lüftersymbol (animiert)
    elif display in ("fan_icon", "fan_icon_gross", "fan_icon_xl", "fan_icon_rpm"):
        sz = opts.get("size", 16 if "gross" in display else 24 if "xl" in display else 8)
        rpm = 0
        try:
            rpm = float(val)
        except (ValueError, TypeError):
            pass
        speed = min(1.0, rpm / 3000)
        frame = int(time.time() * max(1, speed * 12)) % 4 if speed > 0.01 else 0
        draw_fan_icon(buf, x, y, sz, frame)
        if display == "fan_icon_rpm":
            label = f"{round(rpm)}{opts.get('suffix', '')}"
            draw_text(buf, label, x + sz + 2, y + sz // 2 - 3, sx, sy)
