#!/usr/bin/env node
// Prüft die laufende Oberfläche in allen Bereichen und mehreren Fensterbreiten auf Layoutfehler:
//   - Seite rollt seitlich
//   - Element ragt über einen Vorfahren hinaus, der abschneidet (abgeschnittener Inhalt)
//   - Inhalt breiter als sein Kasten (scrollWidth > clientWidth), außer gewollte Auslassungspunkte
//   - Text in Knöpfen und Chips bricht um oder wird oben/unten abgeschnitten
//   - sichtbare Knöpfe und Felder überlappen einander
// Aufruf: node tools/ui-pruefung.mjs [Adresse] [--bilder]   Vorgabe: http://localhost:5173
// Braucht ein laufendes Backend; die Prüfung klickt nur auf Reiter, Auswahl und Fenster, sie speichert nichts
// außer der Wahl im LED-Bereich. Nicht gegen den Betrieb mit echter Hardware laufen lassen.
// Ergebnis: Liste der Befunde je Ansicht und Breite, Rückgabewert 1 bei Befunden.
// Ohne Befunde vermerkt die Prüfung den geprüften Stand (Prüfsumme über frontend/src, frontend/static,
// frontend/index.html) in tools/ui-pruefung/bestanden. node tools/ui-pruefung.mjs --stand gibt die
// Prüfsumme des aktuellen Stands aus; der Pre-Push-Hook vergleicht beides.
import { mkdir, writeFile, rm, readFile, readdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:http";

const WURZEL = join(dirname(fileURLToPath(import.meta.url)), "..");

/* Prüfsumme über alles, was das Aussehen der Oberfläche bestimmt */
async function stand() {
  const hash = createHash("sha256");
  const sammeln = async (pfad) => {
    let eintraege;
    try { eintraege = await readdir(pfad, { withFileTypes: true }); } catch { hash.update(await readFile(pfad)); return; }
    for (const e of eintraege.sort((a, b) => a.name.localeCompare(b.name))) {
      const voll = join(pfad, e.name);
      if (e.isDirectory()) await sammeln(voll); else { hash.update(voll.slice(WURZEL.length)); hash.update(await readFile(voll)); }
    }
  };
  for (const teil of ["frontend/src", "frontend/static", "frontend/index.html"]) await sammeln(join(WURZEL, teil));
  return hash.digest("hex");
}
if (process.argv.includes("--stand")) { console.log(await stand()); process.exit(0); }
const STAND_VORHER = await stand();
const ADRESSE = process.argv.slice(2).find((a) => !a.startsWith("--")) ?? "http://localhost:5173";
const BILDER = process.argv.includes("--bilder");
const ABLAGE = join(WURZEL, "tools", "ui-pruefung");

const GROESSEN = [
  { name: "1920", w: 1920, h: 1080, mobil: false },
  { name: "1440", w: 1440, h: 900, mobil: false },
  { name: "1280", w: 1280, h: 800, mobil: false },
  { name: "1100", w: 1100, h: 760, mobil: false },
  { name: "1024", w: 1024, h: 768, mobil: false },
  { name: "820", w: 820, h: 1180, mobil: true },
  { name: "390", w: 390, h: 844, mobil: true },
  { name: "360", w: 360, h: 740, mobil: true },
];

// Ansichten: Route und Schritte in der Seite. Schritte nutzen klick(selektor, text) und schlafen(ms).
const ANSICHTEN_RECHNER = [
  { name: "display-leer", route: "#/display", schritte: "" },
  { name: "display-eigenschaften", route: "#/display", schritte: `waehleErstesWidget(); await schlafen(900);` },
  { name: "display-mehrfach", route: "#/display", schritte: `waehleAlleWidgets(); await schlafen(900);` },
  { name: "display-hinzufuegen", route: "#/display", schritte: `klick(".reiter button", "Hinzufügen"); await schlafen(600); klick(".quelle"); await schlafen(500); klick(".chip", "Symbol + Wert"); await schlafen(1500);` },
  { name: "display-vorschau-schmal", route: "#/display", schritte: `klick(".reiter button", "Hinzufügen"); await schlafen(600); klick(".quelle"); await schlafen(1200);` },
  { name: "display-hinzufuegen-unten", route: "#/display", schritte: `klick(".reiter button", "Hinzufügen"); await schlafen(600); klick(".quelle"); await schlafen(500); klick(".chip", "Balken + Wert"); await schlafen(1200); rollen(".spalte-rechts .spalte-inhalt", 99999); await schlafen(400);` },
  { name: "display-bausteine", route: "#/display", schritte: `klick(".reiter button", "Bausteine"); await schlafen(2500);` },
  { name: "display-bausteine-unten", route: "#/display", schritte: `klick(".reiter button", "Bausteine"); await schlafen(2500); rollen(".spalte-rechts .spalte-inhalt", 99999); await schlafen(600);` },
  { name: "fenster-vorlagen", route: "#/display", schritte: `klick("button", "Vorlagen"); await schlafen(2500);` },
  { name: "fenster-profile", route: "#/display", schritte: `klick("button", "Profile"); await schlafen(1200);` },
  { name: "fenster-wetterorte", route: "#/display", schritte: `klick("button", "Wetterorte"); await schlafen(1200);` },
  { name: "fenster-hilfe", route: "#/display", schritte: `klick('[title="Hilfe öffnen"]'); await schlafen(1000);` },
  { name: "seitenleiste-umgeschaltet", route: "#/display", schritte: `klick(".sb-collapse"); await schlafen(600); waehleErstesWidget(); await schlafen(600);` },
  { name: "luefter", route: "#/fan", schritte: "" },
  { name: "leds-farben", route: "#/leds", schritte: "" },
  { name: "leds-animationen", route: "#/leds", schritte: `klick("button", "Animationen"); await schlafen(600);` },
  { name: "leds-spielereien", route: "#/leds", schritte: `klick("button", "Spielereien"); await schlafen(600);` },
];
const ANSICHTEN_TELEFON = [
  { name: "m-display", route: "#/display", schritte: "" },
  { name: "m-display-unten", route: "#/display", schritte: `rollen(".mobil-inhalt", 99999); await schlafen(400);` },
  { name: "m-vorlagen", route: "#/display", schritte: `klick('[title="Fertigen Bildschirm aus den Vorlagen einfügen"]'); await schlafen(2500);` },
  { name: "m-luefter", route: "#/fan", schritte: "" },
  { name: "m-leds", route: "#/leds", schritte: "" },
  { name: "m-leds-unten", route: "#/leds", schritte: `rollen(".mobil-inhalt", 99999); await schlafen(400);` },
];

const HILFEN = `
const schlafen = (ms) => new Promise((ok) => setTimeout(ok, ms));
const klick = (sel, text) => { const el = [...document.querySelectorAll(sel)].find((e) => !text || e.textContent.includes(text)); if (el) el.click(); return !!el; };
const rollen = (sel, y) => { for (const e of document.querySelectorAll(sel)) e.scrollTop = y; };
const zeiger = (s, typ, x, y) => s.dispatchEvent(new PointerEvent(typ, { clientX: x, clientY: y, bubbles: true, pointerId: 1, button: 0, isPrimary: true }));
/* Tastet das Display im 6-Pixel-Raster ab, bis ein Widget gewählt ist */
const waehleErstesWidget = () => {
  const s = document.querySelector(".geraet-schirm"); if (!s) return;
  const r = s.getBoundingClientRect(), z = r.width / 128;
  for (let y = 3; y < 64; y += 6) for (let x = 3; x < 128; x += 6) {
    zeiger(s, "pointerdown", r.left + x * z, r.top + y * z); zeiger(s, "pointerup", r.left + x * z, r.top + y * z);
    if (document.querySelector(".auswahl")) return;
  }
};
const waehleAlleWidgets = () => { document.dispatchEvent(new KeyboardEvent("keydown", { key: "a", ctrlKey: true, bubbles: true })); window.dispatchEvent(new KeyboardEvent("keydown", { key: "a", ctrlKey: true, bubbles: true })); };
`;

// Läuft in der Seite: sucht Layoutfehler und liefert sie als Liste
const PRUEFEN = String.raw`(() => {
  const befunde = [];
  const pfad = (el) => {
    const teile = [];
    for (let e = el; e && e !== document.body && teile.length < 4; e = e.parentElement) {
      let t = e.tagName.toLowerCase();
      if (e.classList.length) t += "." + [...e.classList].filter((k) => !k.startsWith("s-")).slice(0, 2).join(".");
      teile.unshift(t);
    }
    const text = (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 30);
    return teile.join(" > ") + (text ? ' "' + text + '"' : "");
  };
  const sichtbar = (el) => {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden" || Number(s.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  /* Sichtbarer Ausschnitt: Rahmen geschnitten mit allen Vorfahren, die senkrecht rollen oder abschneiden */
  const ausschnitt = (el) => {
    const r = el.getBoundingClientRect();
    let a = { l: r.left, t: r.top, r: r.right, b: r.bottom };
    for (let v = el.parentElement; v && v !== document.body; v = v.parentElement) {
      if (getComputedStyle(v).overflowY === "visible") continue;
      const vr = v.getBoundingClientRect();
      a = { l: Math.max(a.l, vr.left), t: Math.max(a.t, vr.top), r: Math.min(a.r, vr.right), b: Math.min(a.b, vr.bottom) };
    }
    a = { l: Math.max(a.l, 0), t: Math.max(a.t, 0), r: Math.min(a.r, innerWidth), b: Math.min(a.b, innerHeight) };
    return a.r - a.l > 1 && a.b - a.t > 1 ? a : null;
  };
  /* Liegt das Element in einer festen Leiste (fixed oder sticky)? Inhalte rollen gewollt darunter. */
  const festeLeiste = (el) => { for (let e = el; e && e !== document.body; e = e.parentElement) { const p = getComputedStyle(e).position; if (p === "fixed" || p === "sticky") return e; } return null; };
  const doc = document.documentElement;
  if (doc.scrollWidth > innerWidth + 1) befunde.push("Seite rollt seitlich: " + doc.scrollWidth + " > " + innerWidth);

  const alle = [...document.body.querySelectorAll("*")].filter(sichtbar);
  for (const el of alle) {
    const s = getComputedStyle(el);
    if (el.closest(".geraet-schirm, svg")) continue;   // Pixelfläche: Auswahlrahmen und Etiketten dürfen überstehen
    const r = el.getBoundingClientRect();
    // 1. über einen abschneidenden Vorfahren hinaus (waagerecht)
    for (let v = el.parentElement; v && v !== document.body; v = v.parentElement) {
      const vs = getComputedStyle(v);
      if (vs.overflowX === "visible") continue;
      const vr = v.getBoundingClientRect();
      const rechts = r.right - vr.right, links = vr.left - r.left;
      if ((rechts > 1.5 || links > 1.5) && r.width <= vr.width + 400) {
        // Elemente in seitlich rollbaren Leisten sind gewollt
        if (vs.overflowX === "auto" || vs.overflowX === "scroll") break;
        befunde.push("abgeschnitten: " + pfad(el) + " ragt " + Math.round(Math.max(rechts, links)) + " px über " + pfad(v).split(' "')[0]);
      }
      break;
    }
    // 2. Inhalt breiter als der eigene Kasten
    const ellipse = s.textOverflow === "ellipsis";
    if (!ellipse && el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0 && s.overflowX !== "auto" && s.overflowX !== "scroll"
        && !["INPUT", "TEXTAREA", "SELECT", "IMG", "svg"].includes(el.tagName)) {
      befunde.push("Inhalt zu breit: " + pfad(el) + " " + el.scrollWidth + " > " + el.clientWidth);
    }
    // 3. Knöpfe und Chips: Text bricht um oder wird senkrecht abgeschnitten
    if (el.matches("button, .chip, .badge, .chip-status") && !el.closest(".hilfe-text")) {
      if (el.scrollHeight > el.clientHeight + 1 && el.clientHeight > 0) befunde.push("Knopftext abgeschnitten: " + pfad(el));
      const zeilen = Math.round(r.height / parseFloat(s.lineHeight || "0"));
      if (s.whiteSpace !== "nowrap" && el.matches(".chip, .badge, .chip-status") && zeilen > 1 && r.height > 40) befunde.push("Chip bricht um: " + pfad(el));
    }
  }
  // 4. Überlappende Bedienelemente
  const bedien = alle.filter((e) => e.matches("button, input, select, textarea, .chip") && !e.closest(".geraet-schirm, .kontext, .toast"))
    .map((e) => ({ e, a: ausschnitt(e), leiste: festeLeiste(e), fenster: e.closest(".fenster, .hilfe-fenster, [role=dialog]") })).filter((x) => x.a);
  for (let i = 0; i < bedien.length; i++) {
    const { e: ei, a, leiste: li, fenster: fi } = bedien[i];
    for (let j = i + 1; j < bedien.length; j++) {
      const { e: b, a: c, leiste: lj, fenster: fj } = bedien[j];
      if (ei.contains(b) || b.contains(ei)) continue;
      if ((li || lj) && li !== lj) continue;   // feste Leiste über rollendem Inhalt
      if (fi !== fj) continue;                 // schwebendes Fenster über der Seite
      const x = Math.min(a.r, c.r) - Math.max(a.l, c.l), y = Math.min(a.b, c.b) - Math.max(a.t, c.t);
      if (x > 2 && y > 2) befunde.push("Überlappung: " + pfad(bedien[i]) + " / " + pfad(b));
    }
  }
  return [...new Set(befunde)];
})()`;

const schlafen = (ms) => new Promise((ok) => setTimeout(ok, ms));
const freierPort = () => new Promise((ok) => { const s = createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => ok(p)); }); });
try { await fetch(ADRESSE, { signal: AbortSignal.timeout(3000) }); } catch { console.error(`Die Oberfläche antwortet nicht unter ${ADRESSE}.`); process.exit(2); }

