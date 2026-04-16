/**
 * PyroPlus — Datenkatalog + Display-Modi
 * Alle verfuegbaren Datenquellen, Darstellungsarten und Defaults.
 */

/* ═══ TABS ═══ */
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

/* ═══ DATENQUELLEN ═══ */
const _fmt = (v, d=1) => v != null ? Number(v).toFixed(d) : '0';
const _pct = (v) => Math.round(v ?? 0);
const _bytes = (b) => { b = b ?? 0; return b > 1048576 ? (b/1048576).toFixed(1)+' MB/s' : b > 1024 ? Math.round(b/1024)+' KB/s' : b+' B/s'; };
const _bytesTotal = (b) => { b = b ?? 0; return b > 1073741824 ? (b/1073741824).toFixed(1)+' GB' : b > 1048576 ? Math.round(b/1048576)+' MB' : Math.round(b/1024)+' KB'; };

export const DATA_SOURCES = [
  // ═══ CPU ═══
  { id: 'cpu.temp',       tab: 'cpu', label: 'Temperatur',       unit: '°C',  type: 'number',
    getValue: (s) => _fmt(s?.cpu?.temp), getRaw: (s) => s?.cpu?.temp ?? 0 },
  { id: 'cpu.percent',    tab: 'cpu', label: 'Auslastung',       unit: '%',   type: 'percent',
    getValue: (s) => _pct(s?.cpu?.percent), getRaw: (s) => s?.cpu?.percent ?? 0 },
  { id: 'cpu.cores',      tab: 'cpu', label: 'Kerne',            unit: '',    type: 'number',
    getValue: (s) => s?.cpu?.cores ?? 4 },
  { id: 'cpu.temp_min',   tab: 'cpu', label: 'Temp Min',         unit: '°C',  type: 'number',
    getValue: (s) => _fmt(s?.cpu?.temp_min) },
  { id: 'cpu.temp_max',   tab: 'cpu', label: 'Temp Max',         unit: '°C',  type: 'number',
    getValue: (s) => _fmt(s?.cpu?.temp_max) },
  { id: 'cpu.temp_range', tab: 'cpu', label: 'Temp Bereich',     unit: '°C',  type: 'string',
    getValue: (s) => `${_fmt(s?.cpu?.temp_min)}-${_fmt(s?.cpu?.temp_max)}` },
  { id: 'cpu.temp_pct',   tab: 'cpu', label: 'Temp Auslastung',  unit: '%',   type: 'percent',
    getValue: (s) => _pct(Math.min(100, (s?.cpu?.temp ?? 0) / 85 * 100)),
    getRaw: (s) => Math.min(100, (s?.cpu?.temp ?? 0) / 85 * 100) },
  { id: 'cpu.load',       tab: 'cpu', label: 'CPU + Temp',       unit: '',    type: 'string',
    getValue: (s) => `${_pct(s?.cpu?.percent)}% ${_fmt(s?.cpu?.temp)}C` },

  // ═══ RAM ═══
  { id: 'ram.used',       tab: 'ram', label: 'Benutzt',          unit: 'GB',  type: 'number',
    getValue: (s) => _fmt(s?.ram?.used_gb) },
  { id: 'ram.total',      tab: 'ram', label: 'Gesamt',           unit: 'GB',  type: 'number',
    getValue: (s) => _fmt(s?.ram?.total_gb) },
  { id: 'ram.available',  tab: 'ram', label: 'Verfuegbar',       unit: 'GB',  type: 'number',
    getValue: (s) => _fmt(s?.ram?.available_gb) },
  { id: 'ram.percent',    tab: 'ram', label: 'Auslastung',       unit: '%',   type: 'percent',
    getValue: (s) => _pct(s?.ram?.percent), getRaw: (s) => s?.ram?.percent ?? 0 },
  { id: 'ram.ratio',      tab: 'ram', label: 'Benutzt/Gesamt',   unit: 'GB',  type: 'string',
    getValue: (s) => `${_fmt(s?.ram?.used_gb)}/${_fmt(s?.ram?.total_gb)}` },
  { id: 'ram.free_pct',   tab: 'ram', label: 'Frei',             unit: '%',   type: 'percent',
    getValue: (s) => _pct(100 - (s?.ram?.percent ?? 0)),
    getRaw: (s) => 100 - (s?.ram?.percent ?? 0) },

  // ═══ DISK (pro Mount) ═══
  { id: 'disk.label',     tab: 'disk', label: 'Name',            unit: '',    type: 'string', perDisk: true,
    getValue: (s, w, o) => s?.disks?.[o?.diskIdx??0]?.label ?? '?' },
  { id: 'disk.mount',     tab: 'disk', label: 'Mountpoint',      unit: '',    type: 'string', perDisk: true,
    getValue: (s, w, o) => s?.disks?.[o?.diskIdx??0]?.mount ?? '?' },
  { id: 'disk.used',      tab: 'disk', label: 'Benutzt',         unit: 'GB',  type: 'number', perDisk: true,
    getValue: (s, w, o) => _fmt(s?.disks?.[o?.diskIdx??0]?.used_gb) },
  { id: 'disk.total',     tab: 'disk', label: 'Gesamt',          unit: 'GB',  type: 'number', perDisk: true,
    getValue: (s, w, o) => _fmt(s?.disks?.[o?.diskIdx??0]?.total_gb) },
  { id: 'disk.available', tab: 'disk', label: 'Verfuegbar',      unit: 'GB',  type: 'number', perDisk: true,
    getValue: (s, w, o) => _fmt(s?.disks?.[o?.diskIdx??0]?.available_gb) },
  { id: 'disk.percent',   tab: 'disk', label: 'Auslastung',      unit: '%',   type: 'percent', perDisk: true,
    getValue: (s, w, o) => _pct(s?.disks?.[o?.diskIdx??0]?.percent),
    getRaw: (s, w, o) => s?.disks?.[o?.diskIdx??0]?.percent ?? 0 },
  { id: 'disk.ratio',     tab: 'disk', label: 'Benutzt/Gesamt',  unit: 'GB',  type: 'string', perDisk: true,
    getValue: (s, w, o) => `${_fmt(s?.disks?.[o?.diskIdx??0]?.used_gb)}/${_fmt(s?.disks?.[o?.diskIdx??0]?.total_gb)}` },
  { id: 'disk.free_pct',  tab: 'disk', label: 'Frei',            unit: '%',   type: 'percent', perDisk: true,
    getValue: (s, w, o) => _pct(100 - (s?.disks?.[o?.diskIdx??0]?.percent ?? 0)),
    getRaw: (s, w, o) => 100 - (s?.disks?.[o?.diskIdx??0]?.percent ?? 0) },
  { id: 'disk.model',     tab: 'disk', label: 'Modell',          unit: '',    type: 'string', perDisk: true,
    getValue: (s, w, o) => s?.disks?.[o?.diskIdx??0]?.model ?? '' },
  { id: 'disk.fstype',    tab: 'disk', label: 'Dateisystem',     unit: '',    type: 'string', perDisk: true,
    getValue: (s, w, o) => s?.disks?.[o?.diskIdx??0]?.fstype ?? '' },

  // ═══ NETZWERK ═══
  { id: 'net.ip',         tab: 'net', label: 'IP-Adresse',       unit: '',    type: 'string',
    getValue: (s) => s?.network?.ip ?? '0.0.0.0' },
  { id: 'net.interface',  tab: 'net', label: 'Interface',        unit: '',    type: 'string',
    getValue: (s) => s?.network?.interface ?? '?' },
  { id: 'net.rx',         tab: 'net', label: 'Download',         unit: '',    type: 'number',
    getValue: (s) => _bytes(s?.network?.rx_bytes_sec) },
  { id: 'net.tx',         tab: 'net', label: 'Upload',           unit: '',    type: 'number',
    getValue: (s) => _bytes(s?.network?.tx_bytes_sec) },
  { id: 'net.rx_raw',     tab: 'net', label: 'Download Bytes',   unit: 'B/s', type: 'number',
    getValue: (s) => s?.network?.rx_bytes_sec ?? 0 },
  { id: 'net.tx_raw',     tab: 'net', label: 'Upload Bytes',     unit: 'B/s', type: 'number',
    getValue: (s) => s?.network?.tx_bytes_sec ?? 0 },
  { id: 'net.traffic',    tab: 'net', label: 'DL/UL kombiniert', unit: '',    type: 'string',
    getValue: (s) => `${_bytes(s?.network?.rx_bytes_sec)} ${_bytes(s?.network?.tx_bytes_sec)}` },
  { id: 'net.hostname',   tab: 'net', label: 'Hostname',         unit: '',    type: 'string',
    getValue: () => 'PyroPlus' },

  // ═══ LUEFTER ═══
  { id: 'fan.rpm',        tab: 'fan', label: 'Drehzahl',         unit: 'RPM', type: 'number',
    getValue: (s) => s?.fan?.rpm ?? 0 },
  { id: 'fan.duty',       tab: 'fan', label: 'PWM Duty',         unit: '%',   type: 'percent',
    getValue: (s) => _pct(s?.fan?.current_duty),
    getRaw: (s) => s?.fan?.current_duty ?? 0 },
  { id: 'fan.level',      tab: 'fan', label: 'Stufe',            unit: '',    type: 'string',
    getValue: (s) => s?.fan?.level_name ?? '?' },
  { id: 'fan.case',       tab: 'fan', label: 'Gehaeuseluefter',  unit: '',    type: 'string',
    getValue: (s) => s?.fan?.case_on ? 'An' : 'Aus' },
  { id: 'fan.mode',       tab: 'fan', label: 'Modus',            unit: '',    type: 'string',
    getValue: (s) => s?.fan?.mode ?? '?' },
  { id: 'fan.rpm_pct',    tab: 'fan', label: 'Drehzahl %',       unit: '%',   type: 'percent',
    getValue: (s) => _pct(Math.min(100, (s?.fan?.rpm ?? 0) / 4000 * 100)),
    getRaw: (s) => Math.min(100, (s?.fan?.rpm ?? 0) / 4000 * 100) },

  // ═══ ZEITEN ═══
  { id: 'zeit.uhr',       tab: 'zeit', label: 'Uhrzeit HH:MM',   unit: '',  type: 'time',
    getValue: () => { const d=new Date(); return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`; } },
  { id: 'zeit.uhr_s',     tab: 'zeit', label: 'Uhr + Sekunden',   unit: '',  type: 'time',
    getValue: () => { const d=new Date(); return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`; } },
  { id: 'zeit.uhr_blink', tab: 'zeit', label: 'Uhr blinkend',    unit: '',  type: 'time',
    getValue: () => { const d=new Date(); const c = d.getSeconds()%2===0?':':' '; return `${String(d.getHours()).padStart(2,'0')}${c}${String(d.getMinutes()).padStart(2,'0')}`; } },
  { id: 'zeit.stunde',    tab: 'zeit', label: 'Stunde',           unit: 'h',  type: 'number',
    getValue: () => new Date().getHours() },
  { id: 'zeit.minute',    tab: 'zeit', label: 'Minute',           unit: 'm',  type: 'number',
    getValue: () => new Date().getMinutes() },
  { id: 'zeit.sekunde',   tab: 'zeit', label: 'Sekunde',          unit: 's',  type: 'number',
    getValue: () => new Date().getSeconds() },
  { id: 'zeit.datum',     tab: 'zeit', label: 'Datum TT.MM.JJJJ', unit: '',  type: 'time',
    getValue: () => new Date().toLocaleDateString('de-DE') },
  { id: 'zeit.datum_kurz',tab: 'zeit', label: 'Datum TT.MM.',    unit: '',    type: 'time',
    getValue: () => { const d=new Date(); return `${String(d.getDate()).padStart(2,'0')}.${String(d.getMonth()+1).padStart(2,'0')}.`; } },
  { id: 'zeit.jahr',      tab: 'zeit', label: 'Jahr',             unit: '',    type: 'number',
    getValue: () => new Date().getFullYear() },
  { id: 'zeit.tag',       tab: 'zeit', label: 'Wochentag kurz',   unit: '',    type: 'time',
    getValue: () => ['So','Mo','Di','Mi','Do','Fr','Sa'][new Date().getDay()] },
  { id: 'zeit.tag_lang',  tab: 'zeit', label: 'Wochentag lang',   unit: '',    type: 'time',
    getValue: () => ['Sonntag','Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag'][new Date().getDay()] },
  { id: 'zeit.tag_datum', tab: 'zeit', label: 'Tag + Datum',      unit: '',    type: 'time',
    getValue: () => { const d=new Date(); return `${['So','Mo','Di','Mi','Do','Fr','Sa'][d.getDay()]} ${d.toLocaleDateString('de-DE')}`; } },
  { id: 'zeit.uptime',    tab: 'zeit', label: 'Uptime',           unit: '',    type: 'string',
    getValue: (s) => s?.uptime?.formatted ?? '0:00' },
  { id: 'zeit.uptime_s',  tab: 'zeit', label: 'Uptime Sekunden',  unit: 's',   type: 'number',
    getValue: (s) => s?.uptime?.seconds ?? 0 },
  { id: 'zeit.unix',      tab: 'zeit', label: 'Unix Timestamp',   unit: '',    type: 'number',
    getValue: () => Math.floor(Date.now()/1000) },
  { id: 'zeit.iso',       tab: 'zeit', label: 'ISO Datum',        unit: '',    type: 'string',
    getValue: () => new Date().toISOString().slice(0,19) },

  // ═══ WETTER: Aktuell ═══
  { id: 'wetter.temp',       tab: 'wetter', label: 'Temperatur',        unit: '°C',   type: 'number',
    getValue: (s, w) => _fmt(w?.temperature_2m, 1) },
  { id: 'wetter.gefuehlt',   tab: 'wetter', label: 'Gefühlt',           unit: '°C',   type: 'number',
    getValue: (s, w) => _fmt(w?.apparent_temperature, 1) },
  { id: 'wetter.feuchte',    tab: 'wetter', label: 'Feuchtigkeit',      unit: '%',    type: 'percent',
    getValue: (s, w) => _pct(w?.relative_humidity_2m),
    getRaw: (s, w) => w?.relative_humidity_2m ?? 0 },
  { id: 'wetter.wind',       tab: 'wetter', label: 'Wind',              unit: 'km/h', type: 'number',
    getValue: (s, w) => _fmt(w?.wind_speed_10m, 0) },
  { id: 'wetter.windricht',  tab: 'wetter', label: 'Windrichtung',      unit: '°',    type: 'number',
    getValue: (s, w) => w?.wind_direction_10m ?? '--' },
  { id: 'wetter.boeen',      tab: 'wetter', label: 'Böen',              unit: 'km/h', type: 'number',
    getValue: (s, w) => _fmt(w?.wind_gusts_10m, 0) },
  { id: 'wetter.wolken',     tab: 'wetter', label: 'Bewölkung',         unit: '%',    type: 'percent',
    getValue: (s, w) => _pct(w?.cloud_cover),
    getRaw: (s, w) => w?.cloud_cover ?? 0 },
  { id: 'wetter.druck',      tab: 'wetter', label: 'Luftdruck',         unit: 'hPa',  type: 'number',
    getValue: (s, w) => _fmt(w?.surface_pressure, 0) },
  { id: 'wetter.druck_msl',  tab: 'wetter', label: 'Druck (Meer)',      unit: 'hPa',  type: 'number',
    getValue: (s, w) => _fmt(w?.pressure_msl, 0) },
  { id: 'wetter.niederschlag', tab: 'wetter', label: 'Niederschlag',    unit: 'mm',   type: 'number',
    getValue: (s, w) => _fmt(w?.precipitation, 1) },
  { id: 'wetter.zustand',    tab: 'wetter', label: 'Zustand',           unit: '',     type: 'string',
    getValue: (s, w) => w?.condition_text ?? '--' },
  { id: 'wetter.tag_nacht',  tab: 'wetter', label: 'Tag/Nacht',         unit: '',     type: 'string',
    getValue: (s, w) => w?.is_day ? 'Tag' : 'Nacht' },
  { id: 'wetter.ort',        tab: 'wetter', label: 'Ort',               unit: '',     type: 'string',
    getValue: (s, w) => w?.location ?? '--' },
  { id: 'wetter.sunrise',    tab: 'wetter', label: 'Sonnenaufgang',     unit: '',     type: 'time',
    getValue: (s, w) => w?.sunrise ?? '--' },
  { id: 'wetter.sunset',     tab: 'wetter', label: 'Sonnenuntergang',   unit: '',     type: 'time',
    getValue: (s, w) => w?.sunset ?? '--' },
  { id: 'wetter.kombi',      tab: 'wetter', label: 'Temp + Zustand',    unit: '',     type: 'string',
    getValue: (s, w) => `${_fmt(w?.temperature_2m,0)}° ${w?.condition_text ?? ''}` },
  { id: 'wetter.wind_kombi', tab: 'wetter', label: 'Wind + Böen',       unit: '',     type: 'string',
    getValue: (s, w) => `${_fmt(w?.wind_speed_10m,0)} (${_fmt(w?.wind_gusts_10m,0)}) km/h` },

  // ═══ TEXTE ═══
  { id: 'text.frei',       tab: 'text', label: 'Freier Text',     unit: '',  type: 'string',
    getValue: (s, w, o) => o?.text ?? 'Text' },
  { id: 'text.laufschrift', tab: 'text', label: 'Laufschrift',    unit: '',  type: 'string',
    getValue: (s, w, o) => o?.text ?? 'Laufschrift' },
  { id: 'text.mehrzeilig', tab: 'text', label: 'Mehrzeilig',      unit: '',  type: 'string',
    getValue: (s, w, o) => o?.text ?? 'Zeile 1' },
  { id: 'text.leer',       tab: 'text', label: 'Leerzeile',      unit: '',  type: 'string',
    getValue: () => '' },
];

