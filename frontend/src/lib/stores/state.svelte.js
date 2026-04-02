/* PyroPlus — State Store v3.0.0 (Svelte 5 Runes) */
import { api, createWebSocket } from '../api/client.js';

let connected = $state(false);
let stats = $state({});
let fan = $state({});
let leds = $state({});
let oled = $state({});
let hwProxy = $state({});
let version = $state('');
let effectsCatalog = $state({});
let customData = $state({});
let toasts = $state([]);
let currentView = $state('fan');
let apiToken = $state('');
let ws = null;

function handleWs(msg) {
  if (msg.type === 'stats') {
    connected = true;
    stats = msg.data.stats || stats;
    fan = { ...fan, ...msg.data.fan };
    if (msg.data.leds) leds = { ...leds, ...msg.data.leds };
    if (msg.data.oled) oled = { ...oled, ...msg.data.oled };
    if (msg.data.custom_data) customData = msg.data.custom_data;
  }
}

async function init() {
  apiToken = await api.fetchToken();
  const s = await api.state();
  if (!s.error) {
    version = s.version || '';
    hwProxy = s.hw_proxy || {};
    fan = s.fan || {};
    oled = s.oled || {};
    leds = s.leds || {};
    stats = s.stats || {};
    customData = s.custom_data || {};
    connected = true;
  }
  const fx = await api.leds.effects();
  if (!fx?.error) effectsCatalog = fx;
  ws = createWebSocket(handleWs);
}

let _tid = 0;
function toast(msg, type = 'info') {
  const id = ++_tid;
  toasts = [...toasts, { id, msg, type }];
  setTimeout(() => { toasts = toasts.filter(t => t.id !== id); }, 3000);
}

function destroy() { ws?.close(); }

