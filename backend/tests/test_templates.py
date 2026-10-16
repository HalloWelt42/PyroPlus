"""Mitgelieferte Vorlagen: eindeutig, vollständig innerhalb des Displays, frische Kennungen beim Einfügen."""

from datetime import datetime

from fastapi.testclient import TestClient

from oled.compose import RenderContext, render_screen
from oled.models import DisplayMode, ScreenKind, W, H
from oled.templates import SCREEN_TEMPLATES, WIDGET_TEMPLATES, screen_template, template_catalog, widget_template
from oled.values import StatsSnapshot
from oled.weather import WeatherCurrent, WeatherReport


def _ctx(stats_dict: dict) -> RenderContext:
    bericht = WeatherReport(location_id="x", location_name="Zeitz",
                            current=WeatherCurrent(temperature=14.7, apparent_temperature=12.0, humidity=71,
                                                   wind_speed=18, wind_gusts=34, cloud_cover=65, pressure=1013,
                                                   precipitation=0.4, condition_text="Bewölkt", sunrise="07:21", sunset="18:04"))
    return RenderContext(stats=StatsSnapshot.model_validate(stats_dict), now=datetime(2026, 10, 16, 12, 34, 56),
                         weather_for=lambda _: bericht, simulate={})


def test_kennungen_eindeutig() -> None:
    ids = [d.id for d in SCREEN_TEMPLATES]
    assert len(ids) == len(set(ids))
    ids = [d.id for d in WIDGET_TEMPLATES]
    assert len(ids) == len(set(ids))
    katalog = template_catalog()
    assert len(katalog.screens) >= 20 and len(katalog.widgets) >= 15 and katalog.categories


def test_vorlagen_bleiben_im_bild(stats_dict: dict) -> None:
    ctx = _ctx(stats_dict)
    for t in template_catalog().screens:
        buf, boxes = render_screen(t.screen, ctx)
        assert sum(buf) > 0, t.name
        for box in boxes:
            assert box.x + box.w <= W and box.y + box.h <= H, f"{t.name}: {box}"
        if t.screen.kind == ScreenKind.widgets:
            # Keine zwei Widgets dürfen sich überlagern (Rahmen dürfen sich nur berühren)
            for i, a in enumerate(boxes):
                for b in boxes[i + 1:]:
                    if a.w == 0 or b.w == 0:
                        continue
                    ueberlappt = a.x < b.x + b.w and b.x < a.x + a.w and a.y < b.y + b.h and b.y < a.y + a.h
                    rahmen = {"Rahmen", "Linie"}
                    namen = {t.screen.widgets[boxes.index(a)].name.split(" ")[0], t.screen.widgets[boxes.index(b)].name.split(" ")[0]}
                    assert not ueberlappt or namen & rahmen, f"{t.name}: {a} überlappt {b}"


def test_widgetvorlagen_rendern(stats_dict: dict) -> None:
    ctx = _ctx(stats_dict)
    from oled.compose import render_widget
    for t in template_catalog().widgets:
        _, box = render_widget(t.widget, ctx)
        if t.widget.display == DisplayMode.laufschrift:
            continue  # läuft zeitabhängig durch das Bild, darf gerade außerhalb sein
        assert box.w > 0 and box.x + box.w <= W and box.y + box.h <= H, t.name


def test_einfuegen_erzeugt_neue_kennungen() -> None:
    a, b = screen_template("klassisch"), screen_template("klassisch")
    assert a and b and a.id != b.id
    assert {w.id for w in a.widgets}.isdisjoint({w.id for w in b.widgets})
    assert screen_template("gibt_es_nicht") is None
    w1, w2 = widget_template("uhr_gross"), widget_template("uhr_gross")
    assert w1 and w2 and w1.id != w2.id


def test_vorlagen_ueber_die_schnittstelle() -> None:
    import main
    from config import API_TOKEN
    with TestClient(main.app) as client:
        client.headers.update({"X-API-Token": API_TOKEN})
        katalog = client.get("/api/oled/templates").json()
        assert katalog["screens"] and katalog["widgets"]
        vorher = len(client.get("/api/oled/screens").json())
        r = client.post("/api/oled/templates/screens/messuhren")
        assert r.status_code == 201 and r.json()["name"] == "Messuhren"
        assert len(client.get("/api/oled/screens").json()) == vorher + 1
        assert client.post("/api/oled/templates/screens/nix").status_code == 404
        w = client.get("/api/oled/templates/widgets/cpu_balken").json()
        assert w["display"] == "balken_label" and len(w["id"]) == 32
        entwurf = {"screen": katalog["screens"][0]["screen"]}
        assert client.post("/api/oled/render", json=entwurf).status_code == 200