function _wmo(code) {
  if (code == null) return '--';
  if (code === 0) return 'Klar';
  if (code <= 3) return 'Bewoelkt';
  if (code <= 49) return 'Nebel';
  if (code <= 59) return 'Niesel';
  if (code <= 69) return 'Regen';
  if (code <= 79) return 'Schnee';
  if (code <= 84) return 'Schauer';
  return 'Gewitter';
}

/* ═══ DISPLAY-MODI ═══ */
const ALL_DATA = ['number', 'percent', 'string', 'time'];
const NUMERIC = ['number', 'percent'];
const TEXT_LIKE = ['string', 'time'];

export const DISPLAY_MODES = [
  // ─── Zahlenwerte (alle Groessen) ───
  { id: 'zahl',            label: 'Zahl Klein (1x)',     forTypes: ALL_DATA },
  { id: 'zahl_gross',      label: 'Zahl Mittel (2x)',    forTypes: ALL_DATA },
  { id: 'zahl_xl',         label: 'Zahl Gross (3x)',     forTypes: ALL_DATA },
  { id: 'zahl_xxl',        label: 'Zahl XXL (4x)',       forTypes: ALL_DATA },
  { id: 'zahl_breit',      label: 'Breit (X2 Y1)',       forTypes: ALL_DATA },
  { id: 'zahl_hoch',       label: 'Hoch (X1 Y2)',        forTypes: ALL_DATA },
  { id: 'zahl_x3y1',       label: 'Extra Breit (X3 Y1)', forTypes: ALL_DATA },
  { id: 'zahl_x1y3',       label: 'Extra Hoch (X1 Y3)',  forTypes: ALL_DATA },
  // ─── Invertiert / Rahmen ───
  { id: 'text_invertiert',  label: 'Invertiert',          forTypes: ALL_DATA },
  { id: 'text_inv_gross',   label: 'Invertiert Mittel',   forTypes: ALL_DATA },
  { id: 'text_inv_xl',      label: 'Invertiert Gross',    forTypes: ALL_DATA },
  { id: 'text_rahmen',      label: 'Mit Rahmen',          forTypes: ALL_DATA },
  { id: 'text_rahmen_gross', label: 'Rahmen Mittel',      forTypes: ALL_DATA },
  // ─── Balken (alle Numerischen) ───
  { id: 'balken',           label: 'Balken',              forTypes: NUMERIC },
  { id: 'balken_schmal',    label: 'Balken Schmal',       forTypes: NUMERIC },
  { id: 'balken_breit',     label: 'Balken Breit',        forTypes: NUMERIC },
  { id: 'balken_hoch',      label: 'Balken Hoch',         forTypes: NUMERIC },
  { id: 'balken_label',     label: 'Balken + Wert',       forTypes: NUMERIC },
  { id: 'balken_label_in',  label: 'Balken (Wert innen)', forTypes: NUMERIC },
  { id: 'balken_voll',      label: 'Balken Volle Breite', forTypes: NUMERIC },
  // ─── Gauge ───
  { id: 'gauge',            label: 'Gauge Klein',         forTypes: NUMERIC },
  { id: 'gauge_gross',      label: 'Gauge Gross',         forTypes: NUMERIC },
  { id: 'gauge_xl',         label: 'Gauge XL',            forTypes: NUMERIC },
  // ─── Verlauf / Sparkline ───
  { id: 'sparkline',        label: 'Verlauf Klein',       forTypes: NUMERIC },
  { id: 'sparkline_gross',  label: 'Verlauf Gross',       forTypes: NUMERIC },
  { id: 'sparkline_breit',  label: 'Verlauf Breit',       forTypes: NUMERIC },
  { id: 'sparkline_voll',   label: 'Verlauf Volle Breite',forTypes: NUMERIC },
  // ─── Text / Laufschrift ───
  { id: 'text',             label: 'Text Klein',          forTypes: TEXT_LIKE },
  { id: 'text_gross',       label: 'Text Mittel',         forTypes: TEXT_LIKE },
  { id: 'text_xl',          label: 'Text Gross',          forTypes: TEXT_LIKE },
  { id: 'laufschrift',      label: 'Laufschrift',         forTypes: ['string'] },
  // ─── Layout ───
  { id: 'linie_h',          label: 'Linie horizontal',    forTypes: ['shape'] },
  { id: 'linie_v',          label: 'Linie vertikal',      forTypes: ['shape'] },
  { id: 'rahmen_shape',     label: 'Rahmen',              forTypes: ['shape'] },
  { id: 'block',            label: 'Block gefuellt',      forTypes: ['shape'] },
  { id: 'section',          label: 'Trennlinie',          forTypes: ['shape'] },
];

