"""Schnittstelle: Bildschirme, Rendern, Katalog, Vorlagen, Profile, Wetterorte, Export, veraltete Routen."""

from __future__ import annotations

import base64
import io
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

import main
from config import API_TOKEN
from oled.models import GeocodeHit, WeatherLocation
from oled.weather import WeatherCurrent, WeatherReport


class FakeProvider:
    def fetch(self, location: WeatherLocation) -> WeatherReport:
        return WeatherReport(location_id=location.id, location_name=location.name,
                             current=WeatherCurrent(temperature=9.5, condition_text="Klar"))

    def geocode(self, query: str) -> list[GeocodeHit]:
        return [GeocodeHit(name="Leipzig", country="Deutschland", lat=51.34, lon=12.37)]


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(main.app) as c:
        main.oled.weather.provider = FakeProvider()
        c.headers.update({"X-API-Token": API_TOKEN})
        yield c


def test_token_pflicht(client: TestClient) -> None:
    offen = TestClient(main.app)
    assert offen.get("/api/oled").status_code == 401
    assert offen.get("/health").status_code == 200


def test_zustand_und_version(client: TestClient) -> None:
    r = client.get("/api/oled")
    assert r.status_code == 200
    daten = r.json()
    assert daten["screens"] and daten["currentScreenId"] == daten["screens"][0]["id"]
    assert daten["version"] == client.get("/health").json()["version"]
    assert "screensVersion" in daten


def test_katalog(client: TestClient) -> None:
    katalog = client.get("/api/oled/catalog").json()
    assert {t["id"] for t in katalog["tabs"]} >= {"cpu", "wetter", "layout"}
    text = next(m for m in katalog["modes"] if m["id"] == "text")
    assert "scaleX" in text["fields"] and text["variants"]


def test_render_entwurf_mit_rahmen(client: TestClient) -> None:
    entwurf = {"screen": {"name": "Entwurf", "widgets": [
        {"source": "cpu.temp", "display": "text", "x": 2, "y": 3, "opts": {"scaleX": 2, "scaleY": 2, "suffix": "C"}},
    ]}, "simulate": {"cpu.temp": 50}}
    r = client.post("/api/oled/render", json=entwurf)
    assert r.status_code == 200, r.text
    daten = r.json()
    png = base64.b64decode(daten["imageBase64"])
    from PIL import Image
    bild = Image.open(io.BytesIO(png))
    assert bild.size == (128, 64)
    box = daten["boxes"][0]
    assert box["x"] == 2 and box["y"] == 3 and box["h"] == 14
    # "50.0C" = 5 Zeichen zu 6 Pixel bei 2x minus Abstand
    assert box["w"] == 5 * 6 * 2 - 2


def test_bildschirme_anlegen_aendern_loeschen(client: TestClient) -> None:
    r = client.post("/api/oled/screens", json={"name": "Neu", "widgets": [
        {"source": "zeit.uhr", "display": "text", "x": 0, "y": 0}]})
    assert r.status_code == 201, r.text
    neu = r.json()
    assert len(neu["id"]) == 32 and neu["widgets"][0]["opts"]["scaleX"] == 1
    version_vorher = client.get("/api/oled").json()["screensVersion"]

    neu["name"] = "Geändert"
    neu["widgets"][0]["opts"]["scaleX"] = 3
    r = client.put(f"/api/oled/screens/{neu['id']}", json=neu)
    assert r.status_code == 200 and r.json()["name"] == "Geändert"
    assert client.get("/api/oled").json()["screensVersion"] > version_vorher

    r = client.post(f"/api/oled/screens/{neu['id']}/duplicate")
    assert r.status_code == 201 and r.json()["name"] == "Geändert Kopie"
    kopie = r.json()
    assert kopie["widgets"][0]["id"] != neu["widgets"][0]["id"]

    ids = [s["id"] for s in client.get("/api/oled/screens").json()]
    r = client.post("/api/oled/screens/order", json={"ids": list(reversed(ids))})
    assert [s["id"] for s in r.json()] == list(reversed(ids))

    assert client.post(f"/api/oled/screens/{kopie['id']}/activate").json()["currentScreenId"] == kopie["id"]
    assert client.delete(f"/api/oled/screens/{kopie['id']}").status_code == 200
    assert client.delete(f"/api/oled/screens/{kopie['id']}").status_code == 404
    assert client.delete(f"/api/oled/screens/{neu['id']}").status_code == 200


def test_letzter_bildschirm_bleibt(client: TestClient) -> None:
    screens = client.get("/api/oled/screens").json()
    assert len(screens) == 1
    assert client.delete(f"/api/oled/screens/{screens[0]['id']}").status_code == 409


def test_einstellungen_patch(client: TestClient) -> None:
    r = client.patch("/api/oled/settings", json={"mode": "manual", "brightness": 77, "rotationInterval": 42})
    assert r.status_code == 200
    s = r.json()
    assert s["mode"] == "manual" and s["brightness"] == 77 and s["rotationInterval"] == 42
    assert client.patch("/api/oled/settings", json={"brightness": 999}).status_code == 422
    assert client.patch("/api/oled/settings", json={"currentScreenId": "gibtesnicht"}).status_code == 404