const CDP = await freierPort();
const profil = join(WURZEL, "tools", `chrome-pruefung-${process.pid}`);
await mkdir(profil, { recursive: true });
if (BILDER) await mkdir(ABLAGE, { recursive: true });
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${CDP}`, "--remote-allow-origins=*",
   `--user-data-dir=${profil}`, "--window-size=1440,900", "--no-first-run", "--no-default-browser-check", "about:blank"], { stdio: "ignore" });
let ziel = null;
for (let i = 0; i < 150 && !ziel; i++) {
  await schlafen(200);
  try { ziel = (await (await fetch(`http://127.0.0.1:${CDP}/json`)).json()).find((t) => t.type === "page"); } catch {}
}
if (!ziel) { console.error("Chrome startet nicht (30 s gewartet)."); chrome.kill(); process.exit(2); }
const ws = new WebSocket(ziel.webSocketDebuggerUrl);
await new Promise((ok, nein) => { ws.onopen = ok; ws.onerror = nein; });
let nr = 0; const offen = new Map();
const senden = (method, params = {}) => new Promise((ok) => { const id = ++nr; offen.set(id, ok); ws.send(JSON.stringify({ id, method, params })); });
ws.onmessage = (ev) => { const m = JSON.parse(ev.data); if (m.id && offen.has(m.id)) { offen.get(m.id)(m); offen.delete(m.id); } };
await senden("Page.enable");