/* Layout-Quellen */
export const LAYOUT_SOURCES = [
  { id: 'layout.linie_h', tab: 'layout', label: 'Linie horizontal', type: 'shape', defaultDisplay: 'linie_h' },
  { id: 'layout.linie_v', tab: 'layout', label: 'Linie vertikal',   type: 'shape', defaultDisplay: 'linie_v' },
  { id: 'layout.rahmen',  tab: 'layout', label: 'Rahmen',           type: 'shape', defaultDisplay: 'rahmen' },
  { id: 'layout.block',   tab: 'layout', label: 'Block',            type: 'shape', defaultDisplay: 'block' },
  { id: 'layout.section', tab: 'layout', label: 'Trennlinie',       type: 'shape', defaultDisplay: 'section' },
  { id: 'layout.abstand', tab: 'layout', label: 'Abstand',          type: 'shape', defaultDisplay: 'block' },
];

export const ALL_SOURCES = [...DATA_SOURCES, ...LAYOUT_SOURCES];

export function getSource(id) {
  // Direkt finden
  const direct = ALL_SOURCES.find(s => s.id === id);
  if (direct) return direct;
  // Dynamische Disk-ID: "disk.used.2" → base "disk.used", diskIdx 2
  const m = id?.match(/^(disk\.\w+)\.(\d+)$/);
  if (m) {
    const base = ALL_SOURCES.find(s => s.id === m[1]);
    if (base) {
      const di = parseInt(m[2]);
      return { ...base, id, _diskIdx: di,
        getValue: (s, w, o) => base.getValue(s, w, { ...o, diskIdx: di }),
        getRaw: base.getRaw ? (s, w, o) => base.getRaw(s, w, { ...o, diskIdx: di }) : undefined,
      };
    }
  }
  return null;
}
export function getModesForType(type) { return DISPLAY_MODES.filter(m => m.forTypes.includes(type)); }