export function getState() {
  return {
    get connected() { return connected; },
    get stats() { return stats; },
    get fan() { return fan; },
    get leds() { return leds; },
    get oled() { return oled; },
    get hwProxy() { return hwProxy; },
    get version() { return version; },
    get effectsCatalog() { return effectsCatalog; },
    get customData() { return customData; },
    get toasts() { return toasts; },
    get currentView() { return currentView; },
    get apiToken() { return apiToken; },
    set currentView(v) { currentView = v; },

    init, destroy, toast,

    get ledsActive() { return leds?.effect && leds.effect !== 'off'; },
    get oledActive() { return oled?.mode && oled.mode !== 'off'; },
    get fanActive() { return fan?.mode && fan.mode !== 'off'; },

    /* Interne Updater für Komponenten */
    updateOled(patch) { oled = { ...oled, ...patch }; },
    updateLeds(patch) { leds = { ...leds, ...patch }; },
    updateFan(patch) { fan = { ...fan, ...patch }; },

    async toggleLeds() {
      if (leds?.effect !== 'off') { await api.quick.ledsOff(); leds = { ...leds, effect: 'off' }; toast('LEDs aus', 'ok'); }
      else { const r = await api.quick.ledsOn(); leds = { ...leds, effect: r.effect || 'static' }; toast('LEDs ein', 'ok'); }
    },
    async toggleOled() {
      if (oled?.mode !== 'off') { await api.quick.oledOff(); oled = { ...oled, mode: 'off' }; toast('Display aus', 'ok'); }
      else { await api.quick.oledOn(); oled = { ...oled, mode: 'auto' }; toast('Display ein', 'ok'); }
    },
    async toggleFan() {
      if (fan?.mode !== 'off') { await api.quick.fanOff(); fan = { ...fan, mode: 'off', fan_on: false, current_speed: 0 }; toast('Lüfter aus', 'ok'); }
      else { await api.quick.fanAuto(); fan = { ...fan, mode: 'auto' }; toast('Lüfter ein (Auto)', 'ok'); }
    },

    async setFanMode(m) { const r = await api.fan.mode(m); if (!r.error) { fan = { ...fan, mode: m, fan_on: m !== 'off' && (m === 'manual' || fan.fan_on) }; toast(`Lüfter → ${m}`, 'ok'); } },
    async setFanProfile(p) { const r = await api.fan.profile(p); if (!r.error) { fan = { ...fan, ...r }; toast(`Profil → ${p}`, 'ok'); } },
    async setFanManualSpeed(s) { await api.fan.manualSpeed(s); fan = { ...fan, manual_speed: s }; },
    async setFanCurve(points) { const r = await api.fan.curve(points); if (!r.error) fan = { ...fan, curve: r.curve || points }; },
    async setFanSettings(settings) { const r = await api.fan.settings(settings); if (!r.error) fan = { ...fan, settings: { ...fan.settings, ...r.settings } }; },

    async setLedEffect(n) { await api.leds.effect(n); leds = { ...leds, effect: n }; toast(`LED → ${n}`, 'ok'); },
    async setLedColor(r, g, b) { await api.leds.color(r, g, b); leds = { ...leds, color: { r, g, b } }; },
    async setLedColor2(r, g, b) { await api.leds.color2(r, g, b); leds = { ...leds, color2: { r, g, b } }; },
    async setLedBrightness(v) { await api.leds.brightness(v); leds = { ...leds, brightness: v }; },
    async setLedSpeed(v) { await api.leds.speed(v); leds = { ...leds, speed: v }; },
    async setLedIndividual(on) {
      await api.leds.individualMode(on);
      leds = { ...leds, individual_mode: on };
    },
    async setLedIndColor(i, r, g, b) {
      await api.leds.individualColor(i, r, g, b);
      const cols = [...(leds.individual_colors || [])];
      cols[i] = { r, g, b };
      leds = { ...leds, individual_colors: cols };
    },

    async setOledMode(m) { await api.oled.mode(m); oled = { ...oled, mode: m }; toast(`Display → ${m}`, 'ok'); },
    async setOledBrightness(v) { await api.oled.brightness(v); oled = { ...oled, brightness: v }; },
    async setOledRotation(s) { await api.oled.rotation(s); oled = { ...oled, rotation_interval: s }; },

    /* OLED Screen-Verwaltung */
    async selectOledScreen(i) {
      const r = await api.oled.screen(i);
      oled = { ...oled, current_screen: i, ...(r?.preview ? { preview: r.preview } : {}) };
    },
    async addOledScreen(screenData) {
      const data = screenData || { type: 'system', name: `Screen ${(oled.screens||[]).length+1}`, widgets: [
        { type: 'clock', x: 0, y: 0, size: 'large' },
        { type: 'cpu_temp', x: 0, y: 24, size: 'small' },
      ]};
      const r = await api.oled.addScreen(data);
      if (r?.screens) oled = { ...oled, screens: r.screens };
      return r;
    },
    async updateOledScreen(i, data) {
      const r = await api.oled.updateScreen(i, data);
      if (r?.screens) oled = { ...oled, screens: r.screens, ...(r.preview ? { preview: r.preview } : {}) };
    },
    async removeOledScreen(i) {
      if ((oled.screens||[]).length <= 1) return;
      const r = await api.oled.removeScreen(i);
      if (r?.screens) oled = { ...oled, screens: r.screens };
    },
    async reorderOledScreens(order) {
      const r = await api.oled.reorderScreens(order);
      if (r?.screens) oled = { ...oled, screens: r.screens };
    },

    /* OLED Uhreinstellungen */
    async setClockSettings(settings) {
      const r = await api.oled.clockSettings(settings);
      if (r?.clock_settings) oled = { ...oled, clock_settings: r.clock_settings };
    },

    /* Pixel Art */
    async savePixelArt(id, name, pixels) {
      return await api.oled.savePixelArt({ id, name, pixels });
    },
    async deletePixelArt(id) {
      await api.oled.deletePixelArt(id);
      oled = { ...oled, pixel_arts: (oled.pixel_arts||[]).filter(p => p.id !== id) };
    },
    async loadPixelArt(id) {
      return await api.oled.getPixelArt(id);
    },
  };
}