def test_vorlagen(client: TestClient) -> None:
    r = client.post("/api/oled/presets", json={"name": "Temp", "source": "cpu.temp", "display": "gauge",
                                                "opts": {"radius": 20}})
    assert r.status_code == 201
    p = r.json()
    assert client.get("/api/oled/presets").json()[0]["id"] == p["id"]
    p["name"] = "Temperatur"
    assert client.put(f"/api/oled/presets/{p['id']}", json=p).json()["name"] == "Temperatur"
    assert client.delete(f"/api/oled/presets/{p['id']}").status_code == 200
    assert client.get("/api/oled/presets").json() == []


def test_profile(client: TestClient) -> None:
    r = client.post("/api/oled/profiles", json={"name": "Tag"})
    assert r.status_code == 201
    profil = r.json()
    assert len(profil["screens"]) == 1
    client.post("/api/oled/screens", json={"name": "Zweiter"})
    assert len(client.get("/api/oled/screens").json()) == 2
    r = client.post(f"/api/oled/profiles/{profil['id']}/apply")
    assert r.status_code == 200 and len(r.json()["screens"]) == 1
    assert client.delete(f"/api/oled/profiles/{profil['id']}").status_code == 200
    assert client.post("/api/oled/profiles/x/apply").status_code == 404


def test_wetterorte(client: TestClient) -> None:
    assert client.get("/api/oled/weather/locations").json() == [], "ohne Bestand gibt es keinen Vorgabeort"
    treffer = client.get("/api/oled/weather/search", params={"q": "Leip"}).json()
    assert treffer[0]["name"] == "Leipzig"
    r = client.post("/api/oled/weather/locations", json=treffer[0])
    assert r.status_code == 201
    erster = r.json()
    orte = client.get("/api/oled/weather/locations").json()
    assert len(orte) == 1 and orte[0]["isDefault"], "der erste Ort wird Vorgabeort"
    client.post("/api/oled/weather/refresh", params={"locationId": erster["id"]})
    zustand = client.get("/api/oled/weather/locations").json()[0]
    assert zustand["ok"] and "9.5" in zustand["summary"]

    r = client.post("/api/oled/weather/locations", json={"name": "Hamburg", "lat": 53.55, "lon": 9.99})
    zweiter = r.json()
    assert client.post(f"/api/oled/weather/locations/{zweiter['id']}/default").json()["defaultLocationId"] == zweiter["id"]
    entwurf = {"screen": {"widgets": [{"source": "wetter.temp", "display": "text", "x": 0, "y": 0,
                                       "opts": {"locationId": erster["id"]}}]}}
    assert client.post("/api/oled/render", json=entwurf).json()["boxes"][0]["w"] > 0
    assert client.delete(f"/api/oled/weather/locations/{zweiter['id']}").status_code == 200
    rest = client.get("/api/oled/weather/locations").json()
    assert len(rest) == 1 and rest[0]["isDefault"], "Vorgabe fällt auf den verbleibenden Ort zurück"
    assert client.delete(f"/api/oled/weather/locations/{rest[0]['location']['id']}").status_code == 409


def test_export_import(client: TestClient) -> None:
    export = client.get("/api/oled/export").json()
    assert export["settings"]["screens"] and len(export["weather"]["locations"]) == 1
    anzahl = len(client.get("/api/oled/screens").json())
    r = client.post("/api/oled/import", json=export)
    assert r.status_code == 200 and r.json()["screens"] >= 1
    assert len(client.get("/api/oled/screens").json()) == anzahl + len(export["settings"]["screens"])
    r = client.post("/api/oled/import", params={"replace": "true"}, json=export)
    assert len(client.get("/api/oled/screens").json()) == len(export["settings"]["screens"])


def test_import_alte_sicherung(client: TestClient) -> None:
    sicherung = {"screens": [{"type": "system", "name": "Alt", "widgets": [
        {"source": "cpu.temp", "display": "zahl_xl", "x": 1, "y": 1, "opts": {"scaleX": 3, "scaleY": 3}}]}],
        "weatherCities": [{"name": "Berlin", "lat": 52.5, "lon": 13.4}],
        "widgetPresets": [{"source": "ram.percent", "display": "balken", "name": "RAM", "opts": {"width": 50}}],
        "profiles": []}
    r = client.post("/api/oled/import-legacy", json=sicherung)
    assert r.status_code == 200, r.text
    screens = client.get("/api/oled/screens").json()
    alt = next(s for s in screens if s["name"] == "Alt")
    assert alt["widgets"][0]["display"] == "text" and alt["widgets"][0]["opts"]["scaleX"] == 3
    assert any(o["location"]["name"] == "Berlin" for o in client.get("/api/oled/weather/locations").json())
    assert any(p["name"] == "RAM" for p in client.get("/api/oled/presets").json())


def test_gesamtstatus_enthaelt_oled(client: TestClient) -> None:
    daten = client.get("/api/state").json()
    assert daten["oled"]["screens"] and "preview" in daten["oled"]
    assert daten["fan"] and "stats" in daten
