#!/usr/bin/env node
// Prüfaufnahme einer laufenden Oberfläche: node qa-shot.mjs <Adresse> <Zieldatei.png> [Skriptdatei] [Breite] [Höhe]
// Das Skript (Rumpf einer async-Funktion) läuft nach dem Laden auf der Seite; danach wird aufgenommen.
import { mkdir, readFile, writeFile, rm } from "node:fs/promises";
import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:http";

const [adresse, ziel, skriptDatei, breiteArg, hoeheArg] = process.argv.slice(2);
const breite = Number(breiteArg ?? 1440), hoehe = Number(hoeheArg ?? 900);
const skript = skriptDatei ? await readFile(skriptDatei, "utf8") : "";
const schlafen = (ms) => new Promise((ok) => setTimeout(ok, ms));
const freierPort = () => new Promise((ok) => { const s = createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => ok(p)); }); });
const CDP = await freierPort();
const profil = join(dirname(fileURLToPath(import.meta.url)), `chrome-qa-${process.pid}`);
await mkdir(profil, { recursive: true });
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${CDP}`, "--remote-allow-origins=*",
   `--user-data-dir=${profil}`, `--window-size=${breite},${hoehe}`, "--no-first-run", "--no-default-browser-check", "about:blank"], { stdio: "ignore" });
let zielSeite = null;
for (let i = 0; i < 50 && !zielSeite; i++) {
  await schlafen(200);
  try { const liste = await (await fetch(`http://127.0.0.1:${CDP}/json`)).json(); zielSeite = liste.find((t) => t.type === "page"); } catch {}
}
const ws = new WebSocket(zielSeite.webSocketDebuggerUrl);
await new Promise((ok, nein) => { ws.onopen = ok; ws.onerror = nein; });
let nr = 0; const offen = new Map(); const konsole = [];
const senden = (method, params = {}) => new Promise((ok) => { const id = ++nr; offen.set(id, ok); ws.send(JSON.stringify({ id, method, params })); });
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && offen.has(m.id)) { offen.get(m.id)(m); offen.delete(m.id); return; }
  if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") konsole.push(m.params.args.map((a) => a.value ?? a.description).join(" "));
  if (m.method === "Runtime.exceptionThrown") konsole.push(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text);
};
await senden("Page.enable"); await senden("Runtime.enable");
await senden("Emulation.setDeviceMetricsOverride", { width: breite, height: hoehe, deviceScaleFactor: 2, mobile: breite < 800 });
await senden("Page.navigate", { url: adresse });
await schlafen(3500);
if (skript) {
  const { result } = await senden("Runtime.evaluate", { expression: `(async () => { const schlafen = (ms) => new Promise((ok) => setTimeout(ok, ms)); const klick = (sel, text) => { const el = [...document.querySelectorAll(sel)].find((e) => !text || e.textContent.includes(text)); if (el) el.click(); return !!el; }; ${skript} })()`, awaitPromise: true, returnByValue: true });
  if (result?.exceptionDetails) console.error("Skript:", result.exceptionDetails.exception?.description ?? result.exceptionDetails.text);
  else if (result?.result?.value !== undefined) console.log("Skript:", JSON.stringify(result.result.value));
  await schlafen(1200);
}
const { result } = await senden("Page.captureScreenshot", { format: "png" });
await writeFile(ziel, Buffer.from(result.data, "base64"));
console.log(`${ziel}${konsole.length ? `\nKonsolenfehler: ${konsole.slice(0, 5).join(" | ")}` : ""}`);
ws.close(); chrome.kill();
await schlafen(300);
await rm(profil, { recursive: true, force: true });
