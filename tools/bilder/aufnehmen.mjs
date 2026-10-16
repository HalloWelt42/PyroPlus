#!/usr/bin/env node
// README-Aufnahmen der laufenden PyroPlus-Oberfläche, kopflos über das DevTools-Protokoll.
// Aufruf: node tools/bilder/aufnehmen.mjs http://<pi>:8070 [Szene ...]   (vorher: vorbereiten.py)
// Nur lesend: jede Anfrage außer GET/HEAD/OPTIONS und POST .../api/oled/render bekommt 409.
// Der Zustand .../api/oled wird aus szenen.json beantwortet (Vorlagen statt des echten Bestands).
import { mkdir, readFile, writeFile, rm } from "node:fs/promises";
import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:http";

const HIER = dirname(fileURLToPath(import.meta.url));
const ADRESSE = process.argv[2];
if (!ADRESSE) { console.error("Adresse der Oberfläche angeben, zum Beispiel http://<pi>:8070"); process.exit(1); }
const NUR = process.argv.slice(3);
const { zustand, klickziele, vorschau } = JSON.parse(await readFile(join(HIER, "szenen.json"), "utf8"));
const ABLAGE = join(HIER, "roh");
await mkdir(ABLAGE, { recursive: true });

const schlafen = (ms) => new Promise((ok) => setTimeout(ok, ms));
const freierPort = () => new Promise((ok) => { const s = createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => ok(p)); }); });
const CDP = await freierPort();
const profil = join(HIER, `chrome-profil-${process.pid}`);
await mkdir(profil, { recursive: true });
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${CDP}`, "--remote-allow-origins=*",
   `--user-data-dir=${profil}`, "--window-size=1440,900", "--no-first-run", "--no-default-browser-check", "about:blank"], { stdio: "ignore" });
let ziel = null;
for (let i = 0; i < 50 && !ziel; i++) {
  await schlafen(200);
  try { const liste = await (await fetch(`http://127.0.0.1:${CDP}/json`)).json(); ziel = liste.find((t) => t.type === "page"); } catch {}
}
if (!ziel) { console.error("Chrome antwortet nicht."); chrome.kill(); process.exit(1); }
const ws = new WebSocket(ziel.webSocketDebuggerUrl);
await new Promise((ok, nein) => { ws.onopen = ok; ws.onerror = nein; });
let nr = 0; const offen = new Map();
const senden = (method, params = {}) => new Promise((ok) => { const id = ++nr; offen.set(id, ok); ws.send(JSON.stringify({ id, method, params })); });
const LESEND = new Set(["GET", "HEAD", "OPTIONS"]);
const antworten = (requestId, code, inhalt) => senden("Fetch.fulfillRequest", {
  requestId, responseCode: code, responseHeaders: [{ name: "Content-Type", value: "application/json" }],
  body: Buffer.from(JSON.stringify(inhalt), "utf8").toString("base64"),
});
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && offen.has(m.id)) { offen.get(m.id)(m); offen.delete(m.id); return; }
  if (m.method !== "Fetch.requestPaused") return;
  const { requestId, request } = m.params;
  const pfad = new URL(request.url).pathname;
  if (request.method === "GET" && pfad === "/api/oled") { void antworten(requestId, 200, zustand); return; }
  if (request.method === "POST" && (pfad === "/api/oled/render" || pfad === "/api/oled/render/widget") && request.postData) {
    try {
      const body = JSON.parse(request.postData);
      const widgets = [...(body.screen?.widgets ?? []), ...(body.widget ? [body.widget] : [])];
      for (const w of widgets) if (w.source === "net.ip") { w.source = "text.frei"; w.opts = { ...(w.opts ?? {}), text: "192.0.2.10" }; }
      void senden("Fetch.continueRequest", { requestId, postData: Buffer.from(JSON.stringify(body), "utf8").toString("base64") });
    } catch { void senden("Fetch.continueRequest", { requestId }); }
    return;
  }
  if (LESEND.has(request.method)) { void senden("Fetch.continueRequest", { requestId }); return; }
  console.log(`  [blockiert] ${request.method} ${pfad}`);
  void antworten(requestId, 409, { detail: "Nur lesend: diese Aufnahme schreibt nichts." });
};
await senden("Page.enable");
// Live-Kanal: Vorschaubild und aktiver Bildschirm zeigen den Beispielbildschirm, nicht den echten Bestand
await senden("Page.addScriptToEvaluateOnNewDocument", { source: `(() => {
  const VORSCHAU = ${JSON.stringify(vorschau)}; const ID = ${JSON.stringify(zustand.screens[0].id)};
  const anpassen = (text) => { try { const o = JSON.parse(text); const gehe = (x) => { if (x && typeof x === "object") { if ("screensVersion" in x && "preview" in x) { x.preview = VORSCHAU; x.currentScreenId = ID; } for (const k in x) gehe(x[k]); } }; gehe(o); return JSON.stringify(o); } catch { return text; } };
  const wrap = (fn) => function (ev) { return fn.call(this, typeof ev.data === "string" ? new MessageEvent("message", { data: anpassen(ev.data) }) : ev); };
  const d = Object.getOwnPropertyDescriptor(WebSocket.prototype, "onmessage");
  Object.defineProperty(WebSocket.prototype, "onmessage", { set(fn) { d.set.call(this, typeof fn === "function" ? wrap(fn) : fn); }, get() { return d.get.call(this); } });
  const add = WebSocket.prototype.addEventListener;
  WebSocket.prototype.addEventListener = function (typ, fn, opt) { return add.call(this, typ, typ === "message" && typeof fn === "function" ? wrap(fn) : fn, opt); };
})();` });
await senden("Fetch.enable", { patterns: [{ urlPattern: "*", requestStage: "Request" }] });

