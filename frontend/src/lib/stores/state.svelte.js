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
let _pollTimer = null;

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

/* Polling als Fallback — zuverlässiger als WebSocket allein */
async function pollState() {
  try {
    const s = await api.state();
    if (!s.error) {
      connected = true;
      if (s.stats) stats = s.stats;
      if (s.fan) fan = { ...fan, ...s.fan };
      if (s.leds) {
        leds = { ...leds, ...s.leds };
        // led_states werden im State gespeichert, die Engine nutzt sie für temp_reactive
      }
      if (s.oled) oled = { ...oled, ...s.oled };
      if (s.version) version = s.version;
      if (s.hw_proxy) hwProxy = s.hw_proxy;
    }
  } catch {
    connected = false;
  }
}

async function init() {
  apiToken = await api.fetchToken();
  await pollState();
  const fx = await api.leds.effects();
  if (!fx?.error) effectsCatalog = fx;
  /* WebSocket für schnelle Updates + Polling als Fallback */
  ws = createWebSocket(handleWs);
  _pollTimer = setInterval(pollState, 1000);
  _startLedEngine();
}

let _tid = 0;
function toast(msg, type = 'info') {
  const id = ++_tid;
  toasts = [...toasts, { id, msg, type }];
  setTimeout(() => { toasts = toasts.filter(t => t.id !== id); }, 3000);
}

function destroy() { ws?.close(); if (_pollTimer) clearInterval(_pollTimer); _stopLedEngine(); }

/* ═══ GLOBALER LED-STATE + ENGINE ═══
   Eigene Animation bei 25 FPS im Frontend.
   Gleiche Konfiguration wie Hardware-Proxy.
   Schreibt in ledDisplay — alle Anzeigen lesen davon. */
const N = 4;
let ledDisplay = $state([
  {r:0,g:0,b:0,rgb:'rgb(0,0,0)',glow:'rgba(0,0,0,0.5)'},
  {r:0,g:0,b:0,rgb:'rgb(0,0,0)',glow:'rgba(0,0,0,0.5)'},
  {r:0,g:0,b:0,rgb:'rgb(0,0,0)',glow:'rgba(0,0,0,0.5)'},
  {r:0,g:0,b:0,rgb:'rgb(0,0,0)',glow:'rgba(0,0,0,0.5)'},
]);
let _ledRaf = 0;
let _ledStep = 0;
let _ledLast = 0;
const LED_MS = 1000 / 25;

function setLedDisplay(leds4) {
  ledDisplay = leds4.map(l => {
    const r = l.r || 0, g = l.g || 0, b = l.b || 0;
    return { r, g, b, rgb: `rgb(${r},${g},${b})`, glow: `rgba(${r},${g},${b},0.5)` };
  });
}

function _hsv(h,s,v) {
  h=((h%360)+360)%360;
  const c=v*s,x=c*(1-Math.abs((h/60)%2-1)),m=v-c;
  let r,g,b;
  if(h<60){r=c;g=x;b=0;}else if(h<120){r=x;g=c;b=0;}else if(h<180){r=0;g=c;b=x;}
  else if(h<240){r=0;g=x;b=c;}else if(h<300){r=x;g=0;b=c;}else{r=c;g=0;b=x;}
  return{r:Math.round((r+m)*255),g:Math.round((g+m)*255),b:Math.round((b+m)*255)};
}