/**
 * Quellen fuer einen Tab holen.
 * Fuer 'disk': dynamisch pro gefundener Disk expandieren.
 * stats muss uebergeben werden damit Disk-Anzahl bekannt ist.
 */
export function getSourcesForTab(tab, stats) {
  if (tab === 'disk' && stats?.disks?.length > 0) {
    const result = [];
    for (let i = 0; i < stats.disks.length; i++) {
      const d = stats.disks[i];
      const lbl = d.label || d.mount || `Disk ${i}`;
      // Separator pro Disk
      result.push({ id: `_disk_header_${i}`, tab: 'disk', label: `── ${lbl} (${d.mount}) ──`, type: '_header', isHeader: true });
      // Alle Disk-Quellen mit fixem diskIdx
      for (const src of ALL_SOURCES.filter(s => s.tab === 'disk' && s.perDisk)) {
        result.push({
          ...src,
          id: `${src.id}.${i}`,
          label: src.label,
          _diskIdx: i,
          getValue: (s, w, o) => src.getValue(s, w, { ...o, diskIdx: i }),
          getRaw: src.getRaw ? (s, w, o) => src.getRaw(s, w, { ...o, diskIdx: i }) : undefined,
        });
      }
    }
    return result;
  }
  return ALL_SOURCES.filter(s => s.tab === tab && !s.perDisk);
}