const js = async (ausdruck) => {
  const { result } = await senden("Runtime.evaluate", { expression: `(async () => { ${ausdruck} })()`, awaitPromise: true, returnByValue: true });
  if (result?.exceptionDetails) console.error("  JS:", result.exceptionDetails.exception?.description ?? result.exceptionDetails.text);
  return result?.result?.value;
};
const klick = async (x, y) => {
  await senden("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await senden("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await senden("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
};
const klickElement = async (selektor, text) => {
  const pos = await js(`
    const alle = [...document.querySelectorAll(${JSON.stringify(selektor)})];
    const el = ${text ? `alle.find((e) => e.textContent.includes(${JSON.stringify(text)}))` : "alle[0]"};
    if (!el) return null; el.scrollIntoView({ block: "nearest" });
    const r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 };`);
  if (!pos) { console.error(`  nicht gefunden: ${selektor} ${text ?? ""}`); return false; }
  await klick(pos.x, pos.y); await schlafen(500); return true;
};
// Klick auf ein Widget: Rahmen aus szenen.json, Lage über das Display-Element
const klickWidget = async (szene) => {
  const z = klickziele[szene]; if (!z) return;
  const pos = await js(`
    const s = document.querySelector(".geraet-schirm"); if (!s) return null;
    const r = s.getBoundingClientRect(); const zoom = r.width / 128;
    return { x: r.left + ${z.cx} * zoom, y: r.top + ${z.cy} * zoom };`);
  if (!pos) { console.error("  Display nicht gefunden"); return; }
  await klick(pos.x, pos.y); await schlafen(700);
};
const bildschirmWaehlen = async (name) => klickElement(".bs-name", name);

const SZENEN = [
  { name: "editor", route: "#/display", vorher: async () => { await klickWidget("System"); } },
  { name: "hinzufuegen", route: "#/display", vorher: async () => {
      await bildschirmWaehlen("Uhr"); await schlafen(800);
      await klickElement(".reiter button", "Hinzufügen");
      await klickElement(".quelle", "Temperatur");
      await klickElement(".chip", "Symbol + Wert");
      await schlafen(1800);
      await js(`const t = [...document.querySelectorAll(".spalte-rechts .gruppe-titel")].find((e) => e.textContent.trim().startsWith("Symbol")); if (t) t.scrollIntoView({ block: "start" });`);
      await schlafen(600);
    } },
  { name: "bausteine", route: "#/display", vorher: async () => {
      await bildschirmWaehlen("Messuhren"); await schlafen(600);
      await klickElement(".reiter button", "Bausteine");
      await schlafen(2500);
      await klickElement(".spalte-rechts .chip", "System");
      await schlafen(2000);
    } },
  { name: "vorlagen", route: "#/display", vorher: async () => {
      await klickElement('[title="Fertige Bildschirme einfügen und danach anpassen"]');
      await schlafen(1500);
      await klickElement(".kategorien .chip", "System");
      await schlafen(600);
      await klickElement(".vorlage", "Messuhren");
    } },
  { name: "pixel", route: "#/display", vorher: async () => {
      await bildschirmWaehlen("Logo"); await schlafen(900);
      await klickWidget("Logo");
      await klickElement('[title^="Zeichenmodus starten"]');
      await schlafen(700);
    } },
  { name: "hilfe", route: "#/display", vorher: async () => { await klickElement('[title="Hilfe öffnen"]'); await schlafen(800); } },
  { name: "fan", route: "#/fan" },
  { name: "leds", route: "#/leds" },
  { name: "m-display", route: "#/display", mobil: true },
  { name: "m-vorlagen", route: "#/display", mobil: true, vorher: async () => { await klickElement('[title="Fertigen Bildschirm aus den Vorlagen einfügen"]'); await schlafen(1500); } },
  { name: "m-fan", route: "#/fan", mobil: true },
  { name: "m-leds", route: "#/leds", mobil: true },
];

for (const s of SZENEN) {
  if (NUR.length && !NUR.includes(s.name)) continue;
  if (s.mobil) await senden("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 3, mobile: true });
  else await senden("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 2, mobile: false });
  await senden("Page.navigate", { url: "about:blank" });
  await schlafen(200);
  await senden("Page.navigate", { url: `${ADRESSE}/${s.route}` });
  await schlafen(3000);
  if (s.vorher) await s.vorher();
  await schlafen(600);
  const { result } = await senden("Page.captureScreenshot", { format: "png" });
  await writeFile(join(ABLAGE, `${s.name}.png`), Buffer.from(result.data, "base64"));
  console.log(`${s.name}.png`);
}
ws.close(); chrome.kill();
await schlafen(300);
await rm(profil, { recursive: true, force: true });
