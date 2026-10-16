/* API-Client: typisierte Aufrufe, Token, WebSocket mit Wiederverbindung. */

import type {
  Catalog, EffectCatalog, FanFineSettings, FanState, GeocodeHit, ImportResult, LedState, Ok,
  OledBundle, OledSettings, OledSettingsPatch, OledState, Profile, RenderRequest, RenderResponse,
  Rgb, Screen, SystemState, TemplateCatalog, WeatherLocation, WeatherLocationCreate,
  WeatherLocationState, WeatherSettings, Widget, WidgetPreset, WidgetRenderResponse, WsMessage,
} from './types';

export class ApiFehler extends Error {
  status: number;
  constructor(status: number, nachricht: string) {
    super(nachricht);
    this.status = status;
  }
}

let token = '';

async function holeToken(): Promise<string> {
  const antwort = await fetch('/api/token');
  const daten = (await antwort.json()) as { token?: string };
  token = daten.token ?? '';
  return token;
}

async function anfrage<T>(methode: string, pfad: string, body?: unknown, wiederholt = false): Promise<T> {
  const antwort = await fetch(`/api${pfad}`, {
    method: methode,
    headers: { 'Content-Type': 'application/json', 'X-API-Token': token },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (antwort.status === 401 && !wiederholt) {
    await holeToken();
    return anfrage<T>(methode, pfad, body, true);
  }
  const text = await antwort.text();
  const daten = text ? (JSON.parse(text) as unknown) : null;
  if (!antwort.ok) {
    const detail = (daten as { detail?: unknown; error?: unknown } | null);
    const grund = typeof detail?.detail === 'string' ? detail.detail
      : typeof detail?.error === 'string' ? detail.error
      : Array.isArray(detail?.detail) ? 'Eingabe ungültig' : `Fehler ${antwort.status}`;
    throw new ApiFehler(antwort.status, grund);
  }
  return daten as T;
}

const get = <T>(p: string) => anfrage<T>('GET', p);
const post = <T>(p: string, b?: unknown) => anfrage<T>('POST', p, b);
const put = <T>(p: string, b?: unknown) => anfrage<T>('PUT', p, b);
const patch = <T>(p: string, b?: unknown) => anfrage<T>('PATCH', p, b);
const del = <T>(p: string) => anfrage<T>('DELETE', p);

export const api = {
  holeToken,
  get token() { return token; },

  system: {
    info: () => get<{ app: string; version: string; voll: string }>('/info'),
    state: () => get<SystemState>('/state'),
  },

  fan: {
    state: () => get<FanState>('/fan'),
    mode: (m: string) => post<Ok & { mode: string }>(`/fan/mode/${m}`),
    profile: (p: string) => post<FanState>(`/fan/profile/${p}`),
    manualSpeed: (s: number) => post<Ok>('/fan/manual-speed', { speed: s }),
    settings: (s: FanFineSettings) => post<Ok & FanState>('/fan/settings', s),
    curve: (points: { temp: number; speed: number }[]) => post<Ok & FanState>('/fan/curve', { points }),
  },

  leds: {
    state: () => get<LedState>('/leds'),
    effects: () => get<EffectCatalog>('/leds/effects'),
    effect: (n: string) => post<Ok & { effect: string }>(`/leds/effect/${n}`),
    color: (c: Rgb) => post<Ok>('/leds/color', c),
    color2: (c: Rgb) => post<Ok>('/leds/color2', c),
    brightness: (v: number) => post<Ok>(`/leds/brightness/${v}`),
    speed: (v: number) => post<Ok>(`/leds/speed/${v}`),
    individualMode: (on: boolean) => post<Ok>(`/leds/individual-mode/${on}`),
    individualColor: (i: number, c: Rgb) => post<Ok>('/leds/individual', { index: i, color: c }),
  },

  quick: {
    ledsOff: () => post<Ok>('/quick/leds-off'),
    ledsOn: () => post<Ok & { effect: string }>('/quick/leds-on'),
    oledOff: () => post<Ok>('/quick/oled-off'),
    oledOn: () => post<Ok>('/quick/oled-on'),
    fanAuto: () => post<Ok>('/quick/fan-auto'),
    fanOff: () => post<Ok>('/quick/fan-off'),
  },

  simulate: {
    temp: (temp: number) => post<Ok>('/simulate/temp', { temp }),
    stop: () => post<Ok>('/simulate/temp', { temp: null }),
  },

  oled: {
    state: () => get<OledState>('/oled'),
    patchSettings: (p: OledSettingsPatch) => patch<OledSettings>('/oled/settings', p),
    catalog: () => get<Catalog>('/oled/catalog'),
    render: (req: RenderRequest) => post<RenderResponse>('/oled/render', req),
    renderWidget: (widget: Widget, simulate: Record<string, number> = {}) => post<WidgetRenderResponse>('/oled/render/widget', { widget, simulate }),
    screens: () => get<Screen[]>('/oled/screens'),
    replaceScreens: (screens: Screen[]) => put<Screen[]>('/oled/screens', screens),
    addScreen: (screen: Partial<Screen>) => post<Screen>('/oled/screens', screen),
    updateScreen: (id: string, screen: Screen) => put<Screen>(`/oled/screens/${id}`, screen),
    deleteScreen: (id: string) => del<Ok>(`/oled/screens/${id}`),
    duplicateScreen: (id: string) => post<Screen>(`/oled/screens/${id}/duplicate`),
    activateScreen: (id: string) => post<OledSettings>(`/oled/screens/${id}/activate`),
    reorder: (ids: string[]) => post<Screen[]>('/oled/screens/order', { ids }),
    presets: () => get<WidgetPreset[]>('/oled/presets'),
    addPreset: (p: Omit<WidgetPreset, 'id' | 'created'>) => post<WidgetPreset>('/oled/presets', p),
    updatePreset: (id: string, p: WidgetPreset) => put<WidgetPreset>(`/oled/presets/${id}`, p),
    deletePreset: (id: string) => del<Ok>(`/oled/presets/${id}`),
    profiles: () => get<Profile[]>('/oled/profiles'),
    saveProfile: (name: string) => post<Profile>('/oled/profiles', { name }),
    applyProfile: (id: string) => post<OledSettings>(`/oled/profiles/${id}/apply`),
    deleteProfile: (id: string) => del<Ok>(`/oled/profiles/${id}`),
    weatherLocations: () => get<WeatherLocationState[]>('/oled/weather/locations'),
    addLocation: (l: WeatherLocationCreate) => post<WeatherLocation>('/oled/weather/locations', l),
    deleteLocation: (id: string) => del<Ok>(`/oled/weather/locations/${id}`),
    defaultLocation: (id: string) => post<WeatherSettings>(`/oled/weather/locations/${id}/default`),
    refreshWeather: (id?: string) => post<Ok>(`/oled/weather/refresh${id ? `?locationId=${encodeURIComponent(id)}` : ''}`),
    searchLocation: (q: string) => get<GeocodeHit[]>(`/oled/weather/search?q=${encodeURIComponent(q)}`),
    templates: () => get<TemplateCatalog>('/oled/templates'),
    addTemplateScreen: (id: string) => post<Screen>(`/oled/templates/screens/${id}`),
    templateWidget: (id: string) => get<Widget>(`/oled/templates/widgets/${id}`),
    exportBundle: () => get<OledBundle>('/oled/export'),
    importBundle: (b: OledBundle, replace: boolean) => post<ImportResult>(`/oled/import?replace=${replace}`, b),
    importLegacy: (daten: unknown, replace: boolean) => post<ImportResult>(`/oled/import-legacy?replace=${replace}`, daten),
  },
};

/* WebSocket zum Backend: gleicher Ursprung, Pfad /ws (im Entwicklungsbetrieb durch Vite weitergeleitet). */
export function verbindeLive(
  beiNachricht: (m: WsMessage) => void,
  beiZustand: (verbunden: boolean) => void,
): { schliessen: () => void } {
  const url = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws`;
  let ws: WebSocket | null = null;
  let aktiv = true;
  let versuche = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;

  function verbinden(): void {
    if (!aktiv) return;
    try {
      ws = new WebSocket(url);
      ws.onopen = () => { versuche = 0; beiZustand(true); };
      ws.onmessage = (e) => {
        try { beiNachricht(JSON.parse(e.data as string) as WsMessage); } catch { /* unlesbar, ignorieren */ }
      };
      ws.onclose = () => {
        beiZustand(false);
        if (!aktiv) return;
        versuche += 1;
        timer = setTimeout(verbinden, Math.min(1000 * versuche, 5000));
      };
      ws.onerror = () => ws?.close();
    } catch {
      if (aktiv) timer = setTimeout(verbinden, 2000);
    }
  }
  verbinden();
  return {
    schliessen() {
      aktiv = false;
      if (timer) clearTimeout(timer);
      ws?.close();
    },
  };
}