function _ledTick(now) {
  _ledRaf = requestAnimationFrame(_ledTick);
  if (now - _ledLast < LED_MS) return;
  _ledLast = now;

  const fx = leds?.effect || 'off';
  const br = Math.pow((leds?.brightness || 500) / 1000, 0.6);
  const spd = Math.pow((leds?.speed || 50) / 100, 1.5);
  const c = leds?.color || {r:0,g:100,b:255};
  const c2 = leds?.color2 || {r:255,g:0,b:0};
  const step = _ledStep;

  // Temperatur/Last-reaktiv: Hardware-States nutzen (kommen per Polling)
  if (['temp_reactive','load_reactive'].includes(fx)) {
    if (leds?.led_states?.length === N) {
      setLedDisplay(leds.led_states);
    }
    _ledStep++; return;
  }

  // Individuelle LEDs: direkt die gespeicherten Farben anzeigen
  if (leds?.individual_mode && leds?.individual_colors?.length === N) {
    setLedDisplay(leds.individual_colors.map(ic => ({
      r: Math.round((ic.r||0)*br), g: Math.round((ic.g||0)*br), b: Math.round((ic.b||0)*br)
    })));
    _ledStep++; return;
  }

  let L = Array.from({length:N}, ()=>({r:0,g:0,b:0}));

  if (fx === 'off') {}
  else if (fx === 'static') { L = L.map(()=>({...c})); }
  else if (fx === 'breathing') { const f=(Math.sin(step*0.04*spd)+1)/2; L=L.map(()=>({r:Math.round(c.r*f),g:Math.round(c.g*f),b:Math.round(c.b*f)})); }
  else if (fx === 'rainbow') { for(let i=0;i<N;i++) L[i]=_hsv(((step*2*spd)+(i*90))%360,1,1); }
  else if (fx === 'gradient') { for(let i=0;i<N;i++){const t=i/(N-1);const ph=Math.sin(step*0.03*spd)*0.3+0.7;L[i]={r:Math.round((c.r+(c2.r-c.r)*t)*ph),g:Math.round((c.g+(c2.g-c.g)*t)*ph),b:Math.round((c.b+(c2.b-c.b)*t)*ph)};} }
  else if (fx === 'candle') { for(let i=0;i<N;i++){const fl=0.6+Math.random()*0.4;L[i]={r:Math.round(255*fl),g:Math.round(120*fl),b:Math.round(20*fl*0.5)};} }
  else if (fx === 'lava') { const t=step*0.01*spd; for(let i=0;i<N;i++) L[i]=_hsv(Math.abs((Math.sin(t+i*1.2)*30+Math.sin(t*0.7+i*0.8)*20)%360),0.9,0.5+Math.sin(t+i)*0.3); }
  else if (fx === 'aurora') { const t=step*0.015*spd; const pal=[{r:0,g:255,b:100},{r:0,g:180,b:255},{r:80,g:0,b:255},{r:0,g:255,b:180}]; for(let i=0;i<N;i++){const idx=(Math.sin(t+i*0.8)+1)/2*(pal.length-1);const lo=Math.floor(idx),hi=Math.min(lo+1,pal.length-1),frac=idx-lo;const b2=0.4+Math.sin(t*1.3+i*2)*0.3;L[i]={r:Math.round((pal[lo].r+(pal[hi].r-pal[lo].r)*frac)*b2),g:Math.round((pal[lo].g+(pal[hi].g-pal[lo].g)*frac)*b2),b:Math.round((pal[lo].b+(pal[hi].b-pal[lo].b)*frac)*b2)};} }
  else if (fx === 'fire') { for(let i=0;i<N;i++){const h=120+Math.floor(Math.random()*136);L[i]={r:h,g:Math.max(0,h-100),b:Math.max(0,h-200)};} }
  else if (fx === 'ocean') { const t=step*0.02*spd; for(let i=0;i<N;i++){const w=Math.sin(t+i*1.5)*0.5+0.5;L[i]={r:0,g:Math.round(80*w),b:Math.round(180+75*w)};} }
  else if (fx === 'pulse') { const t=step*0.06*spd,pos=t%(N+2); for(let i=0;i<N;i++){const b2=Math.max(0,1-Math.abs(i-pos)*0.7);L[i]={r:Math.round(c.r*b2),g:Math.round(c.g*b2),b:Math.round(c.b*b2)};} }
  else if (fx === 'strobe') { const on=(step%Math.max(1,Math.floor(20/spd)))<Math.max(1,Math.floor(5/spd)); L=L.map(()=>on?{...c}:{r:0,g:0,b:0}); }
  else if (fx === 'police') { const ph=(Math.floor(step/Math.max(1,Math.floor(8/spd))))%4; if(ph===0){L[0]={r:255,g:0,b:0};L[1]={r:255,g:0,b:0};}else if(ph===2){L[2]={r:0,g:0,b:255};L[3]={r:0,g:0,b:255};} }
  else if (fx === 'disco') { if(step%Math.max(1,Math.floor(6/spd))===0) for(let i=0;i<N;i++) L[i]=_hsv(Math.random()*360,1,1); }
  else if (fx === 'chase') { const pos=Math.floor(step/Math.max(1,Math.floor(4/spd)))%N; for(let i=0;i<N;i++) L[i]=i===pos?{...c}:{r:0,g:0,b:0}; }
  else if (fx === 'sparkle') { for(let i=0;i<N;i++) L[i]=Math.random()<0.15*spd?{...c}:{r:Math.round(c.r*0.1),g:Math.round(c.g*0.1),b:Math.round(c.b*0.1)}; }
  else if (fx === 'firework') { const cy2=Math.max(1,Math.floor(60/spd)),phase=step%cy2; if(phase===0)L=L.map(()=>({r:255,g:255,b:255}));else if(phase<cy2*0.3){const h=_hsv(Math.random()*360,1,1);L=L.map(()=>({...h}));}else{const fade=Math.max(0,1-(phase-cy2*0.3)/(cy2*0.7));L=L.map(()=>({r:Math.round(c.r*fade),g:Math.round(c.g*fade),b:Math.round(c.b*fade)}));} }
  else if (fx === 'sunset') { const t=step*0.008*spd; const pal=[{r:255,g:60,b:0},{r:255,g:120,b:0},{r:255,g:80,b:50},{r:200,g:40,b:80}]; for(let i=0;i<N;i++){const idx=(Math.sin(t+i*0.5)+1)/2*(pal.length-1),lo=Math.floor(idx),hi=Math.min(lo+1,pal.length-1),frac=idx-lo;L[i]={r:Math.round(pal[lo].r+(pal[hi].r-pal[lo].r)*frac),g:Math.round(pal[lo].g+(pal[hi].g-pal[lo].g)*frac),b:Math.round(pal[lo].b+(pal[hi].b-pal[lo].b)*frac)};} }
  else if (fx === 'forest') { const t=step*0.01*spd; for(let i=0;i<N;i++){const g=Math.round(80+Math.sin(t+i*1.5)*40);L[i]={r:Math.round(g*0.1),g:g,b:Math.round(g*0.2)};} }
  else if (fx === 'neon') { const t=step*0.02*spd; const nc=[{r:255,g:0,b:255},{r:0,g:255,b:255},{r:255,g:0,b:100},{r:100,g:0,b:255}]; for(let i=0;i<N;i++){const ci=Math.floor((t+i*2)%nc.length),fl=0.7+Math.random()*0.3;L[i]={r:Math.round(nc[ci].r*fl),g:Math.round(nc[ci].g*fl),b:Math.round(nc[ci].b*fl)};} }
  else if (fx === 'warm_white') { L=L.map(()=>({r:255,g:180,b:100})); }
  else if (fx === 'night_light') { const v=0.05+Math.sin(step*0.01)*0.02; L=L.map(()=>({r:Math.round(255*v),g:Math.round(200*v),b:Math.round(120*v)})); }
  else { L=L.map(()=>({...c})); }

  setLedDisplay(L.map(l=>({r:Math.round(l.r*br),g:Math.round(l.g*br),b:Math.round(l.b*br)})));
  _ledStep++;
}

function _startLedEngine() { _ledLast = performance.now(); _ledRaf = requestAnimationFrame(_ledTick); }
function _stopLedEngine() { if (_ledRaf) cancelAnimationFrame(_ledRaf); }

export function getState() {
  return {
    get connected() { return connected; },
    get stats() { return stats; },
    get fan() { return fan; },
    get leds() { return leds; },
    get ledColors() { return ledDisplay; },
    setLedDisplay,
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
    async setFanCurve(points) { const r = await api.fan.curve(points); if (!r.error) fan = { ...fan, ...r }; },
    async setFanSettings(s) { const r = await api.fan.settings(s); if (!r.error) fan = { ...fan, ...r }; },

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