export const HISTORY_KEYS = {
  'cpu.percent': 'cpu', 'cpu.temp': 'temp', 'cpu.temp_pct': 'temp',
  'ram.percent': 'ram', 'ram.free_pct': 'ram',
  'fan.rpm': 'fan_speed', 'fan.duty': 'fan_speed', 'fan.rpm_pct': 'fan_speed',
  'net.rx': 'net_rx', 'net.tx': 'net_tx', 'net.rx_raw': 'net_rx', 'net.tx_raw': 'net_tx',
};

export function defaultOpts(display) {
  switch (display) {
    // Zahlen
    case 'zahl':             return { scaleX: 1, scaleY: 1, prefix: '', suffix: '' };
    case 'zahl_gross':       return { scaleX: 2, scaleY: 2, prefix: '', suffix: '' };
    case 'zahl_xl':          return { scaleX: 3, scaleY: 3, prefix: '', suffix: '' };
    case 'zahl_xxl':         return { scaleX: 4, scaleY: 4, prefix: '', suffix: '' };
    case 'zahl_breit':       return { scaleX: 2, scaleY: 1, prefix: '', suffix: '' };
    case 'zahl_hoch':        return { scaleX: 1, scaleY: 2, prefix: '', suffix: '' };
    case 'zahl_x3y1':        return { scaleX: 3, scaleY: 1, prefix: '', suffix: '' };
    case 'zahl_x1y3':        return { scaleX: 1, scaleY: 3, prefix: '', suffix: '' };
    // Invertiert / Rahmen
    case 'text_invertiert':  return { scaleX: 1, scaleY: 1, prefix: '', suffix: '', invert: true };
    case 'text_inv_gross':   return { scaleX: 2, scaleY: 2, prefix: '', suffix: '', invert: true };
    case 'text_inv_xl':      return { scaleX: 3, scaleY: 3, prefix: '', suffix: '', invert: true };
    case 'text_rahmen':      return { scaleX: 1, scaleY: 1, prefix: '', suffix: '', border: true };
    case 'text_rahmen_gross':return { scaleX: 2, scaleY: 2, prefix: '', suffix: '', border: true };
    // Balken
    case 'balken':           return { width: 60, height: 6 };
    case 'balken_schmal':    return { width: 40, height: 3 };
    case 'balken_breit':     return { width: 80, height: 8 };
    case 'balken_hoch':      return { width: 60, height: 12 };
    case 'balken_label':     return { width: 50, height: 6, scaleX: 1, scaleY: 1, prefix: '', suffix: '%' };
    case 'balken_label_in':  return { width: 60, height: 8, scaleX: 1, scaleY: 1, prefix: '', suffix: '' };
    case 'balken_voll':      return { width: 126, height: 6 };
    // Gauge
    case 'gauge':            return { radius: 12 };
    case 'gauge_gross':      return { radius: 20 };
    case 'gauge_xl':         return { radius: 28 };
    // Sparkline
    case 'sparkline':        return { width: 50, height: 16 };
    case 'sparkline_gross':  return { width: 80, height: 24 };
    case 'sparkline_breit':  return { width: 100, height: 16 };
    case 'sparkline_voll':   return { width: 126, height: 30 };
    // Text
    case 'text':             return { scaleX: 1, scaleY: 1, text: '' };
    case 'text_gross':       return { scaleX: 2, scaleY: 2, text: '' };
    case 'text_xl':          return { scaleX: 3, scaleY: 3, text: '' };
    case 'laufschrift':      return { scaleX: 1, scaleY: 1, text: 'Hallo Welt!' };
    // Layout
    case 'linie_h':          return { width: 60 };
    case 'linie_v':          return { height: 20 };
    case 'rahmen_shape':     return { width: 40, height: 20 };
    case 'block':            return { width: 40, height: 20 };
    case 'section':          return { width: 60, text: 'CPU' };
    default:                 return {};
  }
}

export function createWidget(sourceId, display, x = 4, y = 4) {
  const src = getSource(sourceId);
  const opts = defaultOpts(display);
  return {
    id: Date.now() + Math.random(),
    source: sourceId,
    display,
    x, y,
    name: src?.label ?? sourceId,
    opts: { ...opts, invert: opts.invert || false, border: opts.border || false, align: 'left', boxW: 0 },
  };
}
