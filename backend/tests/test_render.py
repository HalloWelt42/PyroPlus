"""Rendern: Werte, Formatierung, Rahmenmessung, Drehung, Pixelbild."""

from datetime import datetime

from oled.compose import RenderContext, render_screen, render_widget
from oled.models import DisplayMode, Rotation, Screen, Widget, WidgetOpts, W, H
from oled.modes import pack_bitmap, unpack_bitmap
from oled.values import StatsSnapshot, ValueContext, resolve
from oled.weather import WeatherCurrent, WeatherReport


def _ctx(stats_dict: dict, simulate: dict | None = None) -> RenderContext:
    return RenderContext(stats=StatsSnapshot.model_validate(stats_dict), now=datetime(2026, 10, 16, 14, 30, 2),
                         weather_for=lambda _id: None, simulate=simulate or {})


def test_zahl_mit_dezimalen_und_tausender(stats_dict: dict) -> None:
    stats = StatsSnapshot.model_validate(stats_dict)
    wert = resolve("cpu.temp", ValueContext(stats=stats, now=datetime.now()))
    assert wert.text == "43.5"
    wert = resolve("cpu.temp", ValueContext(stats=stats, now=datetime.now(), opts=WidgetOpts(decimals=0)))
    assert wert.text == "44"
    wert = resolve("disk.used.1", ValueContext(stats=stats, now=datetime.now(), opts=WidgetOpts(decimals=0, thousands=True)))
    assert wert.text == "1.500"
    wert = resolve("zeit.uhr", ValueContext(stats=stats, now=datetime(2026, 1, 1, 7, 5)))
    assert wert.text == "07:05"


def test_simulation_ersetzt_wert(stats_dict: dict) -> None:
    stats = StatsSnapshot.model_validate(stats_dict)
    wert = resolve("cpu.percent", ValueContext(stats=stats, now=datetime.now(), simulate={"cpu.percent": 55}))
    assert wert.text == "55" and wert.percent == 55


def test_wetter_ohne_bericht_und_mit(stats_dict: dict) -> None:
    stats = StatsSnapshot.model_validate(stats_dict)
    assert resolve("wetter.temp", ValueContext(stats=stats, now=datetime.now())).text == "--"
    bericht = WeatherReport(location_id="a", location_name="Berlin",
                            current=WeatherCurrent(temperature=12.34, condition_text="Klar", humidity=70))
    ctx = ValueContext(stats=stats, now=datetime.now(), weather=bericht)
    assert resolve("wetter.temp", ctx).text == "12.3"
    assert resolve("wetter.ort", ctx).text == "Berlin"
    assert resolve("wetter.feuchte", ctx).percent == 70


def test_rahmen_ist_pixelgenau(stats_dict: dict) -> None:
    widget = Widget(source="text.frei", display=DisplayMode.text, x=10, y=5, opts=WidgetOpts(text="AB"))
    buf, box = render_widget(widget, _ctx(stats_dict))
    # Zwei Zeichen zu 5 Pixel plus 1 Pixel Abstand: Breite 11, Höhe 7
    assert (box.x, box.y, box.w, box.h) == (10, 5, 11, 7)
    assert sum(buf) > 0


def test_leeres_widget_hat_nullrahmen(stats_dict: dict) -> None:
    widget = Widget(source="text.leer", display=DisplayMode.text, x=3, y=3)
    _, box = render_widget(widget, _ctx(stats_dict))
    assert (box.w, box.h) == (0, 0) and (box.x, box.y) == (3, 3)


def test_drehung_vertauscht_breite_und_hoehe(stats_dict: dict) -> None:
    widget = Widget(source="text.frei", display=DisplayMode.text, x=0, y=0,
                    opts=WidgetOpts(text="ABCD", rotate=Rotation.r90))
    _, box = render_widget(widget, _ctx(stats_dict))
    assert box.w == 7 and box.h == 23


def test_bildschirm_liefert_bild_und_rahmen(stats_dict: dict) -> None:
    screen = Screen(name="Test", widgets=[
        Widget(source="cpu.percent", display=DisplayMode.balken, x=0, y=0, opts=WidgetOpts(width=60, height=6)),
        Widget(source="zeit.uhr", display=DisplayMode.text, x=0, y=20, opts=WidgetOpts(scale_x=2, scale_y=2)),
    ])
    buf, boxes = render_screen(screen, _ctx(stats_dict))
    assert len(buf) == W * H and len(boxes) == 2
    assert boxes[0].w == 60 and boxes[0].h == 6
    assert boxes[1].h == 14


def test_bitmap_packen_und_zeichnen(stats_dict: dict) -> None:
    rows = [[1, 0, 1, 0, 1, 0, 1, 0, 1], [0, 1, 0, 1, 0, 1, 0, 1, 0]]
    kodiert = pack_bitmap(rows)
    assert unpack_bitmap(kodiert, 9, 2) == rows
    widget = Widget(source="layout.bitmap", display=DisplayMode.bitmap, x=4, y=4,
                    opts=WidgetOpts(width=9, height=2, bitmap=kodiert))
    buf, box = render_widget(widget, _ctx(stats_dict))
    assert buf[4 * W + 4] == 1 and buf[4 * W + 5] == 0 and buf[5 * W + 5] == 1
    assert (box.x, box.y, box.w, box.h) == (4, 4, 9, 2)


def test_mehrzeiliger_text(stats_dict: dict) -> None:
    widget = Widget(source="text.mehrzeilig", display=DisplayMode.text, x=0, y=0, opts=WidgetOpts(text="A\nB"))
    _, box = render_widget(widget, _ctx(stats_dict))
    assert box.h == 15


def test_unbekannte_quelle_bricht_nicht_ab(stats_dict: dict) -> None:
    widget = Widget(source="gibt.es.nicht", display=DisplayMode.text, x=0, y=0)
    _, box = render_widget(widget, _ctx(stats_dict))
    assert box.w > 0