let gesamt = 0;
for (const g of GROESSEN) {
  await senden("Emulation.setDeviceMetricsOverride", { width: g.w, height: g.h, deviceScaleFactor: 1, mobile: g.mobil });
  for (const a of g.mobil ? ANSICHTEN_TELEFON : ANSICHTEN_RECHNER) {
    await senden("Page.navigate", { url: "about:blank" });
    await senden("Page.navigate", { url: `${ADRESSE}/${a.route}` });
    await schlafen(2500);
    if (a.schritte) {
      const { result } = await senden("Runtime.evaluate", { expression: `(async () => { ${HILFEN} ${a.schritte} })()`, awaitPromise: true });
      if (result?.exceptionDetails) console.error(`  Schritte ${a.name}: ${result.exceptionDetails.exception?.description ?? result.exceptionDetails.text}`);
    }
    await schlafen(500);
    const { result } = await senden("Runtime.evaluate", { expression: PRUEFEN, returnByValue: true });
    const befunde = result?.result?.value ?? [`Prüfung fehlgeschlagen: ${result?.exceptionDetails?.text ?? "?"}`];
    if (befunde.length) {
      gesamt += befunde.length;
      console.log(`\n${a.name} @ ${g.name}`);
      for (const b of befunde) console.log(`  - ${b}`);
    }
    if (BILDER) {
      const { result: bild } = await senden("Page.captureScreenshot", { format: "png" });
      await writeFile(join(ABLAGE, `${a.name}-${g.name}.png`), Buffer.from(bild.data, "base64"));
    }
  }
}
ws.close(); chrome.kill();
await schlafen(300);
await rm(profil, { recursive: true, force: true });
console.log(gesamt ? `\n${gesamt} Befunde` : "Keine Befunde");
if (!gesamt) {
  if (await stand() !== STAND_VORHER) { console.error("Die Oberfläche wurde während der Prüfung geändert, kein Vermerk."); process.exit(1); }
  await mkdir(ABLAGE, { recursive: true });
  await writeFile(join(ABLAGE, "bestanden"), STAND_VORHER + "\n");
}
process.exit(gesamt ? 1 : 0);
