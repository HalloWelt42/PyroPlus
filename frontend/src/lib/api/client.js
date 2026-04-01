/* PyroPlus — API Client v3.0.0 */

let _token = '';

async function fetchToken() {
  try {
    const res = await fetch('/api/token');
    const data = await res.json();
    _token = data.token || '';
    return _token;
  } catch (e) { console.error('[API] Token:', e); return ''; }
}

async function request(path, opts = {}) {
  try {
    const res = await fetch(`/api${path}`, {
      headers: { 'Content-Type': 'application/json', 'X-API-Token': _token, ...opts.headers },
      ...opts,
    });
    if (res.status === 401) {
      await fetchToken();
      const retry = await fetch(`/api${path}`, {
        headers: { 'Content-Type': 'application/json', 'X-API-Token': _token, ...opts.headers },
        ...opts,
      });
      return await retry.json();
    }
    return await res.json();
  } catch (e) { console.error('[API]', e); return { error: e.message }; }
}

const get = (p) => request(p);
const post = (p, b) => request(p, { method: 'POST', body: b ? JSON.stringify(b) : undefined });
const put = (p, b) => request(p, { method: 'PUT', body: JSON.stringify(b) });
const del = (p) => request(p, { method: 'DELETE' });

export const api = {
  fetchToken,
  get token() { return _token; },

  info: () => get('/info'),
  stats: () => get('/stats'),
  state: () => get('/state'),

  fan: {
    state: () => get('/fan'),
    mode: (m) => post(`/fan/mode/${m}`),
    profile: (p) => post(`/fan/profile/${p}`),
    manualSpeed: (s) => post('/fan/manual-speed', { speed: s }),
    settings: (s) => post('/fan/settings', s),
    curve: (points) => post('/fan/curve', { points }),
    speedForTemp: (t) => get(`/fan/speed-for-temp?temp=${t}`),
  },

  oled: {
    state: () => get('/oled'),
    widgetCatalog: () => get('/oled/widget-catalog'),
    mode: (m) => post(`/oled/mode/${m}`),
    brightness: (v) => post(`/oled/brightness/${v}`),
    rotation: (s) => post(`/oled/rotation/${s}`),
    screen: (i) => post(`/oled/screen/${i}`),
    addScreen: (data) => post('/oled/screens', data),
    updateScreen: (i, data) => put(`/oled/screens/${i}`, data),
    removeScreen: (i) => del(`/oled/screens/${i}`),
    reorderScreens: (order) => post('/oled/screens/reorder', order),
    preview: () => get('/oled/preview'),
    clockSettings: (s) => post('/oled/clock', s),
    pixelArts: () => get('/oled/pixel-arts'),
    getPixelArt: (id) => get(`/oled/pixel-arts/${id}`),
    savePixelArt: (data) => post('/oled/pixel-arts', data),
    deletePixelArt: (id) => del(`/oled/pixel-arts/${id}`),
  },

  leds: {
    state: () => get('/leds'),
    effects: () => get('/leds/effects'),
    effect: (n) => post(`/leds/effect/${n}`),
    color: (r, g, b) => post('/leds/color', { r, g, b }),
    color2: (r, g, b) => post('/leds/color2', { r, g, b }),
    brightness: (v) => post(`/leds/brightness/${v}`),
    speed: (v) => post(`/leds/speed/${v}`),
    individualMode: (on) => post(`/leds/individual-mode/${on}`),
    individualColor: (i, r, g, b) => post('/leds/individual', { index: i, color: { r, g, b } }),
  },

  quick: {
    ledsOff: () => post('/quick/leds-off'),
    ledsOn: () => post('/quick/leds-on'),
    oledOff: () => post('/quick/oled-off'),
    oledOn: () => post('/quick/oled-on'),
    fanAuto: () => post('/quick/fan-auto'),
    fanOff: () => post('/quick/fan-off'),
  },
};

export function createWebSocket(onMessage) {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${proto}//${location.host}/ws`;
  let ws = null, alive = true, timer = null;

  function connect() {
    if (!alive) return;
    try {
      ws = new WebSocket(url);
      ws.onmessage = (e) => { try { onMessage(JSON.parse(e.data)); } catch {} };
      ws.onclose = () => { if (alive) timer = setTimeout(connect, 3000); };
      ws.onerror = () => ws?.close();
    } catch { if (alive) timer = setTimeout(connect, 3000); }
  }
  connect();
  return { close() { alive = false; clearTimeout(timer); ws?.close(); } };
}
