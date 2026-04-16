/**
 * PyroPlus — Datenkatalog + Display-Modi
 * Definiert alle verfuegbaren Datenquellen und Darstellungsarten.
 */

/* ═══ TABS / KATEGORIEN ═══ */
export const TABS = [
  { id: 'cpu',     label: 'CPU' },
  { id: 'ram',     label: 'RAM' },
  { id: 'disk',    label: 'Festplatten' },
  { id: 'net',     label: 'Netzwerk' },
  { id: 'fan',     label: 'Luefter' },
  { id: 'zeit',    label: 'Zeiten' },
  { id: 'wetter',  label: 'Wetter' },
  { id: 'text',    label: 'Texte' },
  { id: 'layout',  label: 'Layout' },
];

/* ═══ DATENQUELLEN ═══
 * Jeder Eintrag: { id, tab, label, unit, type, getValue(stats, weather, opts) }
 * type: 'number' | 'percent' | 'string' | 'time' | 'shape'
 */
export const DATA_SOURCES = [
  // ─── CPU ───
  { id: 'cpu.temp',      tab: 'cpu', label: 'Temperatur',   unit: '°C',  type: 'number',
    getValue: (s) => s?.cpu?.temp?.toFixed(1) ?? '0' },
  { id: 'cpu.percent',   tab: 'cpu', label: 'Auslastung',   unit: '%',   type: 'percent',
    getValue: (s) => Math.round(s?.cpu?.percent ?? 0),
    getRaw: (s) => s?.cpu?.percent ?? 0 },
  { id: 'cpu.cores',     tab: 'cpu', label: 'Kerne',        unit: '',    type: 'number',
    getValue: (s) => s?.cpu?.cores ?? 4 },
  { id: 'cpu.temp_min',  tab: 'cpu', label: 'Temp Min',     unit: '°C',  type: 'number',
    getValue: (s) => s?.cpu?.temp_min?.toFixed(1) ?? '0' },
  { id: 'cpu.temp_max',  tab: 'cpu', label: 'Temp Max',     unit: '°C',  type: 'number',
    getValue: (s) => s?.cpu?.temp_max?.toFixed(1) ?? '0' },
  // ─── RAM ───
  { id: 'ram.used',      tab: 'ram', label: 'Benutzt',      unit: 'GB',  type: 'number',
    getValue: (s) => s?.ram?.used_gb?.toFixed(1) ?? '0' },
  { id: 'ram.total',     tab: 'ram', label: 'Gesamt',       unit: 'GB',  type: 'number',
    getValue: (s) => s?.ram?.total_gb?.toFixed(1) ?? '0' },
  { id: 'ram.available', tab: 'ram', label: 'Verfuegbar',   unit: 'GB',  type: 'number',
    getValue: (s) => s?.ram?.available_gb?.toFixed(1) ?? '0' },
  { id: 'ram.percent',   tab: 'ram', label: 'Auslastung',   unit: '%',   type: 'percent',
    getValue: (s) => Math.round(s?.ram?.percent ?? 0),
    getRaw: (s) => s?.ram?.percent ?? 0 },
  // ─── Disk (dynamisch pro Mount) ───
  { id: 'disk.label',    tab: 'disk', label: 'Name',        unit: '',    type: 'string', perDisk: true,
    getValue: (s, w, o) => s?.disks?.[o?.diskIdx??0]?.label ?? '?' },
  { id: 'disk.mount',    tab: 'disk', label: 'Mountpoint',  unit: '',    type: 'string', perDisk: true,
    getValue: (s, w, o) => s?.disks?.[o?.diskIdx??0]?.mount ?? '?' },
  { id: 'disk.used',     tab: 'disk', label: 'Benutzt',     unit: 'GB',  type: 'number', perDisk: true,
    getValue: (s, w, o) => s?.disks?.[o?.diskIdx??0]?.used_gb?.toFixed(1) ?? '0' },
  { id: 'disk.total',    tab: 'disk', label: 'Gesamt',      unit: 'GB',  type: 'number', perDisk: true,
    getValue: (s, w, o) => s?.disks?.[o?.diskIdx??0]?.total_gb?.toFixed(1) ?? '0' },
  { id: 'disk.percent',  tab: 'disk', label: 'Auslastung',  unit: '%',   type: 'percent', perDisk: true,
    getValue: (s, w, o) => Math.round(s?.disks?.[o?.diskIdx??0]?.percent ?? 0),
    getRaw: (s, w, o) => s?.disks?.[o?.diskIdx??0]?.percent ?? 0 },
  { id: 'disk.model',    tab: 'disk', label: 'Modell',      unit: '',    type: 'string', perDisk: true,
    getValue: (s, w, o) => s?.disks?.[o?.diskIdx??0]?.model ?? '' },
  // ─── Netzwerk ───
  { id: 'net.ip',        tab: 'net', label: 'IP-Adresse',   unit: '',    type: 'string',
    getValue: (s) => s?.network?.ip ?? '0.0.0.0' },
  { id: 'net.interface', tab: 'net', label: 'Interface',    unit: '',    type: 'string',
    getValue: (s) => s?.network?.interface ?? '?' },
  { id: 'net.rx',        tab: 'net', label: 'Download',     unit: '',    type: 'number',
    getValue: (s) => { const b = s?.network?.rx_bytes_sec ?? 0; return b > 1048576 ? (b/1048576).toFixed(1)+' MB/s' : b > 1024 ? Math.round(b/1024)+' KB/s' : b+' B/s'; } },
  { id: 'net.tx',        tab: 'net', label: 'Upload',       unit: '',    type: 'number',
    getValue: (s) => { const b = s?.network?.tx_bytes_sec ?? 0; return b > 1048576 ? (b/1048576).toFixed(1)+' MB/s' : b > 1024 ? Math.round(b/1024)+' KB/s' : b+' B/s'; } },
  // ─── Luefter ───
  { id: 'fan.rpm',       tab: 'fan', label: 'Drehzahl',     unit: 'RPM', type: 'number',
    getValue: (s) => s?.fan?.rpm ?? 0 },
  { id: 'fan.duty',      tab: 'fan', label: 'PWM Duty',     unit: '%',   type: 'percent',
    getValue: (s) => Math.round(s?.fan?.current_duty ?? 0),
    getRaw: (s) => s?.fan?.current_duty ?? 0 },
  { id: 'fan.level',     tab: 'fan', label: 'Stufe',        unit: '',    type: 'string',
    getValue: (s) => s?.fan?.level_name ?? '?' },
  { id: 'fan.case',      tab: 'fan', label: 'Gehaeusel.',   unit: '',    type: 'string',
    getValue: (s) => s?.fan?.case_on ? 'An' : 'Aus' },
  // ─── Zeiten ───
  { id: 'zeit.uhr',      tab: 'zeit', label: 'Uhrzeit',     unit: '',    type: 'time',
    getValue: () => { const d = new Date(); return String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0'); } },
  { id: 'zeit.uhr_s',    tab: 'zeit', label: 'Uhr + Sek',   unit: '',    type: 'time',
    getValue: () => { const d = new Date(); return String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0') + ':' + String(d.getSeconds()).padStart(2,'0'); } },
  { id: 'zeit.datum',    tab: 'zeit', label: 'Datum',        unit: '',    type: 'time',
    getValue: () => new Date().toLocaleDateString('de-DE') },
  { id: 'zeit.tag',      tab: 'zeit', label: 'Wochentag',    unit: '',    type: 'time',
    getValue: () => ['So','Mo','Di','Mi','Do','Fr','Sa'][new Date().getDay()] },
  { id: 'zeit.uptime',   tab: 'zeit', label: 'Uptime',       unit: '',    type: 'string',
    getValue: (s) => s?.uptime?.formatted ?? '0:00' },
  // ─── Wetter ───
  { id: 'wetter.temp',   tab: 'wetter', label: 'Temperatur', unit: '°C',  type: 'number',
    getValue: (s, w) => w?.temperature ?? '--' },
  { id: 'wetter.feuchte',tab: 'wetter', label: 'Feuchtigkeit', unit: '%', type: 'number',
    getValue: (s, w) => w?.humidity ?? '--' },
  { id: 'wetter.wind',   tab: 'wetter', label: 'Wind',       unit: 'km/h', type: 'number',
    getValue: (s, w) => w?.wind_speed ?? '--' },
  { id: 'wetter.druck',  tab: 'wetter', label: 'Luftdruck',  unit: 'hPa', type: 'number',
    getValue: (s, w) => w?.pressure ?? '--' },
  { id: 'wetter.zustand',tab: 'wetter', label: 'Zustand',    unit: '',    type: 'string',
    getValue: (s, w) => w?.condition_text ?? '--' },
  { id: 'wetter.ort',    tab: 'wetter', label: 'Ort',         unit: '',    type: 'string',
    getValue: (s, w) => w?.location ?? '--' },
  { id: 'wetter.sunrise',tab: 'wetter', label: 'Sonnenaufgang', unit: '', type: 'time',
    getValue: (s, w) => w?.sunrise ?? '--' },
  { id: 'wetter.sunset', tab: 'wetter', label: 'Sonnenuntergang', unit: '', type: 'time',
    getValue: (s, w) => w?.sunset ?? '--' },
  // ─── Text (frei) ───
  { id: 'text.frei',     tab: 'text', label: 'Freier Text',  unit: '',    type: 'string',
    getValue: (s, w, o) => o?.text ?? 'Text' },
  { id: 'text.laufschrift', tab: 'text', label: 'Laufschrift', unit: '', type: 'string',
    getValue: (s, w, o) => o?.text ?? 'Laufschrift' },
];

/* ═══ DISPLAY-MODI ═══
 * Jeder Modus: { id, label, forTypes[], minW, minH }
 * forTypes: welche source.type-Werte diesen Modus unterstuetzen
 */
export const DISPLAY_MODES = [
  { id: 'zahl',          label: 'Zahl',              forTypes: ['number', 'percent', 'string', 'time'] },
  { id: 'zahl_gross',    label: 'Zahl Gross',        forTypes: ['number', 'percent', 'time'] },
  { id: 'zahl_xl',       label: 'Zahl XL',           forTypes: ['number', 'percent', 'time'] },
  { id: 'balken',        label: 'Balken',             forTypes: ['percent'] },
  { id: 'balken_label',  label: 'Balken + Wert',     forTypes: ['percent'] },
  { id: 'gauge',         label: 'Gauge',              forTypes: ['percent'] },
  { id: 'sparkline',     label: 'Verlauf',            forTypes: ['number', 'percent'] },
  { id: 'text',          label: 'Text',               forTypes: ['string', 'time'] },
  { id: 'laufschrift',   label: 'Laufschrift',        forTypes: ['string'] },
  // ─── Layout-Elemente (keine Datenquelle) ───
  { id: 'linie_h',       label: 'Linie horizontal',   forTypes: ['shape'] },
  { id: 'linie_v',       label: 'Linie vertikal',     forTypes: ['shape'] },
  { id: 'rahmen',        label: 'Rahmen',              forTypes: ['shape'] },
  { id: 'block',         label: 'Block (gefuellt)',    forTypes: ['shape'] },
  { id: 'section',       label: 'Trennlinie',         forTypes: ['shape'] },
];

/* Layout-Quellen (brauchen keine echte Datenquelle) */
export const LAYOUT_SOURCES = [
  { id: 'layout.linie_h', tab: 'layout', label: 'Linie horizontal', type: 'shape', defaultDisplay: 'linie_h' },
  { id: 'layout.linie_v', tab: 'layout', label: 'Linie vertikal',   type: 'shape', defaultDisplay: 'linie_v' },
  { id: 'layout.rahmen',  tab: 'layout', label: 'Rahmen',           type: 'shape', defaultDisplay: 'rahmen' },
  { id: 'layout.block',   tab: 'layout', label: 'Block',            type: 'shape', defaultDisplay: 'block' },
  { id: 'layout.section', tab: 'layout', label: 'Trennlinie',       type: 'shape', defaultDisplay: 'section' },
];

/* Alle Quellen kombiniert */
export const ALL_SOURCES = [...DATA_SOURCES, ...LAYOUT_SOURCES];

/* Hilfsfunktionen */
export function getSource(id) {
  return ALL_SOURCES.find(s => s.id === id);
}

export function getModesForType(type) {
  return DISPLAY_MODES.filter(m => m.forTypes.includes(type));
}

export function getSourcesForTab(tab) {
  return ALL_SOURCES.filter(s => s.tab === tab);
}

/* Histogramm-Quellen (fuer Sparklines) */
export const HISTORY_KEYS = {
  'cpu.percent': 'cpu',
  'cpu.temp':    'temp',
  'ram.percent': 'ram',
  'fan.rpm':     'fan_speed',
  'net.rx':      'net_rx',
  'net.tx':      'net_tx',
};

/* Default-Optionen pro Display-Modus */
export function defaultOpts(display) {
  switch (display) {
    case 'zahl':         return { scaleX: 1, scaleY: 1, prefix: '', suffix: '' };
    case 'zahl_gross':   return { scaleX: 2, scaleY: 2, prefix: '', suffix: '' };
    case 'zahl_xl':      return { scaleX: 3, scaleY: 3, prefix: '', suffix: '' };
    case 'balken':       return { width: 60, height: 6 };
    case 'balken_label': return { width: 50, height: 6, scaleX: 1, scaleY: 1, prefix: '', suffix: '%' };
    case 'gauge':        return { radius: 12 };
    case 'sparkline':    return { width: 60, height: 20 };
    case 'text':         return { scaleX: 1, scaleY: 1, text: '' };
    case 'laufschrift':  return { scaleX: 1, scaleY: 1, text: 'Hallo Welt!' };
    case 'linie_h':      return { width: 60 };
    case 'linie_v':      return { height: 20 };
    case 'rahmen':       return { width: 40, height: 20 };
    case 'block':        return { width: 40, height: 20 };
    case 'section':      return { width: 60, text: 'CPU' };
    default:             return {};
  }
}

/* Widget-Instanz erstellen */
export function createWidget(sourceId, display, x = 4, y = 4) {
  const src = getSource(sourceId);
  const opts = defaultOpts(display);
  return {
    id: Date.now() + Math.random(),
    source: sourceId,
    display,
    x, y,
    name: src?.label ?? sourceId,
    opts: { ...opts, invert: false, border: false, align: 'left', boxW: 0 },
  };
}
